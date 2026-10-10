"""Macro Relationship Graph — nodes and edges for transmission paths."""

from __future__ import annotations

from typing import Any

from macroeconomic_relationship_intelligence.schema import GraphEdge, GraphNode
from macroeconomic_relationship_intelligence.store import STORE


def _node_type(key: str, kind: str, is_source: bool) -> str:
    k = key.upper()
    if k in {"NIFTY", "SENSEX"}:
        return "market"
    if k in {"INFY", "TCS", "HDFCBANK", "RELIANCE", "ITC"}:
        return "company"
    if kind == "global_to_india" and is_source:
        return "global"
    if kind == "macro_to_company" and not is_source:
        return "company"
    if kind == "macro_to_sector" and not is_source:
        return "sector"
    if kind == "macro_to_market" and not is_source:
        return "market"
    if kind == "macro_to_macro":
        return "macro"
    # Heuristic sectors
    sector_words = {
        "BANKS",
        "PRIVATE BANKS",
        "FMCG",
        "IT SERVICES",
        "PHARMA",
        "AIRLINES",
        "OMCS",
        "CAPITAL GOODS",
        "REAL ESTATE",
        "HOUSING",
        "NBFCS",
        "UTILITIES",
        "CEMENT",
        "ENGINEERING",
        "RAILWAYS",
    }
    if k in sector_words or key.replace("_", " ").title() in {
        "Private Banks",
        "IT Services",
        "Capital Goods",
        "Real Estate",
    }:
        return "sector"
    return "macro"


def build_graph(*, limit: int = 500) -> dict[str, Any]:
    rows = STORE.list_all(limit=limit)
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    for r in rows:
        for key, label, is_source in (
            (r.source, r.source_label or r.source, True),
            (r.target, r.target_label or r.target, False),
        ):
            nid = key
            if nid not in nodes:
                nodes[nid] = GraphNode(
                    node_id=nid,
                    label=label or key,
                    node_type=_node_type(key, r.kind, is_source),
                )
            # Expand chain nodes
        for step in r.chain:
            if step not in nodes:
                nodes[step] = GraphNode(
                    node_id=step,
                    label=step,
                    node_type="theme" if " " not in step else "sector",
                )

        edges.append(
            GraphEdge(
                relationship_id=r.relationship_id,
                source=r.source,
                target=r.target,
                relationship=r.relationship,
                direction=r.direction,
                confidence_pct=r.confidence_pct,
                chain=list(r.chain),
            )
        )

    # Sample transmission paths (Fed → … → Infosys)
    paths = _sample_paths(rows)

    return {
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "nodes": [n.model_dump(mode="json") for n in nodes.values()],
        "edges": [e.model_dump(mode="json") for e in edges],
        "transmission_paths": paths,
        "providers_queried": [],
        "gateway": "MRI_GRAPH",
    }


def _sample_paths(rows: list) -> list[dict[str, Any]]:
    paths = []
    for r in rows:
        if r.chain:
            path = [r.source, *r.chain, r.target] if r.target not in r.chain else [r.source, *r.chain]
            # de-dupe consecutive
            clean: list[str] = []
            for p in path:
                if not clean or clean[-1] != p:
                    clean.append(p)
            paths.append(
                {
                    "relationship_id": r.relationship_id,
                    "path": clean,
                    "confidence_pct": r.confidence_pct,
                    "relationship": r.relationship,
                }
            )
    # Prefer high-confidence long paths
    paths.sort(key=lambda p: (len(p["path"]), p["confidence_pct"]), reverse=True)
    return paths[:15]
