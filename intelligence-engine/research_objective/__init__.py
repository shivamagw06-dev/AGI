"""Research Objective Engine (ROE) V1 — RQ1 Sprint 3.

Soft-wire extension of Intent Intelligence. Not a top-level intelligence layer.
"""

from research_objective.production import (
    constitution,
    health,
    plan,
    quality_gates,
    soft_slice_for_ask_agi,
)

__all__ = [
    "constitution",
    "health",
    "plan",
    "quality_gates",
    "soft_slice_for_ask_agi",
]
