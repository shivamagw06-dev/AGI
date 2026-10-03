"""Phase 1 — automatic company / sector detection for SIF."""

from __future__ import annotations

import re
from typing import Any


# Canonical SIF sector ids (Phase 1 minimum set)
SECTOR_IDS = (
    "banks",
    "nbfc",
    "insurance",
    "it_services",
    "software",
    "telecom",
    "retail",
    "fmcg",
    "healthcare",
    "pharma",
    "hospitals",
    "power",
    "utilities",
    "renewables",
    "oil_gas",
    "metals",
    "steel",
    "mining",
    "cement",
    "chemicals",
    "automobile",
    "auto_components",
    "capital_goods",
    "infrastructure",
    "real_estate",
    "airlines",
    "shipping",
    "logistics",
    "defence",
    "media",
    "consumer_internet",
    "conglomerates",
)


# Explicit company → sector inheritance (India institutional coverage + validation namesakes)
COMPANY_SECTOR: dict[str, str] = {
    # Banks
    "HDFCBANK": "banks",
    "ICICIBANK": "banks",
    "IDBI": "banks",
    "SBIN": "banks",
    "AXISBANK": "banks",
    "KOTAKBANK": "banks",
    "INDUSINDBK": "banks",
    "BANDHANBNK": "banks",
    "FEDERALBNK": "banks",
    # NBFC
    "BAJFINANCE": "nbfc",
    "BAJAJFINSV": "nbfc",
    "CHOLAFIN": "nbfc",
    "M&MFIN": "nbfc",
    "MMFIN": "nbfc",
    "SHRIAMFIN": "nbfc",
    "PFC": "nbfc",
    "RECLTD": "nbfc",
    # Insurance
    "SBILIFE": "insurance",
    "HDFCLIFE": "insurance",
    "ICICIPRULI": "insurance",
    "ICICIGI": "insurance",
    "MAXLIFE": "insurance",
    # IT / Software
    "TCS": "it_services",
    "INFY": "it_services",
    "HCLTECH": "it_services",
    "WIPRO": "it_services",
    "TECHM": "it_services",
    "LTIM": "it_services",
    "LTTS": "it_services",
    "PERSISTENT": "it_services",
    "COFORGE": "it_services",
    "MPHASIS": "it_services",
    "OFSS": "software",
    # Telecom
    "BHARTIARTL": "telecom",
    "IDEA": "telecom",
    "RCOM": "telecom",
    # FMCG / Retail
    "HINDUNILVR": "fmcg",
    "ITC": "fmcg",
    "NESTLEIND": "fmcg",
    "BRITANNIA": "fmcg",
    "DABUR": "fmcg",
    "MARICO": "fmcg",
    "ASIANPAINT": "fmcg",  # paints — consumer branded; treated via FMCG-like volume/pricing (also chemicals overlay)
    "DMART": "retail",
    "TRENT": "retail",
    # Pharma / Healthcare / Hospitals
    "SUNPHARMA": "pharma",
    "DRREDDY": "pharma",
    "CIPLA": "pharma",
    "DIVISLAB": "pharma",
    "AUROPHARMA": "pharma",
    "APOLLOHOSP": "hospitals",
    "MAXHEALTH": "hospitals",
    "FORTIS": "hospitals",
    # Power / Utilities / Renewables
    "POWERGRID": "utilities",
    "NTPC": "power",
    "TATAPOWER": "power",
    "ADANIGREEN": "renewables",
    "ADANIPOWER": "power",
    # Oil & Gas / Conglomerate
    "RELIANCE": "conglomerates",
    "ONGC": "oil_gas",
    "IOC": "oil_gas",
    "BPCL": "oil_gas",
    "GAIL": "oil_gas",
    # Metals / Steel / Mining / Cement
    "TATASTEEL": "steel",
    "JSWSTEEL": "steel",
    "SAIL": "steel",
    "HINDALCO": "metals",
    "VEDL": "metals",
    "COALINDIA": "mining",
    "NMDC": "mining",
    "ULTRACEMCO": "cement",
    "AMBUJACEM": "cement",
    "SHREECEM": "cement",
    "ACC": "cement",
    # Chemicals
    "PIDILITIND": "chemicals",
    "UPL": "chemicals",
    "SRF": "chemicals",
    # Auto
    "MARUTI": "automobile",
    "TATAMOTORS": "automobile",
    "M&M": "automobile",
    "MM": "automobile",
    "BAJAJ-AUTO": "automobile",
    "BAJAJAUTO": "automobile",
    "HEROMOTOCO": "automobile",
    "EICHERMOT": "automobile",
    "MOTHERSON": "auto_components",
    "BOSCHLTD": "auto_components",
    # Capital goods / Infra / Realty
    "LT": "capital_goods",
    "SIEMENS": "capital_goods",
    "ABB": "capital_goods",
    "IRCTC": "infrastructure",
    "DLF": "real_estate",
    "GODREJPROP": "real_estate",
    # Airlines / Shipping / Logistics
    "INDIGO": "airlines",
    "SPICEJET": "airlines",
    "GESHIP": "shipping",
    "BLUEDART": "logistics",
    "TCI": "logistics",
    # Defence / Media / Consumer internet
    "HAL": "defence",
    "BEL": "defence",
    "ZEEL": "media",
    "SUNTV": "media",
    "NAUKRI": "consumer_internet",
    "ZOMATO": "consumer_internet",
    "PAYTM": "consumer_internet",
    "NYKAA": "consumer_internet",
    # Conglomerates
    "ADANIENT": "conglomerates",
    "ADANIPORTS": "infrastructure",
}

