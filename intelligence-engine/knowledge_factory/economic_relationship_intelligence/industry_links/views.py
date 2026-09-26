"""Industry relationship views."""

from __future__ import annotations

from typing import Any

from knowledge_factory.economic_relationship_intelligence import store as ieri_store
from knowledge_factory.economic_relationship_intelligence.schema import IERI_VERSION

_BUCKETS = {
    "upstream_industries": ("upstream_industry",),
    "downstream_industries": ("downstream_industry",),
    "supporting_industries": ("supporting_industry",),
    "complementary_industries": ("complementary_industry",),
    "substitute_industries": ("substitute_industry",),
    "commodity_inputs": (
        "commodity_exposure",
        "oil_sensitivity",
        "coal_sensitivity",
        "gas_sensitivity",
        "steel_sensitivity",
        "import_dependency",
        "power_dependency",
    ),
    "demand_sources": ("customer",),
    "supply_sources": ("supplier",),
    "government_dependencies": ("government_dependency", "policy_dependency"),
    "macro_dependencies": (
        "interest_rate_sensitivity",
        "inflation_sensitivity",
        "fx_sensitivity",
        "credit_dependency",
    ),
}


def industry_relationships(industry: str, *, as_of: str | None = None) -> dict[str, Any]:
    iid = str(industry or "").lower().replace(" ", "_").replace("-", "_")
    rows = ieri_store.list_relationships(entity=iid, as_of=as_of)
    buckets: dict[str, list[dict[str, Any]]] = {k: [] for k in _BUCKETS}
    other: list[dict[str, Any]] = []
    for r in rows:
        rtype = str(r.get("relationship_type") or "")
        placed = False
        for bucket, types in _BUCKETS.items():
            if rtype in types:
                buckets[bucket].append(
                    {
                        "relationship_id": r.get("relationship_id"),
                        "source": r.get("source_entity"),
                        "target": r.get("target_entity"),
                        "relationship_type": rtype,
                        "semantics": r.get("semantics"),
                        "strength": r.get("strength"),
                        "confidence": r.get("confidence"),
                        "evidence": r.get("evidence"),
                        "transmission_order": r.get("transmission_order"),
                        "shock_direction": r.get("shock_direction"),
                    }
                )
                placed = True
        if not placed:
            other.append(
                {
                    "relationship_id": r.get("relationship_id"),
                    "relationship_type": rtype,
                    "source": r.get("source_entity"),
                    "target": r.get("target_entity"),
                    "semantics": r.get("semantics"),
                    "confidence": r.get("confidence"),
                }
            )
    return {
        "industry_id": iid,
        "relationships": buckets,
        "other": other,
        "n": len(rows),
        "as_of": as_of,
        "version": IERI_VERSION,
        "fabricated": False,
    }
