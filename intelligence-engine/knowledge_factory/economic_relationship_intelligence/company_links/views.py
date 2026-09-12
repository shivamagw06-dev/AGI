"""Company relationship views — suppliers, customers, competitors, etc."""

from __future__ import annotations

from typing import Any

from knowledge_factory.economic_relationship_intelligence import store as ieri_store
from knowledge_factory.economic_relationship_intelligence.schema import IERI_VERSION


_BUCKETS = {
    "suppliers": ("supplier",),
    "major_customers": ("customer",),
    "distribution_network": ("distributor",),
    "competitors": ("competitor",),
    "strategic_partners": ("partner",),
    "joint_ventures": ("jv",),
    "commodity_inputs": ("commodity_exposure", "oil_sensitivity", "coal_sensitivity", "gas_sensitivity", "steel_sensitivity", "import_dependency"),
    "commodity_outputs": ("export_dependency",),
    "import_sources": ("import_dependency",),
    "export_markets": ("export_dependency",),
    "bank_relationships": ("credit_dependency",),
    "industry_relationships": ("upstream_industry", "downstream_industry", "supporting_industry"),
    "government_relationships": ("government_dependency", "policy_dependency"),
    "infrastructure_dependencies": (
        "power_dependency",
        "water_dependency",
        "transport_dependency",
        "logistics_dependency",
    ),
}


def company_relationships(ticker: str, *, as_of: str | None = None) -> dict[str, Any]:
    t = str(ticker or "").upper()
    rows = ieri_store.list_relationships(entity=t, as_of=as_of)
    buckets: dict[str, list[dict[str, Any]]] = {k: [] for k in _BUCKETS}
    other: list[dict[str, Any]] = []
    for r in rows:
        rtype = str(r.get("relationship_type") or "")
        placed = False
        for bucket, types in _BUCKETS.items():
            if rtype in types:
                buckets[bucket].append(_brief(r, t))
                placed = True
        if not placed:
            other.append(_brief(r, t))

    # Soft industry map
    industry_id = None
    try:
        from knowledge_factory.industry_intelligence import store as iivi_store

        industry_id = iivi_store.get_company_industry(t)
    except Exception:
        industry_id = None

    return {
        "ticker": t,
        "industry_id": industry_id,
        "relationships": buckets,
        "other": other,
        "n": len(rows),
        "as_of": as_of,
        "version": IERI_VERSION,
        "fabricated": False,
    }


def _brief(r: dict[str, Any], ticker: str) -> dict[str, Any]:
    counterpart = r.get("target_entity") if str(r.get("source_entity")).upper() == ticker else r.get("source_entity")
    if str(r.get("source_entity")).upper() == ticker:
        counterpart_ref = r.get("target_ref")
    else:
        counterpart_ref = r.get("source_ref")
    return {
        "relationship_id": r.get("relationship_id"),
        "counterpart": counterpart,
        "counterpart_ref": counterpart_ref,
        "relationship_type": r.get("relationship_type"),
        "semantics": r.get("semantics"),
        "direction": r.get("direction"),
        "strength": r.get("strength"),
        "confidence": r.get("confidence"),
        "evidence": r.get("evidence"),
        "source": r.get("source"),
        "available_from": r.get("available_from"),
        "shock_direction": r.get("shock_direction"),
        "transmission_order": r.get("transmission_order"),
    }
