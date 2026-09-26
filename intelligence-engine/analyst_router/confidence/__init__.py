"""Routing confidence aggregation."""

from __future__ import annotations

from typing import Any

from analyst_router.schema import CONFIDENCE_THRESHOLD


def score_routing(
    *,
    participation_confidence: float,
    required: list[str],
    speaking_order: list[str],
    weights: dict[str, float],
    objective_confidence: float | None = None,
) -> dict[str, Any]:
    part_c = float(participation_confidence or 0.0)
    order_c = 0.98 if speaking_order and set(required).issubset(set(speaking_order)) else 0.6
    weight_c = 0.98 if weights and abs(sum(weights.values()) - 1.0) < 0.02 else 0.7
    obj_c = float(objective_confidence if objective_confidence is not None else part_c)
    overall = round(min(part_c, order_c, weight_c, max(obj_c, 0.85)), 4)
    return {
        "participation_confidence": round(part_c, 4),
        "speaking_order_confidence": round(order_c, 4),
        "weight_confidence": round(weight_c, 4),
        "objective_confidence": round(obj_c, 4),
        "routing_confidence": overall,
        "threshold": CONFIDENCE_THRESHOLD,
        "passes_threshold": overall >= CONFIDENCE_THRESHOLD,
    }
