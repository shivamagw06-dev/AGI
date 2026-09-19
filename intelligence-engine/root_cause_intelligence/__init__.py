"""AGIB Phase 3 Sprint 3.2 — Root Cause Intelligence (RCI).

Transforms IEL failures into clustered, actionable engineering work.
Does not patch selectors — Sprint 3.3 applies framework fixes from clusters.
"""

from root_cause_intelligence.production import analyze, nightly, status
from root_cause_intelligence.schema import MODULE_CODE, PROGRAMME, RCI_VERSION

__all__ = [
    "RCI_VERSION",
    "MODULE_CODE",
    "PROGRAMME",
    "status",
    "analyze",
    "nightly",
]
