"""Market Relationship Graph — nodes, edges, transmission paths."""

from __future__ import annotations

from typing import Any

from market_relationship_intelligence.schema import GraphEdge, GraphNode
from market_relationship_intelligence.store import STORE

MARKET_NODES = {
    "NIFTY",
    "SENSEX",
    "MARKET BREADTH",
    "MARKET LIQUIDITY",
    "EQUITY VALUATION",
    "INDIA EQUITIES",
    "EQUITIES",
    "BULL MARKET",
    "BEAR MARKET",
    "MARKET RECOVERY",
    "CORRECTION RISK",
    "INDEX PERFORMANCE",
    "RISK APPETITE",
    "MARKET LEADERSHIP",
    "LARGE CAP LEADERSHIP",
    "SMALL CAP INDEX",
    "MIDCAPS",
    "LARGE CAPS",
    "MID CAPS",
    "SMALL CAPS",
}
MACRO_NODES = {
    "REPO RATE",
    "CPI",
    "US TREASURY YIELD",
    "BOND YIELDS",
    "USDINR",
    "FISCAL DEFICIT",
}
ASSET_NODES = {
    "USD INDEX",
    "GOLD",
    "OIL",
    "COMMODITIES",
    "EMERGING MARKETS",
}
FLOW_NODES = {
    "FII BUYING",
    "FII SELLING",
    "FII FLOWS",
    "DII BUYING",
    "LIQUIDITY",
    "LIQUIDITY STRESS",
}
VOL_NODES = {"INDIA VIX"}
COMPANY_NODES = {"RELIANCE", "HDFCBANK", "INFY", "TCS", "MARUTI", "ITC", "LT"}


def _node_type(key: str, kind: str, is_source: bool) -> str:
    k = key.upper()
    if k in COMPANY_NODES or (k.isupper() and len(k) <= 12 and k not in MARKET_NODES | MACRO_NODES | ASSET_NODES | FLOW_NODES | VOL_NODES):
        if k in COMPANY_NODES:
            return "company"
    if k in MARKET_NODES:
        return "market"
    if k in MACRO_NODES:
        return "macro"
    if k in ASSET_NODES:
        return "asset"
    if k in FLOW_NODES or kind == "flows":
        if k in FLOW_NODES:
            return "flow"
    if k in VOL_NODES or kind == "volatility":
        if k in VOL_NODES:
            return "volatility"
    if kind == "market_to_company" and not is_source:
        return "company"
    if kind == "market_to_sector" and not is_source:
        return "sector"
    if kind == "sector_to_market" and is_source:
        return "sector"
    if kind == "macro_to_market" and is_source:
        return "macro"
    if kind == "cross_asset":
        return "asset"
    sector_words = {
        "BANKS",
        "BANKING",
        "BANKING LEADERSHIP",
        "CAPITAL GOODS",
        "DEFENSIVE SECTORS",
        "FMCG",
        "PHARMA",
        "AUTO",
        "NBFC",
        "ENERGY",
        "REAL ESTATE",
    }
    if k in sector_words:
        return "sector"
    return "theme"


def build_graph(*, limit: int = 500) -> dict[str, Any]:
    rows = STORE.list_all(limit=limit)
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    for r in rows:
        for key, label, is_source in (
            (r.source, r.source_label or r.source, True),
            (r.target, r.target_label or r.target, False),
        ):
            if key not in nodes:
                nodes[key] = GraphNode(
                    node_id=key,
                    label=label or key,
                    node_type=_node_type(key, r.kind, is_source),
                )
        for step in r.chain:
            if step not in nodes:
                nodes[step] = GraphNode(
                    node_id=step,
                    label=step,
                    node_type=_node_type(step, r.kind, False),
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
        "gateway": "MKRI_GRAPH",
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
