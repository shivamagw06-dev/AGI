"""Institutional Analyst Router (IAR) V1 — RQ1 Sprint 5.

Soft-wire extension of Intent Intelligence / ROE. Not a top-level intelligence layer.
"""

from analyst_router.production import (
    constitution,
    health,
    quality_gates,
    route,
    soft_slice_for_ask_agi,
)

__all__ = [
    "constitution",
    "health",
    "quality_gates",
    "route",
    "soft_slice_for_ask_agi",
]
