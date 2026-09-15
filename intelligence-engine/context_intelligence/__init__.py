"""Context Intelligence Engine (CIE) V1 — RQ1 Sprint 4.

Soft-wire enrichment before analysts reason. Not a top-level intelligence layer.
"""

from context_intelligence.production import (
    constitution,
    enrich,
    health,
    quality_gates,
    soft_slice_for_ask_agi,
)

__all__ = [
    "constitution",
    "enrich",
    "health",
    "quality_gates",
    "soft_slice_for_ask_agi",
]
