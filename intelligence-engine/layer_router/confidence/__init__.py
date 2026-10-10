"""Confidence plan from layer contributions."""

from __future__ import annotations

from typing import Any

from layer_router.registry import LAYER_DEFS
from layer_router.schema import CONFIDENCE_THRESHOLD


def build_confidence_plan(
    required: list[str],
    suppressed: list[str],
    *,
    expected_contributions: dict[str, float] | None = None,
) -> dict[str, Any]:
    contrib = {}
    for layer in required:
        base = float((LAYER_DEFS.get(layer) or {}).get("confidence_contribution") or 0.03)
        if expected_contributions and layer in expected_contributions:
            contrib[layer] = round(float(expected_contributions[layer]), 4)
        else:
            contrib[layer] = base
    total = round(sum(contrib.values()), 4)
    # Normalize display to sum ~ planned confidence uplift capped
    missing_penalty = round(0.02 * len([s for s in suppressed if s in {"FIL", "EIL", "PIL", "Business", "Financial", "Valuation"}]), 4)
    planned = round(min(0.99, 0.55 + total - missing_penalty), 4)
    return {
        "confidence_plan": {
            "by_layer": contrib,
            "planned_confidence": planned,
            "missing_layer_penalty": missing_penalty,
            "threshold": CONFIDENCE_THRESHOLD,
            "passes_threshold": planned >= CONFIDENCE_THRESHOLD,
        },
        "contribution_sum": total,
    }
