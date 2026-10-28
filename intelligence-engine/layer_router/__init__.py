"""Intelligence Layer Router (ILR) V1 — RQ1 Sprint 6.

Soft-wire execution planner. Not a top-level intelligence layer.
"""

from layer_router.production import (
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
