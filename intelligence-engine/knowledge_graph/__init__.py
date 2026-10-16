"""Institutional Knowledge Graph (IKG) V1 — what is connected?"""

from knowledge_graph.production import (
    company,
    dashboard,
    entity,
    health,
    path,
    quality_gates,
    query,
    relationships,
    soft_slice_for_analyst,
    soft_slice_for_irs,
)
from knowledge_graph.schema import IKG_VERSION, PRIMARY_QUESTION

__all__ = [
    "IKG_VERSION",
    "PRIMARY_QUESTION",
    "company",
    "dashboard",
    "entity",
    "health",
    "path",
    "quality_gates",
    "query",
    "relationships",
    "soft_slice_for_analyst",
    "soft_slice_for_irs",
]
