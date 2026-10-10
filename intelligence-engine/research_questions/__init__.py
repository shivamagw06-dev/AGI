"""Institutional Research Question Engine (IRQ) V1 — RQ2 Sprint 2.

Soft-wire research-question planner. Not a top-level intelligence layer.
Executes AFTER Hypothesis Generation (IHG) and BEFORE Evidence Collection.
"""

from research_questions.production import (
    constitution,
    generate_for_question,
    health,
    plan,
    quality_gates,
    soft_slice_for_ask_agi,
)

__all__ = [
    "constitution",
    "generate_for_question",
    "health",
    "plan",
    "quality_gates",
    "soft_slice_for_ask_agi",
]
