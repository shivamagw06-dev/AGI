"""CCI-01 Relationship Engine — discover relationships for an entity via providers."""

from __future__ import annotations

from typing import Any, Optional

from institutional_cross_company.models import InstitutionalRelationship
from institutional_cross_company.relationship_registry import catalog, discover_all, get
from institutional_cross_company.schema import TYPE_TO_CATEGORY
from institutional_cross_company.validator import validate_relationships


def relationships_for_company(
    ticker: str,
    *,
    portfolio_id: str = "agi-core-equity",
    categories: Optional[list[str]] = None,
) -> list[InstitutionalRelationship]:
    t = str(ticker or "").upper().strip()
    ctx = {"ticker": t, "portfolio_id": portfolio_id}
    rels = discover_all(ctx)
    if categories:
        allowed = {c.lower() for c in categories}
        rels = [r for r in rels if (r.category or TYPE_TO_CATEGORY.get(r.relationship_type, "")).lower() in allowed]
    ok, _ = validate_relationships(rels)
    return ok


def relationships_for_sector(sector: str) -> list[InstitutionalRelationship]:
    from institutional_cross_company.schema import ECOSYSTEMS

    s = str(sector or "").strip().lower()
    out: list[InstitutionalRelationship] = []
    for eco in ECOSYSTEMS.values():
        label = str(eco.get("sector") or "").lower()
        industry = str(eco.get("industry") or "").lower()
        cluster = str(eco.get("cluster") or "").lower()
        if s and s not in {label, industry, cluster} and s not in label and s not in industry:
            continue
        for member in eco.get("members") or ():
            out.extend(relationships_for_company(str(member)))
    # Dedupe
    seen: set[str] = set()
    unique: list[InstitutionalRelationship] = []
    for r in out:
        if r.relationship_id in seen:
            continue
        seen.add(r.relationship_id)
        unique.append(r)
    return unique


def relationships_for_macro(driver: str) -> list[InstitutionalRelationship]:
    d = str(driver or "").lower().strip().replace(" ", "_")
    aliases = {
        "rates": "interest_rates",
        "interest": "interest_rates",
        "rate_cut": "interest_rates",
        "rbi": "interest_rates",
        "crude": "oil",
        "currency": "fx",
        "usd": "fx",
        "credit": "credit_cycle",
    }
    d = aliases.get(d, d)
    reg = get(d)
    if reg and reg.discover:
        rels = reg.discover({"macro_driver": d}) or []
        ok, _ = validate_relationships(rels)
        return ok
    return []


def group_by_type(rels: list[InstitutionalRelationship]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for r in rels:
        grouped.setdefault(r.relationship_type, []).append(r.to_dict())
    return grouped


def provider_catalog() -> list[dict[str, Any]]:
    return catalog()
