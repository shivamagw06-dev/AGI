"""CCI-01 traversal — walk relationships; soft-use KG-01 paths when available."""

from __future__ import annotations

from typing import Any, Optional

from institutional_cross_company.kg_bridge import soft_get_company_graph
from institutional_cross_company.models import InstitutionalRelationship
from institutional_cross_company.relationship_engine import relationships_for_company


def traverse(
    source: str,
    *,
    relationship_types: Optional[list[str]] = None,
    max_depth: int = 2,
) -> dict[str, Any]:
    """BFS over CCI relationships; annotate with KG-01 availability (not a second graph)."""
    start = str(source or "").upper().strip()
    allowed = {t.lower() for t in (relationship_types or [])} if relationship_types else None
    visited: set[str] = {start}
    frontier = [start]
    edges: list[dict[str, Any]] = []
    nodes: set[str] = {start}
    depth = 0

    while frontier and depth < max_depth:
        nxt: list[str] = []
        for entity in frontier:
            # Only expand company-like tickers (skip pure macro/sector labels for peer expansion)
            if entity.isalpha() or any(ch.isdigit() for ch in entity) or "&" in entity or "-" in entity:
                rels = relationships_for_company(entity) if len(entity) <= 15 else []
            else:
                rels = []
            for rel in rels:
                if allowed and rel.relationship_type not in allowed:
                    continue
                target = rel.target_entity
                edges.append(
                    {
                        "from": rel.source_entity,
                        "to": target,
                        "type": rel.relationship_type,
                        "strength": rel.strength,
                        "relationship_id": rel.relationship_id,
                        "kg_backed": rel.kg_backed,
                    }
                )
                nodes.add(target)
                key = target.upper() if isinstance(target, str) else str(target)
                if key not in visited and _looks_like_ticker(key):
                    visited.add(key)
                    nxt.append(key)
        frontier = nxt
        depth += 1

    kg = soft_get_company_graph(start) if _looks_like_ticker(start) else {"available": False}
    return {
        "source": start,
        "nodes": sorted(nodes),
        "edges": edges,
        "depth": depth,
        "kg_ref": {
            "system": "KG-01",
            "available": bool(kg.get("available")),
            "ok": bool(kg.get("ok")),
        },
        "owns_graph": False,
    }


def _looks_like_ticker(value: str) -> bool:
    v = str(value or "")
    if not v or " " in v:
        return False
    if v.lower() in {
        "interest_rates",
        "oil",
        "fx",
        "inflation",
        "gdp",
        "credit_cycle",
        "banks",
        "private banks",
        "it services",
    }:
        return False
    return v.replace("&", "").replace("-", "").isalnum() and 2 <= len(v) <= 15


def path_summaries(rels: list[InstitutionalRelationship]) -> list[dict[str, Any]]:
    return [
        {
            "relationship_id": r.relationship_id,
            "path": list(r.propagation_path) or [r.source_entity, r.relationship_type, r.target_entity],
            "type": r.relationship_type,
        }
        for r in rels
    ]
