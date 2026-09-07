"""ROE policy — ambiguity and execution gates."""

from __future__ import annotations

from typing import Any

from research_objective.schema import CONFIDENCE_THRESHOLD


def should_block_execution(objective_confidence: float, requires_clarification: bool = False) -> bool:
    if requires_clarification:
        return True
    return float(objective_confidence or 0.0) < CONFIDENCE_THRESHOLD


def clarification_payload(
    *,
    reason: str,
    primary_objective: str | None,
    objective_confidence: float,
    alternatives: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "requires_clarification": True,
        "clarification_reason": reason,
        "primary_objective": primary_objective,
        "objective_confidence": round(float(objective_confidence or 0.0), 4),
        "threshold": CONFIDENCE_THRESHOLD,
        "alternative_objectives": list(alternatives or []),
        "block_execution": True,
        "message": (
            "Objective confidence is below institutional threshold. "
            "Clarify the decision to support before research begins."
        ),
    }
