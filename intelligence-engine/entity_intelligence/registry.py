"""Curated Entity Intelligence registry — exact / alias / private / global.

Deterministic. Never fuzzy-substitutes across unrelated companies.
"""

from __future__ import annotations

from typing import Any, Optional

# Each entity: canonical identity + coverage + forbidden substitutions.
# Aliases are exact lowercase matches (normalized).
ENTITIES: list[dict[str, Any]] = [
    # ---- Covered public India ----
    {
        "id": "ENT_RELIANCE",
        "canonical_name": "Reliance Industries Limited",
        "aliases": ["reliance", "ril", "reliance industries", "reliance industries limited", "reliance industries ltd"],
        "ticker": "RELIANCE",
        "exchange": "NSE",
        "listing": "public",
        "country": "India",
        "sector": "Conglomerate",
        "industry": "oil_gas",
        "coverage": "full_institutional",
        "parent": None,
        "forbid_tickers": ["BHARTIARTL", "RIIL", "RELINFRA"],
    },
    {
        "id": "ENT_TCS",
        "canonical_name": "Tata Consultancy Services",
        "aliases": ["tcs", "tata consultancy", "tata consultancy services"],
        "ticker": "TCS",
        "exchange": "NSE",
        "listing": "public",
        "country": "India",
        "sector": "IT",
        "industry": "it_services",
        "coverage": "full_institutional",
        "forbid_tickers": [],
    },
    {
        "id": "ENT_INFY",
        "canonical_name": "Infosys Limited",
        "aliases": ["infosys", "infy", "infosys limited", "infosys ltd"],
        "ticker": "INFY",
        "exchange": "NSE",
        "listing": "public",
        "country": "India",
        "sector": "IT",
        "industry": "it_services",
        "coverage": "full_institutional",
        "forbid_tickers": [],
    },
    {
        "id": "ENT_HDFCBANK",
        "canonical_name": "HDFC Bank Limited",
        "aliases": ["hdfc bank", "hdfcbank", "hdfc bank limited", "hdfc bank ltd"],
        "ticker": "HDFCBANK",
        "exchange": "NSE",
        "listing": "public",
        "country": "India",
        "sector": "Banking",
        "industry": "private_bank",
        "coverage": "full_institutional",
        "forbid_tickers": ["HDFCLIFE", "HDFCAMC"],
    },
    {
        "id": "ENT_HDFCLIFE",
        "canonical_name": "HDFC Life Insurance",
        "aliases": ["hdfc life", "hdfclife", "hdfc life insurance"],
        "ticker": "HDFCLIFE",
        "exchange": "NSE",
        "listing": "public",
        "country": "India",
        "sector": "Financials",
        "industry": "life_insurance",
        "coverage": "full_institutional",
        "forbid_tickers": ["HDFCBANK", "HDFCAMC"],
    },
    {
        "id": "ENT_HDFCAMC",
        "canonical_name": "HDFC Asset Management Company",
        "aliases": ["hdfc amc", "hdfcamc", "hdfc asset management"],
        "ticker": "HDFCAMC",
        "exchange": "NSE",
        "listing": "public",
        "country": "India",
        "sector": "Financials",
        "industry": "asset_management",
        "coverage": "full_institutional",
        "forbid_tickers": ["HDFCBANK", "HDFCLIFE"],
    },
    {
        "id": "ENT_ASIANPAINT",
        "canonical_name": "Asian Paints Limited",
        "aliases": ["asian paints", "asianpaint", "asian paints limited", "apnt"],
        "ticker": "ASIANPAINT",
        "exchange": "NSE",
        "listing": "public",
        "country": "India",
        "sector": "Consumer",
        "industry": "paints",
        "coverage": "full_institutional",
        "forbid_tickers": [],
    },
    {
        "id": "ENT_DMART",
        "canonical_name": "Avenue Supermarts (DMart)",
        "aliases": ["dmart", "d-mart", "avenue supermarts", "avenue supermarts limited"],
        "ticker": "DMART",
        "exchange": "NSE",
        "listing": "public",
        "country": "India",
        "sector": "Retail",
        "industry": "retail",
        "coverage": "full_institutional",
        "forbid_tickers": [],
    },
    {
        "id": "ENT_INDIGO",
        "canonical_name": "InterGlobe Aviation (IndiGo)",
        "aliases": ["indigo", "indi go", "interglobe", "interglobe aviation", "interglobe aviation limited"],
        "ticker": "INDIGO",
        "exchange": "NSE",
        "listing": "public",
        "country": "India",
        "sector": "Airlines",
        "industry": "airline",
        "coverage": "full_institutional",
        "forbid_tickers": ["BHARTIARTL", "BSE517514"],
    },
    {
        "id": "ENT_BHARTI",
        "canonical_name": "Bharti Airtel Limited",
        "aliases": ["bharti airtel", "airtel", "bharti", "bhartiartl"],
        "ticker": "BHARTIARTL",
        "exchange": "NSE",
        "listing": "public",
        "country": "India",
        "sector": "Telecom",
        "industry": "telecom",
        "coverage": "full_institutional",
        "forbid_tickers": [],
    },
    {
        "id": "ENT_JSWSTEEL",
        "canonical_name": "JSW Steel Limited",
        "aliases": ["jsw steel", "jswsteel"],
        "ticker": "JSWSTEEL",
        "exchange": "NSE",
        "listing": "public",
        "country": "India",
        "sector": "Materials",
        "industry": "steel",
        "coverage": "full_institutional",
        "forbid_tickers": ["JSWENERGY"],
    },
    {
        "id": "ENT_JSWENERGY",
        "canonical_name": "JSW Energy Limited",
        "aliases": ["jsw energy", "jswenergy"],
        "ticker": "JSWENERGY",
        "exchange": "NSE",
        "listing": "public",
        "country": "India",
        "sector": "Utilities",
        "industry": "power",
        "coverage": "full_institutional",
        "forbid_tickers": ["JSWSTEEL"],
    },
    {
        "id": "ENT_TITAN",
        "canonical_name": "Titan Company Limited",
        "aliases": ["titan", "titan company", "titan company limited"],
        "ticker": "TITAN",
        "exchange": "NSE",
        "listing": "public",
        "country": "India",
        "sector": "Consumer",
        "industry": "jewellery",
        "coverage": "full_institutional",
        "forbid_tickers": [],
        "note": "Do not confuse with Titan Biotech",
    },
    {
        "id": "ENT_TITANBIO",
        "canonical_name": "Titan Biotech Limited",
        "aliases": ["titan biotech", "titan biotech limited"],
        "ticker": "TITANBIO",
        "exchange": "BSE",
        "listing": "public",
        "country": "India",
        "sector": "Healthcare",
        "industry": "biotech",
        "coverage": "limited_public_private",
        "forbid_tickers": ["TITAN"],
    },
    {
        "id": "ENT_RELINFRA",
        "canonical_name": "Reliance Infrastructure Limited",
        "aliases": ["reliance infrastructure", "relinfra", "reliance infra"],
        "ticker": "RELINFRA",
        "exchange": "NSE",
        "listing": "public",
        "country": "India",
        "sector": "Infrastructure",
        "industry": "infra",
        "coverage": "limited_public_private",
        "forbid_tickers": ["RELIANCE", "RIIL"],
    },
    {
        "id": "ENT_RIIL",
        "canonical_name": "Reliance Industrial Infrastructure Limited",
        "aliases": ["reliance industrial infrastructure", "riil", "reliance industrial infra"],
        "ticker": "RIIL",
        "exchange": "NSE",
        "listing": "public",
        "country": "India",
        "sector": "Infrastructure",
        "industry": "infra",
        "coverage": "limited_public_private",
        "forbid_tickers": ["RELIANCE", "RELINFRA"],
    },
    # ---- Private / known but insufficient CapIQ institutional ----
    {
        "id": "ENT_AIR_INDIA",
        "canonical_name": "Air India",
        "aliases": ["air india", "airindia", "air india limited"],
        "ticker": None,
        "exchange": None,
        "listing": "private",
        "country": "India",
        "sector": "Airlines",
        "industry": "airline",
        "coverage": "insufficient_institutional",
        "parent": "Tata Group",
        "forbid_tickers": ["BHARTIARTL", "INDIGO", "BSE517514", "AIRAN"],
        "public_facts": [
            "Air India is a privately owned airline under the Tata Group.",
            "It is not interchangeable with Bharti Airtel, IndiGo, or other listed names.",
        ],
    },
    {
        "id": "ENT_FLIPKART",
        "canonical_name": "Flipkart",
        "aliases": ["flipkart", "flipkart internet"],
        "ticker": None,
        "listing": "private",
        "country": "India",
        "sector": "E-commerce",
        "industry": "ecommerce",
        "coverage": "insufficient_institutional",
        "forbid_tickers": [],
    },
    {
        "id": "ENT_BYJUS",
        "canonical_name": "BYJU'S",
        "aliases": ["byju's", "byjus", "byju"],
        "ticker": None,
        "listing": "private",
        "country": "India",
        "sector": "Education",
        "industry": "edtech",
        "coverage": "insufficient_institutional",
        "forbid_tickers": [],
    },
    {
        "id": "ENT_HYPERPURE",
        "canonical_name": "Zomato Hyperpure",
        "aliases": ["zomato hyperpure", "hyperpure"],
        "ticker": None,
        "listing": "private",
        "country": "India",
        "sector": "Food",
        "industry": "b2b_supply",
        "coverage": "insufficient_institutional",
        "parent": "Zomato",
        "forbid_tickers": ["ZOMATO"],
    },
    # ---- Global unsupported (honest coverage refusal) ----
    {
        "id": "ENT_VISA",
        "canonical_name": "Visa",
        "aliases": ["visa"],
        "ticker": None,
        "listing": "public",
        "country": "USA",
        "coverage": "none",
        "forbid_tickers": [],
        "unsupported_global": True,
    },
    {
        "id": "ENT_MASTERCARD",
        "canonical_name": "Mastercard",
        "aliases": ["mastercard", "master card"],
        "ticker": None,
        "listing": "public",
        "country": "USA",
        "coverage": "none",
        "forbid_tickers": [],
        "unsupported_global": True,
    },
    {
        "id": "ENT_COSTCO",
        "canonical_name": "Costco",
        "aliases": ["costco"],
        "ticker": None,
        "listing": "public",
        "country": "USA",
        "coverage": "none",
        "forbid_tickers": [],
        "unsupported_global": True,
    },
    {
        "id": "ENT_TESLA",
        "canonical_name": "Tesla",
        "aliases": ["tesla"],
        "ticker": None,
        "listing": "public",
        "country": "USA",
        "coverage": "none",
        "forbid_tickers": [],
        "unsupported_global": True,
    },
    {
        "id": "ENT_FERRARI",
        "canonical_name": "Ferrari",
        "aliases": ["ferrari"],
        "ticker": None,
        "listing": "public",
        "country": "Italy",
        "coverage": "none",
        "forbid_tickers": [],
        "unsupported_global": True,
    },
    {
        "id": "ENT_TOYOTA",
        "canonical_name": "Toyota",
        "aliases": ["toyota"],
        "ticker": None,
        "listing": "public",
        "country": "Japan",
        "coverage": "none",
        "forbid_tickers": [],
        "unsupported_global": True,
    },
    {
        "id": "ENT_OPENAI",
        "canonical_name": "OpenAI",
        "aliases": ["openai", "open ai"],
        "ticker": None,
        "listing": "private",
        "country": "USA",
        "coverage": "none",
        "forbid_tickers": [],
        "unsupported_global": True,
    },
]

