"""RQ1 Sprint 2 — Entity Resolution Engine (ERE) V1."""

from entity_resolution.canonical_resolver import resolve_question
from entity_resolution.production import constitution, dashboard, health, quality_gates, resolve

__all__ = [
    "resolve_question",
    "resolve",
    "health",
    "dashboard",
    "constitution",
    "quality_gates",
]
