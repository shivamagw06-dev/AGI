"""Evidence node constructor — institutional analyst node shape."""

from __future__ import annotations

import hashlib
from typing import Any

from institutional_evidence_graph.schema import SOURCE_STRENGTH


def evidence_node(
    *,
    entity: str,
    domain: str,
    source: str,
    timestamp: str | None = None,
    confidence: float = 0.5,
    document: str | None = None,
    paragraph: str | None = None,
    relationship: str | None = None,
    expiry: str | None = None,
    evidence_strength: float | None = None,
    title: str | None = None,
    evidence_id: str | None = None,
    available_from: str | None = None,
    kind: str = "evidence",
    counterpart: str | None = None,
) -> dict[str, Any]:
    src = str(source or "unknown").lower()
    strength = evidence_strength
    if strength is None:
        strength = SOURCE_STRENGTH.get(src, SOURCE_STRENGTH["unknown"])
        for key, val in SOURCE_STRENGTH.items():
            if key != "unknown" and key in src:
                strength = val
                break
    nid_src = evidence_id or f"{entity}:{domain}:{src}:{title or paragraph or relationship or 'node'}"
    node_id = "ev:" + hashlib.sha1(nid_src.encode("utf-8")).hexdigest()[:16]
    return {
        "node_id": node_id,
        "kind": kind,
        "domain": domain,
        "entity": str(entity).upper() if entity else None,
        "counterpart": counterpart,
        "source": source,
        "timestamp": timestamp or available_from,
        "available_from": available_from or timestamp,
        "confidence": float(confidence),
        "document": document,
        "paragraph": (paragraph or title or "")[:400] if (paragraph or title) else None,
        "title": title,
        "relationship": relationship,
        "expiry": expiry,
        "evidence_strength": float(strength),
        "evidence_id": evidence_id,
        "fabricated": False,
        "llm_used": False,
    }


def entity_node(entity_id: str, *, label: str | None = None, kind: str = "company") -> dict[str, Any]:
    eid = str(entity_id).upper()
    return {
        "node_id": f"entity:{eid}",
        "kind": "entity",
        "entity_kind": kind,
        "entity": eid,
        "label": label or eid,
        "fabricated": False,
    }


def domain_node(entity_id: str, domain: str, *, label: str) -> dict[str, Any]:
    eid = str(entity_id).upper()
    return {
        "node_id": f"domain:{eid}:{domain}",
        "kind": "domain",
        "entity": eid,
        "domain": domain,
        "label": label,
        "fabricated": False,
    }
