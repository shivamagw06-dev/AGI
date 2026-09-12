"""Sector Relationship Graph — nodes, edges, transmission paths (MRI twin)."""

from __future__ import annotations

from typing import Any

from sector_relationship_intelligence.schema import GraphEdge, GraphNode
from sector_relationship_intelligence.store import STORE


def _node_type(key: str, kind: str, is_source: bool) -> str:
    k = key.upper()
    if k in {"NIFTY", "SENSEX", "MARKET BREADTH"}:
        return "market"
    if k in {
        "INFY",
        "TCS",
        "HCLTECH",
        "HDFCBANK",
        "RELIANCE",
        "MARUTI",
        "LT",
        "ITC",
    }:
        return "company"
    if kind == "global_to_sector" and is_source:
        return "global"
    if kind == "macro_to_sector" and is_source:
        return "macro"
    if kind == "sector_to_company" and not is_source:
        return "company"
    if kind == "company_to_sector" and is_source:
        return "company"
    if kind == "sector_to_market" and not is_source:
        return "market"
    if kind in {
        "macro_to_sector",
        "sector_to_sector",
        "sector_to_company",
        "company_to_sector",
        "sector_to_market",
        "global_to_sector",
    }:
        if kind == "company_to_sector" and not is_source:
            return "sector"
        if kind == "sector_to_company" and is_source:
            return "sector"
        if kind in {"sector_to_sector", "macro_to_sector", "global_to_sector", "sector_to_market"}:
            return "sector" if (not is_source or kind.startswith("sector")) else (
                "macro" if kind == "macro_to_sector" else "global" if kind == "global_to_sector" else "sector"
            )
    sector_words = {
        "BANKING",
        "BANKS",
        "PRIVATE BANKS",
        "NBFC",
        "NBFCS",
        "FMCG",
        "IT SERVICES",
        "IT",
        "PHARMA",
        "AUTO",
        "AUTOMOBILES",
        "REAL ESTATE",
        "CEMENT",
        "CAPITAL GOODS",
        "OIL & GAS",
        "CHEMICALS",
        "PAINT",
        "TYRES",
        "LOGISTICS",
        "AVIATION",
        "METALS",
        "STEEL",
        "INFRASTRUCTURE",
        "ENGINEERING",
        "EXPORTERS",
    }
    if k in sector_words:
        return "sector"
    if kind.startswith("macro"):
        return "macro"
    return "sector"


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

    paths = _sample_paths(rows)

    return {
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "nodes": [n.model_dump(mode="json") for n in nodes.values()],
        "edges": [e.model_dump(mode="json") for e in edges],
        "transmission_paths": paths,
        "providers_queried": [],
        "gateway": "SRI_GRAPH",
    }


def _sample_paths(rows: list) -> list[dict[str, Any]]:
    paths: list[dict[str, Any]] = []
    for r in rows:
        if r.chain:
            path = [r.source, *r.chain, r.target] if r.target not in r.chain else [r.source, *r.chain]
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
                    "kind": r.kind,
                }
            )
    paths.sort(key=lambda p: (len(p["path"]), p["confidence_pct"]), reverse=True)
    return paths[:20]


def find_paths(
    *,
    start: str,
    end: str | None = None,
    max_depth: int = 4,
) -> list[dict[str, Any]]:
    """BFS transmission paths from start (optionally ending at end)."""
    start_n = str(start or "").strip().lower()
    end_n = str(end or "").strip().lower() if end else None
    if not start_n:
        return []

    relationships = STORE.list_all(limit=500)
    adj: dict[str, list] = {}
    for rel in relationships:
        if rel.stale:
            continue
        s = str(rel.source or "").strip().lower()
        if s:
            adj.setdefault(s, []).append(rel)

    paths: list[dict[str, Any]] = []
    queue: list[tuple[str, list]] = [(start_n, [])]
    seen: set[tuple[str, int]] = set()

    while queue and len(paths) < 20:
        node, trail = queue.pop(0)
        depth = len(trail)
        key = (node, depth)
        if key in seen:
            continue
        seen.add(key)
        if depth > 0 and (end_n is None or node == end_n):
            paths.append(
                {
                    "start": start_n,
                    "end": node,
                    "depth": depth,
                    "hops": [
                        {
                            "source": r.source,
                            "target": r.target,
                            "relationship": r.relationship,
                            "direction": r.direction,
                            "confidence_pct": r.confidence_pct,
                            "average_lag": r.average_lag,
                            "kind": r.kind,
                        }
                        for r in trail
                    ],
                    "min_confidence": min((r.confidence_pct for r in trail), default=0),
                }
            )
            if end_n is not None:
                continue
        if depth >= max_depth:
            continue
        for rel in adj.get(node, []):
            nxt = str(rel.target or "").strip().lower()
            if not nxt or nxt == node:
                continue
            if any(str(x.relationship_id) == str(rel.relationship_id) for x in trail):
                continue
            queue.append((nxt, trail + [rel]))

    paths.sort(key=lambda p: (-int(p.get("min_confidence") or 0), p.get("depth") or 99))
    return paths
