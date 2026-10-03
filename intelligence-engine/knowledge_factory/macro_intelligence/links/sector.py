"""Sector ↔ macro knowledge links (knowledge only; does not modify ISI)."""

from __future__ import annotations

from typing import Any

from knowledge_factory.macro_intelligence import store as imi_store
from knowledge_factory.macro_intelligence.playbooks.catalog import all_regime_playbooks
from knowledge_factory.macro_intelligence.producers.impacts import relationship
from knowledge_factory.macro_intelligence.schema import IMI_VERSION

SECTORS = (
    "banks",
    "nbfc",
    "insurance",
    "it_services",
    "fmcg",
    "metals",
    "utilities",
    "real_estate",
    "logistics",
    "oil_gas",
    "chemicals",
    "consumer",
    "auto",
    "pharma",
)

_MACROS = ("interest_rates", "oil", "inflation", "usd", "dxy")


def sector_macro_link(sector: str) -> dict[str, Any]:
    primary: list[dict[str, Any]] = []
    secondary: list[dict[str, Any]] = []
    for macro in _MACROS:
        rel = relationship(macro, sector)
        if not rel.get("found"):
            continue
        row = {
            "macro": macro,
            "direction": rel.get("direction"),
            "strength": rel.get("strength"),
            "confidence": rel.get("confidence"),
            "historical_validation": rel.get("historical_validation"),
        }
        if float(rel.get("strength") or 0) >= 2:
            primary.append(row)
        else:
            secondary.append(row)

    preferred_regimes: list[str] = []
    weak_regimes: list[str] = []
    for regime, pb in all_regime_playbooks().items():
        winners = [str(x).lower() for x in (pb.get("typical_winners") or [])]
        losers = [str(x).lower() for x in (pb.get("typical_losers") or [])]
        s = sector.lower()
        if any(s == w or s in w or w in s for w in winners):
            preferred_regimes.append(regime)
        if any(s == w or s in w or w in s for w in losers):
            weak_regimes.append(regime)

    return {
        "link_type": "sector_macro",
        "sector": sector,
        "primary_macro_drivers": primary,
        "secondary_drivers": secondary,
        "historical_sector_rotation": {
            "preferred_regimes": preferred_regimes,
            "weak_regimes": weak_regimes,
        },
        "historical_macro_performance": {
            "relationship_count": len(primary) + len(secondary),
        },
        "preferred_macro_regimes": preferred_regimes,
        "weak_macro_regimes": weak_regimes,
        "imi_version": IMI_VERSION,
        "knowledge_only": True,
        "does_not_modify_isi": True,
        "fabricated": False,
    }


def compile_sector_links(sectors: list[str] | None = None) -> dict[str, Any]:
    sectors = list(sectors or SECTORS)
    links = {s: sector_macro_link(s) for s in sectors}
    payload = {
        "kind": "sector_macro",
        "n": len(links),
        "links": links,
        "imi_version": IMI_VERSION,
        "knowledge_only": True,
        "does_not_modify_isi": True,
    }
    imi_store.put_links("sector", payload)
    return payload
