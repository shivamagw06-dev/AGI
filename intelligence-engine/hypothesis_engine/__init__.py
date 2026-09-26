"""Institutional Hypothesis Generation Engine (IHG) V1 — RQ2 Sprint 1.

Soft-wire hypothesis planner. Not a top-level intelligence layer.
Executes AFTER IREP and BEFORE first analyst research.
"""

from hypothesis_engine.production import (
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
