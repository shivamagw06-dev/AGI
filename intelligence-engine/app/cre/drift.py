"""CRE-003 Drift Detection — model / confidence / feature / distribution / performance."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Any

from app.cre.models import DriftAlert, RegressionAlert, RollingMetrics
from app.validation.models import ReplayDaySlice


def _now_iso(ts: datetime | None = None) -> str:
    return (ts or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z")


def _psi(reference: list[float], current: list[float], bins: int = 10) -> float:
    """Population Stability Index between two samples."""
    if len(reference) < 2 or len(current) < 2:
        return 0.0
    lo = min(min(reference), min(current))
    hi = max(max(reference), max(current))
    if hi <= lo:
        return 0.0
    width = (hi - lo) / bins
    eps = 1e-6
    psi = 0.0
    for i in range(bins):
        a = lo + i * width
        b = lo + (i + 1) * width
        r = sum(1 for x in reference if (a <= x < b) or (i == bins - 1 and x == b)) / len(reference)
        c = sum(1 for x in current if (a <= x < b) or (i == bins - 1 and x == b)) / len(current)
        r = max(r, eps)
        c = max(c, eps)
        psi += (c - r) * math.log(c / r)
    return round(psi, 6)


def detect_drift(
    *,
    days: list[ReplayDaySlice],
    rolling: dict[str, RollingMetrics],
    as_of: str,
    generated_at: datetime | None = None,
) -> tuple[list[DriftAlert], list[RegressionAlert]]:
    """Emit DriftAlert / RegressionAlert from replay series + rolling metrics."""
    ts = _now_iso(generated_at)
    drifts: list[DriftAlert] = []
    regressions: list[RegressionAlert] = []

    confidences = [c for d in days for c in d.confidences.values()]
    scores = [s for d in days for s in d.l4_scores.values()]
    e03_scores = [s for d in days for s in d.e03_scores.values()]
    returns = [float(d.portfolio_return or 0.0) for d in days]

    if len(confidences) >= 4:
        mid = len(confidences) // 2
        base_m = mean(confidences[:mid])
        curr_m = mean(confidences[mid:])
        delta = curr_m - base_m
        if abs(delta) >= 0.15:
            drifts.append(
                DriftAlert(
                    alert_id="drift-confidence-L4",
                    kind="confidence",
                    engine="L4",
                    severity="critical" if abs(delta) >= 0.25 else "watch",
                    metric="mean_confidence",
                    baseline=round(base_m, 6),
                    current=round(curr_m, 6),
                    delta=round(delta, 6),
                    message=f"Confidence drift Δ={delta:.3f}",
                    as_of=as_of,
                    timestamp=ts,
                )
            )

    if len(scores) >= 4:
        mid = len(scores) // 2
        psi = _psi(scores[:mid], scores[mid:])
        if psi >= 0.1:
            drifts.append(
                DriftAlert(
                    alert_id="drift-distribution-L4",
                    kind="distribution",
                    engine="L4",
                    severity="critical" if psi >= 0.25 else "watch",
                    metric="score_psi",
                    baseline=0.0,
                    current=psi,
                    delta=psi,
                    message=f"Distribution drift PSI={psi:.3f}",
                    as_of=as_of,
                    timestamp=ts,
                )
            )

    if len(e03_scores) >= 4 and len(scores) >= 4:
        n = min(len(e03_scores), len(scores))
        feat_delta = abs(mean(scores[:n]) - mean(e03_scores[:n]))
        if feat_delta >= 10.0:
            drifts.append(
                DriftAlert(
                    alert_id="drift-feature-L4",
                    kind="feature",
                    engine="L4",
                    severity="watch",
                    metric="l4_vs_e03_score_gap",
                    baseline=round(mean(e03_scores[:n]), 6),
                    current=round(mean(scores[:n]), 6),
                    delta=round(feat_delta, 6),
                    message=f"Feature/score gap L4 vs E03={feat_delta:.3f}",
                    as_of=as_of,
                    timestamp=ts,
                )
            )

    m30 = rolling.get("30")
    m90 = rolling.get("90")
    if (
        m30
        and m90
        and m90.information_coefficient is not None
        and m30.information_coefficient is not None
    ):
        base = m90.information_coefficient
        curr = m30.information_coefficient
        drop = base - curr
        if drop >= 0.15:
            drifts.append(
                DriftAlert(
                    alert_id="drift-model-L4",
                    kind="model",
                    engine="L4",
                    severity="critical",
                    metric="information_coefficient",
                    baseline=round(base, 6),
                    current=round(curr, 6),
                    delta=round(-drop, 6),
                    message="Model IC drift vs longer window",
                    as_of=as_of,
                    timestamp=ts,
                )
            )
            regressions.append(
                RegressionAlert(
                    alert_id="regr-ic-L4",
                    engine="L4",
                    severity="critical",
                    metric="information_coefficient",
                    baseline=round(base, 6),
                    current=round(curr, 6),
                    message="Performance degradation: IC drop",
                    as_of=as_of,
                    timestamp=ts,
                )
            )

    if len(returns) >= 4:
        mid = len(returns) // 2
        base_vol = pstdev(returns[:mid]) if len(returns[:mid]) > 1 else 0.0
        curr_vol = pstdev(returns[mid:]) if len(returns[mid:]) > 1 else 0.0
        if base_vol > 1e-12 and (curr_vol - base_vol) / base_vol >= 0.5:
            drifts.append(
                DriftAlert(
                    alert_id="drift-performance-E10",
                    kind="performance",
                    engine="E10",
                    severity="watch",
                    metric="return_volatility",
                    baseline=round(base_vol, 6),
                    current=round(curr_vol, 6),
                    delta=round(curr_vol - base_vol, 6),
                    message="Performance volatility drift",
                    as_of=as_of,
                    timestamp=ts,
                )
            )

    for key, eng in (("parity_stability", "ORCH"), ("schema_stability", "ORCH")):
        val = getattr(m30, key, None) if m30 is not None else None
        if val is not None and val < 1.0:
            regressions.append(
                RegressionAlert(
                    alert_id=f"regr-{key}-ORCH",
                    engine=eng,
                    severity="critical" if val < 0.95 else "watch",
                    metric=key,
                    baseline=1.0,
                    current=round(float(val), 6),
                    message=f"{key} regression",
                    as_of=as_of,
                    timestamp=ts,
                )
            )

    if len(days) < 30:
        drifts.append(
            DriftAlert(
                alert_id="drift-info-short-window",
                kind="model",
                engine="CRE",
                severity="info",
                metric="days_used",
                baseline=30.0,
                current=float(len(days)),
                delta=float(len(days) - 30),
                message="Rolling windows truncated to available replay days",
                as_of=as_of,
                timestamp=ts,
            )
        )

    return drifts, regressions


def extract_series(days: list[ReplayDaySlice]) -> dict[str, Any]:
    return {
        "confidences": [c for d in days for c in d.confidences.values()],
        "l4_scores": [s for d in days for s in d.l4_scores.values()],
        "e03_scores": [s for d in days for s in d.e03_scores.values()],
        "returns": [float(d.portfolio_return or 0.0) for d in days],
        "as_ofs": [d.as_of for d in days],
    }
