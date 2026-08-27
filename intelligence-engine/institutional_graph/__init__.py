"""KG-01 — Institutional Knowledge Graph (single-company scope)."""

from institutional_graph.graph import InstitutionalKnowledgeGraph, build_company_graph
from institutional_graph.inference import infer
from institutional_graph.schema import KG_VERSION, KG_WORKSTREAM_ID

__all__ = [
    "InstitutionalKnowledgeGraph",
    "build_company_graph",
    "infer",
    "KG_VERSION",
    "KG_WORKSTREAM_ID",
]
