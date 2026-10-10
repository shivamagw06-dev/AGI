"""Relationship enrichment — IKG authoritative, registry soft fallback."""

from __future__ import annotations

from typing import Any

from entity_resolution.entity_registry import get_entity


def enrich_relationships(entity: dict[str, Any]) -> dict[str, Any]:
    kg_id = entity.get("knowledge_graph_id") or entity.get("ticker") or entity.get("id")
    ikg_pack: dict[str, Any] = {}
    try:
        from knowledge_graph.relationship_engine.engine import relationships_for

        ikg_pack = relationships_for(str(kg_id)) if kg_id else {}
    except Exception:
        ikg_pack = {}

    peers: list[str] = []
    indexes: list[str] = []
    regulators: list[str] = []
    macro_dependencies: list[str] = []

    if ikg_pack.get("found"):
        by_type = ikg_pack.get("by_type") or {}
        for rel in by_type.get("competes_with") or []:
            peers.append(str(rel.get("counterpart_label") or rel.get("counterpart")))
        for rel in ikg_pack.get("relationships") or []:
            relation = str(rel.get("relation") or "")
            label = str(rel.get("counterpart_label") or rel.get("counterpart"))
            if "index" in relation or "member" in relation:
                indexes.append(label)
            if "regulat" in relation:
                regulators.append(label)
            if "macro" in relation or "depends" in relation:
                macro_dependencies.append(label)

    # Registry soft fallback
    for pid in entity.get("peers") or []:
        p = get_entity(pid)
        if p:
            peers.append(str(p.get("canonical_name")))
    for iid in entity.get("indexes") or []:
        ix = get_entity(iid)
        if ix:
            indexes.append(str(ix.get("canonical_name")))

    # Deduplicate preserving order
    def uniq(xs: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in xs:
            if not x or x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    return {
        "peers": uniq(peers)[:12],
        "indexes": uniq(indexes)[:12],
        "regulators": uniq(regulators)[:8],
        "macro_dependencies": uniq(macro_dependencies)[:8],
        "portfolio_presence": [],
        "parent": entity.get("parent"),
        "children": list(entity.get("children") or []),
        "ikg_relationship_count": ikg_pack.get("relationship_count") or 0,
        "ikg_found": bool(ikg_pack.get("found")),
    }
