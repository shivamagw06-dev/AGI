"""Evidence Graph — Annual Report → supports → Claim → used by → Research Note."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..entity.resolve import resolve_entity


def build_evidence_graph(
    ticker_or_query: str,
    *,
    registry_items: Optional[List[Dict[str, Any]]] = None,
    claims: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    resolved = resolve_entity(ticker_or_query)
    if not resolved.get("resolved"):
        return {"ok": True, "resolved": False, "nodes": [], "edges": []}

    ticker = resolved["ticker"]
    entity_id = resolved["entity_id"]
    nodes: List[Dict[str, Any]] = [
        {"id": entity_id, "type": "entity", "label": resolved.get("company") or ticker}
    ]
    edges: List[Dict[str, Any]] = []
    sources: List[str] = ["iep_registry"]

    items = list(registry_items or [])
    if not items:
        try:
            from ..registry.store import get_registry_for_ticker

            reg = get_registry_for_ticker(ticker)
            items = list(reg.get("items") or [])
        except Exception:
            items = []

    for ev in items:
        eid = str(ev.get("evidence_id") or "")
        if not eid:
            continue
        nodes.append(
            {
                "id": eid,
                "type": "evidence",
                "label": ev.get("document_type") or "evidence",
                "document_type": ev.get("document_type"),
                "authority_score": ev.get("authority_score"),
            }
        )
        edges.append({"from": eid, "to": entity_id, "rel": "documents"})

    claim_rows = list(claims or [])
    for c in claim_rows:
        cid = str(c.get("claim_id") or "")
        if not cid:
            continue
        nodes.append(
            {
                "id": cid,
                "type": "claim",
                "label": (c.get("text") or "")[:120],
                "verified": c.get("verified"),
                "confidence": c.get("confidence"),
            }
        )
        for ref in c.get("evidence_ids") or []:
            edges.append({"from": str(ref), "to": cid, "rel": "supports"})
        for consumer in c.get("consumers") or []:
            nodes.append({"id": str(consumer), "type": "consumer", "label": str(consumer)})
            edges.append({"from": cid, "to": str(consumer), "rel": "used_by"})

    # Soft IEG
    try:
        from institutional_evidence_graph.production import get_graph  # type: ignore

        g = get_graph(ticker)
        if isinstance(g, dict) and (g.get("nodes") or g.get("edges")):
            sources.append("institutional_evidence_graph")
            for n in g.get("nodes") or []:
                if isinstance(n, dict) and n.get("id"):
                    nodes.append({"id": str(n["id"]), "type": n.get("type") or "ieg", "label": n.get("label")})
            for e in g.get("edges") or []:
                if isinstance(e, dict) and e.get("from") and e.get("to"):
                    edges.append(
                        {"from": str(e["from"]), "to": str(e["to"]), "rel": e.get("rel") or e.get("type") or "related"}
                    )
    except Exception:
        pass

    # Dedup nodes
    by_id = {}
    for n in nodes:
        by_id[n["id"]] = n

    return {
        "ok": True,
        "resolved": True,
        "entity_id": entity_id,
        "ticker": ticker,
        "node_count": len(by_id),
        "edge_count": len(edges),
        "nodes": list(by_id.values()),
        "edges": edges,
        "sources": sorted(set(sources)),
        "rule": "Every conclusion becomes explainable via evidence lineage",
        "example_path": [
            "Annual Report",
            "supports",
            "Revenue Growth",
            "used_by",
            "Financial Intelligence",
            "used_by",
            "Research Note",
        ],
    }
