"""Shared deterministic helpers for FIRE-02 relationship analysis."""

from __future__ import annotations

from typing import Any

from financial_intelligence.confidence import score_confidence
from financial_intelligence.drivers.schema import SEV_HIGH, SEV_INFO, SEV_LOW, SEV_MEDIUM
from financial_intelligence.schema import CONF_LOW
from financial_intelligence.trends import normalize_series


def latest_pair(
    series_a: list[dict[str, Any]],
    series_b: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Align two series on a shared latest period (exact period match preferred)."""
    a = normalize_series(series_a)
    b = normalize_series(series_b)
    if not a or not b:
        return None
    by_b = {r["period"]: r for r in b}
    # Prefer shared latest period walking back from A's latest
    for row in reversed(a):
        if row["period"] in by_b:
            return row, by_b[row["period"]]
    return None


def prior_pair(
    series_a: list[dict[str, Any]],
    series_b: list[dict[str, Any]],
    *,
    skip_latest: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Shared prior period (second-to-latest shared if skip_latest)."""
    a = normalize_series(series_a)
    b = normalize_series(series_b)
    by_b = {r["period"]: r for r in b}
    shared = [r for r in a if r["period"] in by_b]
    if len(shared) < (2 if skip_latest else 1):
        return None
    row = shared[-2] if skip_latest else shared[-1]
    return row, by_b[row["period"]]


def pct_change(curr: float, prior: float) -> float | None:
    if prior == 0:
        return None
    return round(100.0 * (curr - prior) / abs(prior), 4)


def direction(delta: float | None, *, eps: float = 1e-9) -> str:
    if delta is None:
        return "unknown"
    if abs(delta) < eps:
        return "flat"
    return "up" if delta > 0 else "down"


def evidence_points(
    *rows: dict[str, Any] | None,
    metrics: list[str] | None = None,
) -> list[dict[str, Any]]:
    out = []
    for i, r in enumerate(rows):
        if not r:
            continue
        out.append(
            {
                "metric": (metrics[i] if metrics and i < len(metrics) else r.get("metric")),
                "period": r.get("period"),
                "value": r.get("value"),
                "version": r.get("version"),
                "warehouse_version": r.get("warehouse_version"),
                "validation_id": r.get("validation_id"),
                "validation_status": r.get("validation_status"),
                "fact_key": r.get("fact_key"),
                "evidence_id": r.get("validation_id") or r.get("fact_key"),
            }
        )
    return out


def make_relationship(
    *,
    category: str,
    relationship: str,
    observation: str,
    narrative: str,
    evidence: list[dict[str, Any]],
    confidence: str,
    severity: str,
    code: str,
    supporting_values: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Hard guard: no evidence → no relationship (anti-hallucination)."""
    if not evidence:
        return None
    return {
        "category": category,
        "relationship": relationship,
        "observation": observation,
        "narrative": narrative,
        "confidence": confidence,
        "severity": severity,
        "evidence": evidence,
        "code": code,
        "supporting_values": supporting_values or {},
        "source": "fire_02_driver_engine",
        "buy_sell": False,
        "forecast": False,
        "uses_llm": False,
    }


def confidence_for_points(
    points: list[dict[str, Any]],
    *,
    history_n: int,
    coverage_pct: float | None,
    conflict: bool = False,
) -> str:
    statuses = [str(p.get("validation_status") or "") for p in points if p]
    status = "APPROVED" if any(s.upper() == "APPROVED" for s in statuses) else (statuses[0] if statuses else None)
    conf = score_confidence(
        history_n=history_n,
        windows_n=1 if history_n >= 2 else 0,
        validation_status=status,
        coverage_pct=coverage_pct,
    )
    if conflict:
        # Downgrade one band
        order = ["High", "Medium", "Low"]
        idx = order.index(conf) if conf in order else 2
        conf = order[min(idx + 1, 2)]
    if history_n < 2:
        return CONF_LOW
    return conf


def severity_for(code: str, *, adverse: bool) -> str:
    if not adverse:
        return SEV_LOW if "strong" in code or "improving" in code or "deleverag" in code else SEV_INFO
    if any(x in code for x in ("weak", "pressure", "deteriorat", "not_supported", "aggressive")):
        return SEV_HIGH
    return SEV_MEDIUM


def series_history_n(series_map: dict[str, list[dict[str, Any]]], *metrics: str) -> int:
    return max((len(normalize_series(series_map.get(m) or [])) for m in metrics), default=0)
