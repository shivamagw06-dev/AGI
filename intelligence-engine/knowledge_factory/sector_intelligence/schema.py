"""Institutional Sector Intelligence schemas — KF enrichment only.

Reasoning Phases 1–7 and Historical Depth remain untouched.
"""

from __future__ import annotations

from typing import Any

ISI_VERSION = "institutional-sector-intelligence-v1.0.0"
ISI_SCHEMA_VERSION = "isi-schema-v1.0.0"

# Canonical sector universe (Sprint 5 minimum + mapped extras).
SECTOR_UNIVERSE: tuple[str, ...] = (
    "it_services",
    "banks",
    "nbfc",
    "insurance",
    "pharma",
    "healthcare",
    "auto",
    "auto_ancillary",
    "capital_goods",
    "industrials",
    "infrastructure",
    "real_estate",
    "metals",
    "mining",
    "oil_gas",
    "power",
    "utilities",
    "telecom",
    "consumer",
    "fmcg",
    "retail",
    "chemicals",
    "cement",
    "textiles",
    "logistics",
    "media",
    "internet",
)

# Map Knowledge Factory / seed labels → canonical ISI keys.
SECTOR_ALIASES: dict[str, str] = {
    "it_services": "it_services",
    "banks": "banks",
    "bank": "banks",
    "nbfc": "nbfc",
    "insurance": "insurance",
    "pharma": "pharma",
    "healthcare": "healthcare",
    "auto": "auto",
    "auto_ancillary": "auto_ancillary",
    "capital_goods": "capital_goods",
    "industrials": "industrials",
    "infrastructure": "infrastructure",
    "real_estate": "real_estate",
    "metals": "metals",
    "mining": "mining",
    "oil_gas": "oil_gas",
    "energy": "oil_gas",
    "energy_conglomerate": "oil_gas",
    "power": "power",
    "utilities": "utilities",
    "telecom": "telecom",
    "consumer": "consumer",
    "fmcg": "fmcg",
    "retail": "retail",
    "chemicals": "chemicals",
    "specialty_chem": "chemicals",
    "cement": "cement",
    "textiles": "textiles",
    "logistics": "logistics",
    "media": "media",
    "internet": "internet",
    "consumer_internet": "internet",
    "consumer_durables": "consumer",
    "aviation": "logistics",
    "conglomerate": "industrials",
    "diversified": "industrials",
    "capital_markets": "nbfc",
}

CYCLE_STATES = (
    "expansion",
    "peak",
    "slowdown",
    "recovery",
    "contraction",
    "late_cycle",
    "early_cycle",
)


def canonicalize(sector: str | None) -> str | None:
    if not sector:
        return None
    key = str(sector).strip().lower().replace(" ", "_").replace("&", "and")
    key = key.replace("oil_and_gas", "oil_gas")
    return SECTOR_ALIASES.get(key, key if key in SECTOR_UNIVERSE else None)


def sector_envelope(sector: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "isi_schema_version": ISI_SCHEMA_VERSION,
        "isi_version": ISI_VERSION,
        "sector": canonicalize(sector) or sector,
        **payload,
    }
