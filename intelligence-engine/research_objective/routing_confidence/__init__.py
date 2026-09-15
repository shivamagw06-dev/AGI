"""Aggregate routing / planning confidences."""

from __future__ import annotations

from typing import Any

from research_objective.schema import CONFIDENCE_THRESHOLD


def score_routing(
    *,
    intent_confidence: float | None,
    objective_confidence: float,
    blueprint_sections: list[str] | None,
    analysts: list[str] | None,
    layers: list[str] | None,
) -> dict[str, Any]:
    intent_c = float(intent_confidence if intent_confidence is not None else objective_confidence)
    obj_c = float(objective_confidence or 0.0)
    bp_c = 0.98 if blueprint_sections and len(blueprint_sections) >= 4 else 0.8
    analyst_c = 0.98 if analysts else 0.5
    layer_c = 0.97 if layers is not None else 0.5
    # Educational may have empty layers — still high confidence
    if layers == [] and analysts == ["Academy"]:
        layer_c = 0.99
    routing = round(min(intent_c, obj_c, bp_c, analyst_c, layer_c), 4)
    overall = round((intent_c * 0.15 + obj_c * 0.45 + bp_c * 0.15 + analyst_c * 0.125 + layer_c * 0.125), 4)
    return {
        "intent_confidence": round(intent_c, 4),
        "objective_confidence": round(obj_c, 4),
        "blueprint_confidence": round(bp_c, 4),
        "analyst_routing_confidence": round(analyst_c, 4),
        "layer_routing_confidence": round(layer_c, 4),
        "routing_confidence": routing,
        "overall_confidence": overall,
        "threshold": CONFIDENCE_THRESHOLD,
        "passes_threshold": obj_c >= CONFIDENCE_THRESHOLD,
    }