# Ambiguous stems → clarification candidates (never guess).
AMBIGUOUS: dict[str, list[str]] = {
    "hdfc": ["ENT_HDFCBANK", "ENT_HDFCLIFE", "ENT_HDFCAMC"],
    "tata": ["ENT_TCS", "ENT_AIR_INDIA", "ENT_TITAN"],
    "jsw": ["ENT_JSWSTEEL", "ENT_JSWENERGY"],
    "titan": ["ENT_TITAN", "ENT_TITANBIO"],
    "reliance": [],  # default to RIL via alias; infra variants are longer aliases
}

_ALIAS_INDEX: dict[str, dict[str, Any]] = {}
_ID_INDEX: dict[str, dict[str, Any]] = {}


def _rebuild() -> None:
    _ALIAS_INDEX.clear()
    _ID_INDEX.clear()
    for e in ENTITIES:
        _ID_INDEX[e["id"]] = e
        for a in e.get("aliases") or []:
            _ALIAS_INDEX[str(a).strip().lower()] = e
        name = str(e.get("canonical_name") or "").strip().lower()
        if name:
            _ALIAS_INDEX[name] = e
        tk = e.get("ticker")
        if tk:
            _ALIAS_INDEX[str(tk).strip().lower()] = e


_rebuild()


def normalize(text: str) -> str:
    t = (text or "").strip().lower()
    for ch in (",", ".", "?", "!", ";", ":", "'", '"'):
        t = t.replace(ch, " ")
    return " ".join(t.split())


def lookup_exact(token: str) -> Optional[dict[str, Any]]:
    return _ALIAS_INDEX.get(normalize(token))


def get_by_id(eid: str) -> Optional[dict[str, Any]]:
    return _ID_INDEX.get(eid)


def list_entities() -> list[str]:
    return [e["id"] for e in ENTITIES]


def ambiguity_candidates(stem: str) -> list[dict[str, Any]]:
    ids = AMBIGUOUS.get(normalize(stem)) or []
    return [e for eid in ids if (e := get_by_id(eid))]
