"""Causal Intelligence Graph (CIG) V1 — why did this happen?"""

from causal_graph.production import (
    analyse,
    company,
    dashboard,
    event,
    graph,
    health,
    quality_gates,
    soft_slice_for_analyst,
    soft_slice_for_irs,
)
from causal_graph.schema import CIG_VERSION, PRIMARY_QUESTION

__all__ = [
    "CIG_VERSION",
    "PRIMARY_QUESTION",
    "analyse",
    "company",
    "dashboard",
    "event",
    "graph",
    "health",
    "quality_gates",
    "soft_slice_for_analyst",
    "soft_slice_for_irs",
]
