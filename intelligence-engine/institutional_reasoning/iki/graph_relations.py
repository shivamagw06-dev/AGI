"""Module 6 — Knowledge Graph expansion (in-process).

Framework → REQUIRES → Evidence → SUPPORTED_BY → Author → CONFLICTS_WITH …
Still no Neo4j.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.iki.registry import get_framework, list_frameworks
from institutional_reasoning.iki.schema import IKI_EDGE_TYPES

GRAPH_VERSION = "iki-graph-relations-v1.0.0"


def _edge(src: str, rel: str, dst: str, **meta: Any) -> dict[str, Any]:
    return {"source": src, "type": rel, "target": dst, "meta": meta}


def framework_subgraph(framework_id: str) -> dict[str, Any]:
    spec = get_framework(framework_id)
    if not spec:
        return {"found": False, "framework_id": framework_id}
    edges: list[dict[str, Any]] = []
    for req in spec.requires:
        edges.append(_edge(framework_id, "REQUIRES", req, kind="evidence"))
    edges.append(_edge(framework_id, "SUPPORTED_BY", spec.author, kind="author"))
    for c in spec.competing_frameworks:
        edges.append(_edge(framework_id, "CONFLICTS_WITH", c))
        edges.append(_edge(framework_id, "COMPETES_WITH", c))
    for a in spec.alternative_frameworks:
        edges.append(_edge(framework_id, "ALTERNATIVE_TO", a))
    for s in spec.applicable_sectors:
        edges.append(_edge(framework_id, "APPLIES_TO", s, kind="sector"))
    for s in spec.not_applicable_sectors:
        edges.append(_edge(framework_id, "INVALIDATED_BY", s, kind="sector_condition"))
    for cond in spec.failure_conditions:
        edges.append(_edge(framework_id, "INVALIDATED_BY", cond, kind="failure_condition"))
    return {
        "found": True,
        "framework_id": framework_id,
        "author": spec.author,
        "edges": edges,
        "edge_types": list(IKI_EDGE_TYPES),
        "graph_version": GRAPH_VERSION,
    }


def author_conflicts(author_a: str, author_b: str) -> dict[str, Any]:
    """Cross-author conflict surface from registry."""
    a = str(author_a or "")
    b = str(author_b or "")
    fa = [f for f in list_frameworks() if f.get("author") == a]
    fb = [f for f in list_frameworks() if f.get("author") == b]
    conflicts = []
    for x in fa:
        for y in fb:
            if y["framework_id"] in (x.get("competing_frameworks") or []) or x["framework_id"] in (
                y.get("competing_frameworks") or []
            ):
                conflicts.append(
                    {
                        "left": x["framework_id"],
                        "right": y["framework_id"],
                        "relation": "CONFLICTS_WITH",
                        "left_author": a,
                        "right_author": b,
                    }
                )
    return {
        "authors": [a, b],
        "conflicts": conflicts,
        "left_frameworks": [f["framework_id"] for f in fa],
        "right_frameworks": [f["framework_id"] for f in fb],
        "graph_version": GRAPH_VERSION,
    }


def soft_ikg_slice(framework_id: str | None = None) -> dict[str, Any]:
    """Soft attach for existing IKG consumers — additive only."""
    if framework_id:
        return framework_subgraph(framework_id)
    return {
        "graph_version": GRAPH_VERSION,
        "edge_types": list(IKI_EDGE_TYPES),
        "frameworks": [framework_subgraph(f["framework_id"]) for f in list_frameworks()[:12]],
        "neo4j": False,
        "note": "In-process relation expansion; existing IKG unchanged.",
    }
