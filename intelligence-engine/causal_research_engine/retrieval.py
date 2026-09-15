"""Bounded traversal over AGI's existing causal graph; no second graph."""

from __future__ import annotations

from collections import deque
from typing import Any, Iterable

from causal_graph.graph.store import graph_snapshot
from causal_research_engine.adapters import from_cig_edge
from causal_research_engine.schema import CausalRelationship


def relevant_subgraph(
    seeds: Iterable[str], *, depth: int = 3, company_id: str | None = None,
    industry: str | None = None, min_confidence: float = 0.0,
    analysis_as_of: str | None = None,
) -> dict[str, Any]:
    depth = max(0, min(int(depth), 6))
    snapshot = graph_snapshot()
    nodes = {str(row.get("id")): row for row in snapshot.get("nodes") or []}
    edges = snapshot.get("edges") or []
    adjacency: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        adjacency.setdefault(str(edge.get("source")), []).append(edge)
        adjacency.setdefault(str(edge.get("target")), []).append(edge)
    queue = deque((str(seed), 0) for seed in seeds if seed)
    visited: set[str] = set()
    selected: list[CausalRelationship] = []
    selected_ids: set[str] = set()
    while queue:
        node_id, level = queue.popleft()
        if node_id in visited or level > depth:
            continue
        visited.add(node_id)
        if level == depth:
            continue
        for edge in adjacency.get(node_id, []):
            relation = from_cig_edge(edge, industry=industry, company_id=company_id)
            if relation.confidence < min_confidence:
                continue
            if analysis_as_of and relation.valid_from and relation.valid_from > analysis_as_of:
                continue
            if relation.relationship_id not in selected_ids:
                selected.append(relation); selected_ids.add(relation.relationship_id)
            other = str(edge.get("target")) if str(edge.get("source")) == node_id else str(edge.get("source"))
            queue.append((other, level + 1))
    return {
        "seeds": list(dict.fromkeys(str(x) for x in seeds if x)), "depth": depth,
        "nodes": [nodes[x] for x in visited if x in nodes],
        "relationships": selected, "relationship_count": len(selected),
        "point_in_time": analysis_as_of, "source_graph": "AGI_CIG",
    }
