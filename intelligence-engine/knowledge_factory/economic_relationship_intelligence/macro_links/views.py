"""Macro variable relationship views."""

from __future__ import annotations

from typing import Any

from knowledge_factory.economic_relationship_intelligence import store as ieri_store
from knowledge_factory.economic_relationship_intelligence.schema import IERI_VERSION
from knowledge_factory.economic_relationship_intelligence.transmission.orders import (
    transmission_from_entity,
)


def macro_relationships(macro: str, *, as_of: str | None = None) -> dict[str, Any]:
    mid = str(macro or "").lower().replace(" ", "_").replace("-", "_")
    rows = ieri_store.list_relationships(entity=mid, as_of=as_of)
    tx = transmission_from_entity(mid, as_of=as_of)
    return {
        "macro_id": mid,
        "links": [
            {
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
                "time_horizon": r.get("time_horizon"),
            }
            for r in rows
        ],
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
