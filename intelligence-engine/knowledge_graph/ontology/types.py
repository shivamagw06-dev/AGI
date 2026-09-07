"""IKG ontology — allowed node and edge types."""

from __future__ import annotations

from knowledge_graph.schema import EDGE_TYPES, NODE_TYPES

NODE_ONTOLOGY = {t: {"type": t, "canonical_required": True} for t in NODE_TYPES}
EDGE_ONTOLOGY = {
    t: {
        "type": t,
        "directed": True,
        "requires_evidence": True,
        "temporal": True,
    }
    for t in EDGE_TYPES
}


def is_valid_node_type(t: str) -> bool:
    return t in NODE_ONTOLOGY


def is_valid_edge_type(t: str) -> bool:
    return t in EDGE_ONTOLOGY
