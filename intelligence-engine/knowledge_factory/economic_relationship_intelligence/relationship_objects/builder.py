"""Immutable economic relationship objects."""

from __future__ import annotations

import hashlib
from typing import Any

from knowledge_factory.economic_relationship_intelligence.provenance import provenance
from knowledge_factory.economic_relationship_intelligence.schema import (
    IERI_VERSION,
    DIRECTIONS,
    RELATIONSHIP_TYPES,
    UNKNOWN,
    semantics_for,
)


def entity_ref(*, kind: str, entity_id: str, label: str | None = None) -> dict[str, Any]:
    eid = str(entity_id or "").strip()
    return {
        "kind": str(kind or UNKNOWN).lower(),
        "id": eid.lower() if kind not in ("company", "bank", "policy") else eid.upper() if kind == "company" or kind == "bank" else eid,
        "label": label or eid,
    }


def _normalize_entity_id(kind: str, entity_id: str) -> str:
    e = str(entity_id or "").strip()
    if kind in ("company", "bank"):
        return e.upper()
    if kind == "policy":
        return e.upper() if e.isupper() or "-" in e else e
    return e.lower().replace(" ", "_").replace("-", "_")


def build_relationship(
    *,
    source_kind: str,
    source_id: str,
    target_kind: str,
    target_id: str,
    relationship_type: str,
    direction: str = "outbound",
    strength: str | float = "moderate",
    confidence: float = 0.75,
    evidence: str | list[str] | None = None,
    source: str,
    collector: str,
    available_from: str,
    effective_date: str | None = None,
    semantics: str | None = None,
    notes: str | None = None,
    derived_from: list[str] | None = None,
    transmission_order: int | None = None,
    time_horizon: str | None = None,
    shock_direction: str | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    rtype = str(relationship_type or "").lower()
    if rtype not in RELATIONSHIP_TYPES:
        raise ValueError(f"invalid relationship_type: {relationship_type}")
    direc = str(direction or "").lower()
    if direc not in DIRECTIONS:
        raise ValueError(f"unknown direction: {direction}")
    if not source or source == UNKNOWN:
        raise ValueError("missing source")
    if not available_from:
        raise ValueError("missing available_from")

    src_id = _normalize_entity_id(source_kind, source_id)
    tgt_id = _normalize_entity_id(target_kind, target_id)
    sem = semantics_for(rtype, semantics)
    evid = evidence if isinstance(evidence, list) else ([evidence] if evidence else [])
    fingerprint = "|".join([source_kind, src_id, target_kind, tgt_id, rtype, direc, available_from])
    rid = "REL-" + hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16].upper()

    prov = provenance(
        source=source,
        collector=collector,
        confidence=confidence,
        derived_from=derived_from,
        version=version or IERI_VERSION,
    )

    obj: dict[str, Any] = {
        "relationship_id": rid,
        "source_entity": src_id,
        "target_entity": tgt_id,
        "source_ref": entity_ref(kind=source_kind, entity_id=src_id),
        "target_ref": entity_ref(kind=target_kind, entity_id=tgt_id),
        "relationship_type": rtype,
        "semantics": sem,
        "direction": direc,
        "strength": strength,
        "confidence": round(float(confidence), 4),
        "evidence": evid,
        "source": source,
        "collector": collector,
        "available_from": available_from,
        "effective_date": effective_date or available_from,
        "version": version or IERI_VERSION,
        "validation": {"status": "pending", "gates": []},
        "provenance": prov,
        "notes": notes,
        "transmission_order": transmission_order,
        "time_horizon": time_horizon,
        "shock_direction": shock_direction,
        "historical_changes": [],
        "fabricated": False,
        "immutable": True,
    }
    return obj
