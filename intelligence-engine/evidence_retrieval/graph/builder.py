"""Evidence graph — Question → Entities → Objects → Documents → Pack."""

from __future__ import annotations

import uuid
from typing import Any

from evidence_retrieval.store import put_graph, utc_now


def build_evidence_graph(
    *,
    retrieval_id: str,
    discovery: dict[str, Any],
    ranked: list[dict[str, Any]],
    pack_ids: list[str],
) -> dict[str, Any]:
    graph_id = f"iere_graph_{retrieval_id}"
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    qid = f"q:{retrieval_id}"
    nodes.append({"id": qid, "kind": "question", "label": (discovery.get("question") or "")[:120]})

    for company in discovery.get("companies") or []:
        eid = f"entity:{company}"
        nodes.append({"id": eid, "kind": "entity", "label": company})
        edges.append(_edge(qid, eid, source="discovery", weight=1.0, confidence=0.9, discovery=discovery))

    for item in ranked[:60]:
        kid = f"ko:{item.get('evidence_id')}"
        nodes.append(
            {
                "id": kid,
                "kind": "knowledge_object",
                "label": item.get("title"),
                "evidence_type": item.get("evidence_type"),
            }
        )
        company = item.get("company")
        src = f"entity:{company}" if company else qid
        if company and not any(n["id"] == src for n in nodes):
            nodes.append({"id": src, "kind": "entity", "label": company})
            edges.append(_edge(qid, src, source="discovery", weight=0.8, confidence=0.8, discovery=discovery))
        edges.append(
            _edge(
                src,
                kid,
                source=str(item.get("source") or "unknown"),
                weight=float(item.get("rank_score") or 0.5),
                confidence=float(item.get("confidence") or 0.5),
                discovery=discovery,
                available_from=item.get("available_from"),
                replay_id=retrieval_id,
            )
        )
        if item.get("document_id"):
            did = f"doc:{item['document_id']}"
            if not any(n["id"] == did for n in nodes):
                nodes.append({"id": did, "kind": "document", "label": item.get("document_id")})
            edges.append(
                _edge(
                    kid,
                    did,
                    source="institutional_documents",
                    weight=0.9,
                    confidence=float(item.get("confidence") or 0.8),
                    discovery=discovery,
                    available_from=item.get("available_from"),
                    replay_id=retrieval_id,
                )
            )
        et = str(item.get("evidence_type") or "")
        if et == "CORPORATE_EVENTS":
            ev = f"event:{item.get('evidence_id')}"
            nodes.append({"id": ev, "kind": "event", "label": item.get("title")})
            edges.append(
                _edge(kid, ev, source="corporate_events", weight=0.85, confidence=0.75, discovery=discovery)
            )
        if et == "MACRO_INDICATORS":
            mid = "macro:global"
            if not any(n["id"] == mid for n in nodes):
                nodes.append({"id": mid, "kind": "macro", "label": "macro"})
            edges.append(_edge(kid, mid, source="macro", weight=0.8, confidence=0.7, discovery=discovery))
        if et == "GOVERNMENT_POLICIES":
            gid = "gov:policy"
            if not any(n["id"] == gid for n in nodes):
                nodes.append({"id": gid, "kind": "government", "label": "government"})
            edges.append(_edge(kid, gid, source="government", weight=0.8, confidence=0.7, discovery=discovery))
        if et == "RELATIONSHIP_GRAPH":
            rid = f"rel:{item.get('evidence_id')}"
            nodes.append({"id": rid, "kind": "relationship", "label": item.get("title")})
            edges.append(
                _edge(kid, rid, source="relationships", weight=0.75, confidence=0.7, discovery=discovery)
            )

    for pid in pack_ids:
        nid = f"pack:{pid}"
        nodes.append({"id": nid, "kind": "evidence_pack", "label": pid})
        edges.append(
            _edge(qid, nid, source="assembly", weight=1.0, confidence=0.95, discovery=discovery, replay_id=retrieval_id)
        )

    # Deduplicate nodes by id
    seen = set()
    uniq_nodes = []
    for n in nodes:
        if n["id"] in seen:
            continue
        seen.add(n["id"])
        uniq_nodes.append(n)

    graph = {
        "graph_id": graph_id,
        "retrieval_id": retrieval_id,
        "nodes": uniq_nodes,
        "edges": edges,
        "built_at": utc_now(),
        "fabricated": False,
    }
    put_graph(graph_id, graph)
    return graph


def _edge(
    frm: str,
    to: str,
    *,
    source: str,
    weight: float,
    confidence: float,
    discovery: dict[str, Any],
    available_from: str | None = None,
    replay_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": f"e_{uuid.uuid4().hex[:10]}",
        "from": frm,
        "to": to,
        "source": source,
        "weight": round(float(weight), 6),
        "confidence": round(float(confidence), 6),
        "available_from": available_from or discovery.get("as_of"),
        "replay_id": replay_id,
    }
