"""Government / policy relationship views."""

from __future__ import annotations

from typing import Any

from knowledge_factory.economic_relationship_intelligence import store as ieri_store
from knowledge_factory.economic_relationship_intelligence.schema import IERI_VERSION
from knowledge_factory.economic_relationship_intelligence.transmission.orders import (
    transmission_from_entity,
)


def policy_relationships(policy: str, *, as_of: str | None = None) -> dict[str, Any]:
    pid = str(policy or "").strip()
    rows = ieri_store.list_relationships(entity=pid, as_of=as_of)
    industries = []
    companies = []
    macros = []
    other = []
    for r in rows:
        tgt_kind = (r.get("target_ref") or {}).get("kind")
        src_kind = (r.get("source_ref") or {}).get("kind")
        brief = {
            "relationship_id": r.get("relationship_id"),
            "source": r.get("source_entity"),
            "target": r.get("target_entity"),
            "relationship_type": r.get("relationship_type"),
            "semantics": r.get("semantics"),
            "strength": r.get("strength"),
            "confidence": r.get("confidence"),
            "evidence": r.get("evidence"),
            "transmission_order": r.get("transmission_order"),
            "shock_direction": r.get("shock_direction"),
        }
        if tgt_kind == "industry" or src_kind == "industry":
            industries.append(brief)
        elif tgt_kind == "company" or src_kind == "company":
            companies.append(brief)
        elif tgt_kind == "macro" or src_kind == "macro":
            macros.append(brief)
        else:
            other.append(brief)

    tx = transmission_from_entity(pid, as_of=as_of)
    return {
        "policy_id": pid,
        "industries": industries,
        "companies": companies,
        "macro_links": macros,
        "other": other,
        "transmission": {
            "first_order": tx.get("first_order"),
            "second_order": tx.get("second_order"),
            "third_order": tx.get("third_order"),
        },
        "n": len(rows),
        "as_of": as_of,
        "version": IERI_VERSION,
        "fabricated": False,
    }
