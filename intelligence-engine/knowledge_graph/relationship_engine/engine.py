"""Relationship engine — edges for an entity with confidence/evidence."""

from __future__ import annotations

from typing import Any

from knowledge_graph.confidence.model import edge_confidence
from knowledge_graph.entity_resolution.resolve import resolve_entity
from knowledge_graph.evidence.attach import evidence_for_edge
from knowledge_graph.graph.store import incoming, node_for, outgoing


def relationships_for(entity_id: str) -> dict[str, Any]:
    resolved = resolve_entity(entity_id)
    if not resolved:
        return {"found": False, "entity": entity_id, "relationships": []}
    cid = resolved["canonical_id"]
    node = resolved["node"]
    rels = []
    for edge in outgoing(cid) + incoming(cid):
        direction = "out" if str(edge.get("source")) == cid else "in"
        other = str(edge.get("target") if direction == "out" else edge.get("source"))
        rels.append(
            {
                "direction": direction,
                "relation": edge.get("relation"),
                "from": edge.get("source"),
                "to": edge.get("target"),
                "counterpart": other,
                "counterpart_label": (node_for(other) or {}).get("label") or other,
                "strength": edge.get("strength"),
                "confidence": edge.get("confidence"),
                "confidence_score": edge_confidence(edge),
                "evidence": evidence_for_edge(edge),
                "historical_validation": edge.get("historical_accuracy"),
                "start_date": edge.get("start_date"),
                "end_date": edge.get("end_date"),
                "active": edge.get("active", True),
                "historical": edge.get("historical", False),
            }
        )
    rels.sort(key=lambda r: (-float(r.get("confidence_score") or 0), r.get("relation") or ""))
    by_type: dict[str, list[dict[str, Any]]] = {}
    for r in rels:
        by_type.setdefault(str(r.get("relation")), []).append(r)
    return {
        "found": True,
        "canonical_id": cid,
        "entity": node,
        "relationship_count": len(rels),
        "relationships": rels,
        "by_type": by_type,
        "duplicate_free": resolved.get("duplicate_free", True),
    }
