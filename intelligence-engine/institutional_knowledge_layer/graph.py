"""Knowledge Graph edges from extractions — confidence-weighted, soft."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_layer.schema import RELATIONSHIP_TYPES, now_ts
from institutional_knowledge_layer import store


def upsert_relationships(
    relationships: list[dict[str, Any]],
    *,
    source_id: str | None = None,
) -> dict[str, Any]:
    """Append/merge relationship edges into durable JSONL edge log + index."""
    written = 0
    for rel in relationships or []:
        if not isinstance(rel, dict):
            continue
        rtype = str(rel.get("rel") or "").strip()
        if rtype not in RELATIONSHIP_TYPES:
            # allow close aliases
            alias = {
                "benefits": "benefits_from",
                "hurts": "hurt_by",
                "customer_of": "customer_of",
            }.get(rtype)
            if not alias:
                continue
            rtype = alias
        edge = {
            "from_type": rel.get("from_type"),
            "from_id": rel.get("from_id"),
            "rel": rtype,
            "to_type": rel.get("to_type"),
            "to_id": rel.get("to_id"),
            "confidence": float(rel.get("confidence") or 0.4),
            "source_id": source_id or rel.get("source_id"),
            "at": now_ts(),
        }
        if not edge["from_id"] or not edge["to_id"]:
            continue
        if store.append_jsonl("graph_edges", edge):
            written += 1
            # maintain per-entity adjacency index
            _index_edge(edge)
    return {"ok": True, "edges_written": written}


def _index_edge(edge: dict[str, Any]) -> None:
    try:
        key = f"{edge.get('from_type')}:{edge.get('from_id')}"
        idx = store.load_memory("graph_index", key) or {
            "key": key,
            "edges": [],
            "updated_at": now_ts(),
        }
        edges = list(idx.get("edges") or [])
        sig = (
            f"{edge.get('rel')}|{edge.get('to_type')}|{edge.get('to_id')}|{edge.get('source_id')}"
        )
        if not any(
            f"{e.get('rel')}|{e.get('to_type')}|{e.get('to_id')}|{e.get('source_id')}" == sig
            for e in edges
        ):
            edges.append(edge)
        idx["edges"] = edges[-120:]
        idx["updated_at"] = now_ts()
        store.save_memory("graph_index", key, idx)
    except Exception:
        return


def neighbors(
    *,
    entity_type: str,
    entity_id: str,
    limit: int = 40,
) -> list[dict[str, Any]]:
    try:
        key = f"{entity_type}:{entity_id}"
        idx = store.load_memory("graph_index", key)
        if not idx:
            return []
        edges = list(idx.get("edges") or [])
        return edges[: max(1, int(limit))]
    except Exception:
        return []


def package_for_ask(
    *,
    company_ids: list[str] | None = None,
    industries: list[str] | None = None,
) -> dict[str, Any]:
    edges: list[dict[str, Any]] = []
    for cid in company_ids or []:
        edges.extend(neighbors(entity_type="company", entity_id=str(cid).upper(), limit=20))
    for ind in industries or []:
        edges.extend(neighbors(entity_type="industry", entity_id=str(ind), limit=12))
    # de-dupe
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for e in edges:
        sig = f"{e.get('from_id')}|{e.get('rel')}|{e.get('to_id')}"
        if sig in seen:
            continue
        seen.add(sig)
        uniq.append(e)
    return {
        "enabled": True,
        "edge_count": len(uniq),
        "edges": uniq[:60],
        "confidence": round(
            sum(float(e.get("confidence") or 0) for e in uniq) / max(1, len(uniq)), 3
        )
        if uniq
        else 0.0,
    }
