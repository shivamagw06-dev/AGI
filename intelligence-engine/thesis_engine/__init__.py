"""Institutional Thesis Construction Engine (ITCE) V1 — RQ2 Sprint 7.

Soft-wire thesis constructor. Not a top-level intelligence layer.
Executes AFTER the Bayesian Belief & Confidence Engine and BEFORE the Investment Committee.
"""

from thesis_engine.production import (
    build_thesis,
    constitution,
    generate_for_question,
    health,
    plan,
    quality_gates,
    soft_slice_for_ask_agi,
)

__all__ = [
    "build_thesis",
    "constitution",
    "generate_for_question",
    "health",
    "plan",
    "quality_gates",
    "soft_slice_for_ask_agi",
]
