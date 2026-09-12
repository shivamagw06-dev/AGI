"""Attach institutional entity context (company/sector/peers/index)."""

from __future__ import annotations

from typing import Any

# Soft peer maps for common Indian names / tickers
_PEERS: dict[str, list[str]] = {
    "HDFCBANK": ["ICICI Bank", "Axis Bank", "Kotak Mahindra Bank", "SBI"],
    "ICICIBANK": ["HDFC Bank", "Axis Bank", "Kotak Mahindra Bank", "SBI"],
    "INFY": ["TCS", "Wipro", "HCL Tech", "Tech Mahindra"],
    "TCS": ["Infosys", "Wipro", "HCL Tech", "Tech Mahindra"],
    "RELIANCE": ["ONGC", "IOC", "BPCL"],
    "SBIN": ["HDFC Bank", "ICICI Bank", "Axis Bank", "PNB"],
}

_SECTOR_DEFAULTS: dict[str, dict[str, Any]] = {
    "Bank": {
        "sector": "Financials / Banks",
        "industry": "Private Sector Bank",
        "index_membership": ["Nifty Bank", "Nifty 50"],
        "business_model": "Retail + wholesale banking franchise",
        "lifecycle": "Mature growth",
    },
    "IT": {
        "sector": "Information Technology",
        "industry": "IT Services",
        "index_membership": ["Nifty IT", "Nifty 50"],
        "business_model": "Global IT services / digital",
        "lifecycle": "Mature growth",
    },
}


def detect_entity_context(
    question: str,
    *,
    entity_resolution: dict[str, Any] | None = None,
    research_objective: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ere = entity_resolution or {}
    primary = ere.get("primary_entity") or ere.get("canonical_entity") or {}
    if not primary and ere.get("entity"):
        primary = {
            "canonical_name": ere.get("entity"),
            "entity_type": ere.get("entity_type"),
            "ticker": ere.get("ticker"),
            "sector": ere.get("sector"),
            "industry": ere.get("industry"),
        }
    # Soft resolve via ERE if empty
    if not primary.get("canonical_name") and not primary.get("ticker"):
        try:
            from entity_resolution.canonical_resolver import resolve_question

            row = resolve_question(question or "", {"use_cache": True})
            if not row.get("needs_clarification"):
                primary = row.get("canonical_entity") or {
                    "canonical_name": row.get("entity"),
                    "entity_type": row.get("entity_type"),
                    "ticker": row.get("ticker"),
                    "sector": row.get("sector"),
                    "industry": row.get("industry"),
                }
                ere = {**ere, **row}
        except Exception:
            pass

    ticker = (primary.get("ticker") or "").upper() or None
    name = primary.get("canonical_name") or primary.get("name") or ere.get("entity")
    etype = primary.get("entity_type") or ere.get("entity_type")
    sector = primary.get("sector") or ere.get("sector")
    industry = primary.get("industry") or ere.get("industry")

    # Heuristic fill from question text when ERE sparse
    q = (question or "").lower()
    if not name:
        if "nifty it" in q:
            name, etype, sector = "Nifty IT", "Sector Index", "Information Technology"
        elif "hdfc bank" in q:
            name, ticker, etype = "HDFC Bank", "HDFCBANK", "Company"
        elif "infosys" in q or " infy" in q:
            name, ticker, etype = "Infosys", "INFY", "Company"

    defaults: dict[str, Any] = {}
    if ticker in {"HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK"} or (
        sector and "bank" in str(sector).lower()
    ) or (name and "bank" in str(name).lower()):
        defaults = dict(_SECTOR_DEFAULTS["Bank"])
    elif ticker in {"INFY", "TCS", "WIPRO", "HCLTECH"} or (etype == "Sector Index" and name and "IT" in str(name)):
        defaults = dict(_SECTOR_DEFAULTS["IT"])

    peers = list(_PEERS.get(ticker or "", []))
    if not peers and "bank" in str(name or "").lower():
        peers = list(_PEERS["HDFCBANK"])

    market_cap = primary.get("market_cap_bucket") or ("Large Cap" if etype == "Company" else None)

    return {
        "entity": name,
        "entity_type": etype,
        "ticker": ticker,
        "sector": sector or defaults.get("sector"),
        "industry": industry or defaults.get("industry"),
        "peers": peers,
        "index_membership": defaults.get("index_membership") or primary.get("index_membership") or [],
        "market_cap": market_cap,
        "lifecycle": defaults.get("lifecycle") or primary.get("lifecycle"),
        "business_model": defaults.get("business_model") or primary.get("business_model"),
        "knowledge_graph_id": primary.get("knowledge_graph_id") or ere.get("knowledge_graph_id"),
        "required": bool(name),
        "confidence": 0.95 if name and ticker else (0.88 if name else 0.55),
    }
