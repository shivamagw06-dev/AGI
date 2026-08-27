"""In-memory institutional knowledge graph store."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from knowledge_graph.company_graph.seed import COMPANY_EDGES, COMPANY_NODES
from knowledge_graph.events.seed import EVENT_EDGES, EVENT_NODES
from knowledge_graph.evidence.attach import is_supported
from knowledge_graph.macro_graph.seed import MACRO_EDGES, MACRO_NODES
from knowledge_graph.ownership.seed import OWNERSHIP_EDGES, OWNERSHIP_NODES
from knowledge_graph.people.seed import PEOPLE_EDGES, PEOPLE_NODES
from knowledge_graph.products.seed import PRODUCT_EDGES, PRODUCT_NODES
from knowledge_graph.regulations.seed import REG_EDGES, REG_NODES
from knowledge_graph.supply_chain.seed import SUPPLY_EDGES, SUPPLY_NODES
from knowledge_graph.technology.seed import TECH_EDGES, TECH_NODES
from knowledge_graph.thesis.seed import THESIS_EDGES, THESIS_NODES


def nodes() -> list[dict[str, Any]]:
    bags = [
        COMPANY_NODES,
        MACRO_NODES,
        SUPPLY_NODES,
        OWNERSHIP_NODES,
        PEOPLE_NODES,
        PRODUCT_NODES,
        TECH_NODES,
        REG_NODES,
        EVENT_NODES,
        THESIS_NODES,
    ]
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for bag in bags:
        for node in bag:
            nid = str(node["id"])
            if nid in seen:
                # merge aliases into first canonical node
                for existing in out:
                    if existing["id"] == nid:
                        aliases = list(dict.fromkeys((existing.get("aliases") or []) + (node.get("aliases") or [])))
                        existing["aliases"] = aliases
                        break
                continue
            seen.add(nid)
            out.append(deepcopy(node))
    return out


def edges(*, include_unsupported: bool = False) -> list[dict[str, Any]]:
    bags = [
        COMPANY_EDGES,
        MACRO_EDGES,
        SUPPLY_EDGES,
        OWNERSHIP_EDGES,
        PEOPLE_EDGES,
        PRODUCT_EDGES,
        TECH_EDGES,
        REG_EDGES,
        EVENT_EDGES,
        THESIS_EDGES,
    ]
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for bag in bags:
        for edge in bag:
            if not include_unsupported and not is_supported(edge):
                continue
            key = (str(edge.get("source")), str(edge.get("target")), str(edge.get("relation")))
            if key in seen:
                continue
            seen.add(key)
            out.append(deepcopy(edge))
    return out


def node_for(node_id: str) -> dict[str, Any] | None:
    nid = str(node_id)
    for n in nodes():
        if n["id"] == nid:
            return deepcopy(n)
    return None


def outgoing(node_id: str) -> list[dict[str, Any]]:
    nid = str(node_id)
    return [e for e in edges() if str(e.get("source")) == nid]


def incoming(node_id: str) -> list[dict[str, Any]]:
    nid = str(node_id)
    return [e for e in edges() if str(e.get("target")) == nid]


def graph_snapshot() -> dict[str, Any]:
    n = nodes()
    e = edges()
    hist = [x for x in e if x.get("historical") or not x.get("active", True)]
    return {
        "node_count": len(n),
        "edge_count": len(e),
        "historical_edge_count": len(hist),
        "nodes": n,
        "edges": e,
        "active_edges": [x for x in e if x.get("active", True)],
        "types": sorted({str(x.get("type")) for x in n}),
        "relations": sorted({str(x.get("relation")) for x in e}),
    }
