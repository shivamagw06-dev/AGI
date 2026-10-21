"""Instrument-type resolution for VPAE.

Company master does not yet carry a first-class instrument_type. Until that
column lands, classify from symbol/name heuristics so ETFs, REITs and InvITs
never inherit equity valuation multiples. Sector labels alone never decide.
"""

from __future__ import annotations

import re
from typing import Any, Optional

INSTRUMENT_TYPES = (
    "EQUITY",
    "ETF",
    "INDEX",
    "REIT",
    "INVIT",
    "ADR",
    "PREFERENCE_SHARE",
    "BOND",
    "MUTUAL_FUND",
    "COMMODITY_ETF",
)

# Symbol-shaped ETF / index product tokens (applied to ticker primarily).
_ETF_SYMBOL = re.compile(
    r"(ETF|BEES|IETF|BETF|GOLDETF|SILVERETF|LIQUIDETF|"
    r"NIFTY|SENSEX|BANKNIFTY|CPSEETF|GILT|"
    r"AUTOBEES|BANKBEES|JUNIORBEES|INFRABEES|PSUBNKBEES|ITBEES|PHARMABEES|"
    r"MID150BEES|NEXT50|MOM30IETF|ALPHAETF|EQUAL50|EQUAL200|"
    r"DIVOPPBEES|CONSUMBEES|FMCGIETF|BANKIETF|AUTOIETF)",
    re.I,
)
_REIT_TOKEN = re.compile(r"\bREIT\b|EMBASSY\s*OFFICE|MINDSPACE|BROOKFIELD\s*REIT|NEXUS\s*SELECT", re.I)
_INVIT_TOKEN = re.compile(r"\bINVIT\b|INDIGRID|IRBINVIT|CUBE\s*HIGHWAYS", re.I)
_MF_TOKEN = re.compile(r"\bMUTUAL\s*FUND\b", re.I)
_INDEX_SYMBOL = re.compile(r"^(NIFTY|SENSEX|BANKNIFTY|FINNIFTY|MIDCPNIFTY)(\d+)?$", re.I)
_ADR_TOKEN = re.compile(r"\bADR\b|\bGDR\b", re.I)
_COMMODITY = re.compile(r"(GOLD|SILVER).*(ETF|BEES)|^(EGOLD|ESILVER|GOLDBEES|SILVERBEES)", re.I)


def resolve_instrument(
    *,
    symbol: str,
    company_name: Optional[str] = None,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    industry_dna: Optional[str] = None,
    master: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Return instrument_type + detection provenance."""
    row = master or {}
    explicit = (
        row.get("instrument_type")
        or row.get("instrument")
        or row.get("security_type")
        or row.get("listing_type")
    )
    if explicit:
        code = str(explicit).strip().upper().replace(" ", "_")
        if code in {"EQ", "EQUITY", "STOCK", "COMMON_STOCK"}:
            code = "EQUITY"
        if code in INSTRUMENT_TYPES:
            return {
                "instrument_type": code,
                "source": "company_master",
                "confidence": "HIGH",
            }

    dna = str(industry_dna or "").strip().lower()
    if dna == "etf":
        return {"instrument_type": "ETF", "source": "industry_dna", "confidence": "HIGH"}
    if dna == "reit":
        return {"instrument_type": "REIT", "source": "industry_dna", "confidence": "HIGH"}
    if dna == "invit":
        return {"instrument_type": "INVIT", "source": "industry_dna", "confidence": "HIGH"}

    sym = str(symbol or "").upper()
    name = str(company_name or row.get("company_name") or "")
    # Name+symbol only — never sector/industry labels (they false-positive ETF tokens).
    identity = f"{sym} {name}".strip()

    if _INVIT_TOKEN.search(identity) or "INVIT" in sym:
        return {"instrument_type": "INVIT", "source": "name_heuristic", "confidence": "HIGH"}
    if _REIT_TOKEN.search(identity) or sym.endswith("REIT"):
        return {"instrument_type": "REIT", "source": "name_heuristic", "confidence": "HIGH"}
    if _ADR_TOKEN.search(identity):
        return {"instrument_type": "ADR", "source": "name_heuristic", "confidence": "MEDIUM"}
    if _INDEX_SYMBOL.match(sym) and not sector:
        return {"instrument_type": "INDEX", "source": "symbol_heuristic", "confidence": "MEDIUM"}
    if _MF_TOKEN.search(identity):
        return {"instrument_type": "MUTUAL_FUND", "source": "name_heuristic", "confidence": "MEDIUM"}
    if _COMMODITY.search(sym) or _COMMODITY.search(name):
        return {"instrument_type": "COMMODITY_ETF", "source": "symbol_heuristic", "confidence": "HIGH"}
    if _ETF_SYMBOL.search(sym) or re.search(r"\bETF\b", name, re.I):
        return {
            "instrument_type": "ETF",
            "source": "symbol_heuristic",
            "confidence": "HIGH" if _ETF_SYMBOL.search(sym) else "MEDIUM",
        }
    # Blank-sector ticker that still looks like a product code (…ETF/BEES already caught).
    if not sector and not industry and not dna and re.search(r"(ETF|BEES|IETF)$", sym, re.I):
        return {"instrument_type": "ETF", "source": "symbol_heuristic", "confidence": "MEDIUM"}

    return {
        "instrument_type": "EQUITY",
        "source": "default",
        "confidence": "MEDIUM" if sector or industry or dna else "LOW",
    }