COMPANY_ALIASES: dict[str, str] = {
    "hdfc bank": "HDFCBANK",
    "hdfcbank": "HDFCBANK",
    "icici bank": "ICICIBANK",
    "icici": "ICICIBANK",
    "idbi": "IDBI",
    "idbi bank": "IDBI",
    "idbi bank ltd": "IDBI",
    "idbi bank limited": "IDBI",
    "sbi": "SBIN",
    "infosys": "INFY",
    "tcs": "TCS",
    "wipro": "WIPRO",
    "hcl": "HCLTECH",
    "hcltech": "HCLTECH",
    "ultratech": "ULTRACEMCO",
    "ultratech cement": "ULTRACEMCO",
    "asian paints": "ASIANPAINT",
    "asian paint": "ASIANPAINT",
    "reliance": "RELIANCE",
    "reliance industries": "RELIANCE",
    "sun pharma": "SUNPHARMA",
    "tata steel": "TATASTEEL",
    "power grid": "POWERGRID",
    "powergrid": "POWERGRID",
    "maruti": "MARUTI",
    "bharti": "BHARTIARTL",
    "airtel": "BHARTIARTL",
}

SECTOR_QUERY_HINTS: dict[str, tuple[str, ...]] = {
    "banks": ("bank", "nim", "casa", "gnpa", "nnpa", "cet1", "credit cost", "deposit"),
    "nbfc": ("nbfc", "aumm", "disbursement", "stage 3", "hfc"),
    "insurance": ("insurance", "vnb", "embedded value", "solvency", "persistenc"),
    "it_services": ("it services", "infosys", "tcs", "attrition", "utilisation", "deal win", "genai"),
    "software": ("saas", "arr", "rule of 40", "software product"),
    "telecom": ("telecom", "arpu", "subscriber", "spectrum"),
    "fmcg": ("fmcg", "volume growth", "rural demand", "asian paints", "hindustan unilever"),
    "retail": ("retail", "same store", "footfall", "dmart"),
    "pharma": ("pharma", "usfda", "anda", "api"),
    "hospitals": ("hospital", "occupancy", "arpo"),
    "power": ("power generation", "plant load", "ntpc"),
    "utilities": ("utility", "transmission", "power grid", "regulated return"),
    "renewables": ("renewable", "solar", "wind", "green energy"),
    "oil_gas": ("oil", "crude", "refining", "grm", "upstream"),
    "metals": ("aluminium", "copper", "non-ferrous"),
    "steel": ("steel", "spread", "hrc", "iron ore"),
    "mining": ("mining", "coal india", "ore production"),
    "cement": ("cement", "ultratech", "ebitda/tonne", "capacity utilisation"),
    "chemicals": ("chemical", "specialty chemical"),
    "automobile": ("auto", "pv volume", "cv cycle", "maruti"),
    "auto_components": ("auto component", "ancillar"),
    "capital_goods": ("capital goods", "order book", "industrial capex"),
    "infrastructure": ("infrastructure", "epc", "roads"),
    "real_estate": ("real estate", "pre-sales", "realty"),
    "airlines": ("airline", "ask", "rask", "load factor"),
    "shipping": ("shipping", "freight rate", "tanker"),
    "logistics": ("logistics", "warehous"),
    "defence": ("defence", "defense", "indigenisation"),
    "media": ("media", "advertising", "subscription"),
    "consumer_internet": ("internet", "gmv", "take rate", "zomato"),
    "conglomerates": ("conglomerate", "sotp", "reliance"),
}


def resolve_ticker(query: str, ticker: str | None = None) -> str | None:
    if ticker:
        t = ticker.strip().upper()
        if t in COMPANY_SECTOR:
            return t
    q = (query or "").strip().lower()
    for alias, sym in COMPANY_ALIASES.items():
        if alias in q:
            return sym
    # bare ticker tokens
    for tok in re.findall(r"[A-Za-z0-9&-]+", query or ""):
        up = tok.upper()
        if up in COMPANY_SECTOR:
            return up
    # BANK suffix heuristic
    for tok in re.findall(r"[A-Za-z0-9]+", (query or "").upper()):
        if tok.endswith("BANK") and tok in COMPANY_SECTOR:
            return tok
    return ticker.strip().upper() if ticker else None


def detect_sector(query: str, ticker: str | None = None) -> dict[str, Any]:
    """Detect sector_id + company for a query."""
    resolved = resolve_ticker(query, ticker)
    if resolved and resolved in COMPANY_SECTOR:
        return {
            "sector_id": COMPANY_SECTOR[resolved],
            "ticker": resolved,
            "method": "company_map",
            "confidence": 0.95,
        }
    q = (query or "").lower()
    scores: list[tuple[str, int]] = []
    for sid, hints in SECTOR_QUERY_HINTS.items():
        score = sum(1 for h in hints if h in q)
        if score:
            scores.append((sid, score))
    scores.sort(key=lambda x: -x[1])
    if scores:
        return {
            "sector_id": scores[0][0],
            "ticker": resolved,
            "method": "query_hints",
            "confidence": min(0.9, 0.45 + 0.15 * scores[0][1]),
            "alternates": [{"sector_id": s, "score": sc} for s, sc in scores[1:4]],
        }
    return {
        "sector_id": None,
        "ticker": resolved,
        "method": "unresolved",
        "confidence": 0.0,
    }
