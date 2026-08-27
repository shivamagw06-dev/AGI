"""Institutional Hypothesis Testing Engine (IHTE) V1 — RQ2 Sprint 4.

Soft-wire evidence testing. Not a top-level intelligence layer.
Executes AFTER Evidence Planning and BEFORE Business/Financial/Valuation analysts.
"""

from hypothesis_testing.production import (
    constitution,
    generate_for_question,
    health,
    plan,
    quality_gates,
    soft_slice_for_ask_agi,
    test_hypothesis,
)

__all__ = [
    "constitution",
    "generate_for_question",
    "health",
    "plan",
    "quality_gates",
    "soft_slice_for_ask_agi",
    "test_hypothesis",
]
