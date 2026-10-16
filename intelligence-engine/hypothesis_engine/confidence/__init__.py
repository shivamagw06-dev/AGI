"""Confidence engine — per-hypothesis and overall belief strength."""

from __future__ import annotations

from typing import Any


def score_confidence(hypotheses: list[dict[str, Any]]) -> dict[str, Any]:
    if not hypotheses:
        return {"overall_confidence": 0.0, "by_hypothesis": {}, "mean_confidence": 0.0}
    by_id = {str(h.get("id")): round(float(h.get("confidence") or 0), 4) for h in hypotheses}
    vals = list(by_id.values())
    # Weight by priority (earlier = higher)
    weighted = 0.0
    weight_sum = 0.0
    for h in hypotheses:
        conf = float(h.get("confidence") or 0)
        w = 1.0 / max(int(h.get("priority") or 1), 1)
        weighted += conf * w
        weight_sum += w
    overall = weighted / weight_sum if weight_sum else 0.0
    return {
        "overall_confidence": round(overall, 4),
        "mean_confidence": round(sum(vals) / len(vals), 4),
        "by_hypothesis": by_id,
        "high_confidence_count": sum(1 for v in vals if v >= 0.7),
        "contested_count": sum(1 for v in vals if v < 0.65),
    }
