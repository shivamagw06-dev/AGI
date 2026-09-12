"""AIP-01 / AIP-05 Cross-engine + confidence calibration (suggestions only)."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from app.aip.models import CalibrationPlan
from app.validation.golden.loader import GoldenDataset


def _plan_id(dataset_id: str, as_of: str) -> str:
    raw = f"aip_cal|{dataset_id}|{as_of}"
    return "cal_" + sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_calibration_plan(
    scored: list[dict[str, Any]],
    dataset: GoldenDataset,
    *,
    as_of: str,
) -> CalibrationPlan:
    """Propose temperature + bucket map. Never applied to production."""
    day_by = {d.as_of: d for d in dataset.days}
    obs: list[tuple[float, bool]] = []
    for r in scored:
        g = day_by.get(r["as_of"])
        if g is None:
            continue
        fwd = g.forward_returns.get(r["symbol"])
        if fwd is None:
            continue
        pred_up = r["score"] >= 50.0
        realized_up = float(fwd) > 0.0
        conf = float(r["confidence"])
        # store confidence in predicted direction
        p = conf if pred_up else (1.0 - conf)
        obs.append((p, realized_up))

    if not obs:
        return CalibrationPlan(
            plan_id=_plan_id(dataset.dataset_id, as_of),
            as_of=as_of,
            dataset_id=dataset.dataset_id,
            applied_to_production=False,
            notes=["No observations", "Not applied to production"],
        )

    hit = sum(1 for _, y in obs if y) / len(obs)
    mean_p = sum(p for p, _ in obs) / len(obs)
    baseline_err = abs(mean_p - hit)

    # Simple temperature: shrink confidence toward 0.5 to reduce overconfidence.
    best_t = 1.0
    best_err = baseline_err
    for t in (0.6, 0.8, 1.0, 1.2, 1.5):
        errs = []
        for p, y in obs:
            # temperature on logit-ish around 0.5
            centered = p - 0.5
            adj = 0.5 + centered / t
            adj = min(0.95, max(0.05, adj))
            errs.append((adj - (1.0 if y else 0.0)) ** 2)
        # also track |mean_adj - hit|
        mean_adj = sum(0.5 + (p - 0.5) / t for p, _ in obs) / len(obs)
        mean_adj = min(0.95, max(0.05, mean_adj))
        err = abs(mean_adj - hit)
        if err < best_err:
            best_err = err
            best_t = t

    buckets: list[dict[str, Any]] = []
    edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.01]
    for lo, hi in zip(edges, edges[1:]):
        group = [(p, y) for p, y in obs if lo <= p < hi]
        if not group:
            continue
        buckets.append(
            {
                "lo": lo,
                "hi": hi,
                "n": len(group),
                "mean_confidence": round(sum(p for p, _ in group) / len(group), 4),
                "hit_rate": round(sum(1 for _, y in group if y) / len(group), 4),
            }
        )

    return CalibrationPlan(
        plan_id=_plan_id(dataset.dataset_id, as_of),
        as_of=as_of,
        dataset_id=dataset.dataset_id,
        baseline_calibration_error=round(baseline_err, 6),
        proposed_calibration_error=round(best_err, 6),
        temperature=best_t,
        bucket_map=buckets,
        applied_to_production=False,
        notes=[
            "Suggestion only — AIP_PROMOTION=false blocks production apply",
            "Cross-engine score scales remain frozen under Architecture v1.0.1",
            f"temperature={best_t}",
        ],
    )
