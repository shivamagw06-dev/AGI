"""Seed fixtures for offline Knowledge Factory operation.

Built from institutional_reasoning.fundamentals primitives when available;
never invents PE ratios — only primitives + returns.
"""

from __future__ import annotations

from typing import Any


def company_universe() -> list[str]:
    try:
        from institutional_reasoning.fundamentals.primitives import covered_entities

        return list(covered_entities())
    except Exception:
        return ["INFY", "TCS", "WIPRO", "HCLTECH", "TECHM", "HDFCBANK", "ICICIBANK", "RELIANCE", "ZOMATO"]


def primitive_panel(entity: str) -> dict[str, Any] | None:
    try:
        from institutional_reasoning.fundamentals.primitives import primitive_panel as pp

        panel = pp(entity)
        if not panel:
            return None
        return {"entity": entity.upper(), "fields": panel, "provider": "fixture"}
    except Exception:
        return None


def price_series(entity: str) -> list[dict[str, Any]]:
    try:
        from institutional_reasoning.fundamentals.market_series import monthly_returns

        rets = monthly_returns(entity) or []
    except Exception:
        rets = []
    # Synthetic month-end closes from returns (index 100)
    px = 100.0
    out = []
    for i, r in enumerate(rets):
        px = round(px * (1.0 + r / 100.0), 4)
        out.append({"date": f"2024-{(i % 12) + 1:02d}-28", "close": px, "return_pct": r})
    return out


def sector_map() -> dict[str, str]:
    """Company → sector affinity. Tier-2 Nifty 500 merged over Tier-1 seed."""
    base = {
        "ABB": "industrials",
        "ADANIENT": "conglomerate",
        "ADANIGREEN": "utilities",
        "ADANIPORTS": "infrastructure",
        "ALKEM": "pharma",
        "AMBUJACEM": "cement",
        "APOLLOHOSP": "healthcare",
        "ASIANPAINT": "fmcg",
        "AUROPHARMA": "pharma",
        "AXISBANK": "banks",
        "BAJAJ-AUTO": "auto",
        "BAJAJFINSV": "nbfc",
        "BAJFINANCE": "nbfc",
        "BANKBARODA": "banks",
        "BEL": "industrials",
        "BERGEPAINT": "fmcg",
        "BHARTIARTL": "telecom",
        "BOSCHLTD": "auto",
        "BPCL": "energy",
        "BRITANNIA": "fmcg",
        "CANBK": "banks",
        "CHOLAFIN": "nbfc",
        "CIPLA": "pharma",
        "COALINDIA": "energy",
        "COLPAL": "fmcg",
        "DABUR": "fmcg",
        "DIVISLAB": "pharma",
        "DLF": "real_estate",
        "DMART": "retail",
        "DRREDDY": "pharma",
        "EICHERMOT": "auto",
        "GODREJCP": "fmcg",
        "GRASIM": "diversified",
        "HAL": "industrials",
        "HAVELLS": "consumer_durables",
        "HCLTECH": "it_services",
        "HDFCBANK": "banks",
        "HDFCLIFE": "insurance",
        "HEROMOTOCO": "auto",
        "HINDALCO": "metals",
        "HINDUNILVR": "fmcg",
        "ICICIBANK": "banks",
        "ICICIGI": "insurance",
        "ICICIPRULI": "insurance",
        "INDHOTEL": "consumer",
        "INDIGO": "aviation",
        "INDUSINDBK": "banks",
        "INFY": "it_services",
        "IOC": "energy",
        "IRCTC": "consumer",
        "ITC": "fmcg",
        "JINDALSTEL": "metals",
        "JSWSTEEL": "metals",
        "LT": "industrials",
        "LTIM": "it_services",
        "LUPIN": "pharma",
        "M&M": "auto",
        "MARICO": "fmcg",
        "MARUTI": "auto",
        "MAXHEALTH": "healthcare",
        "MUTHOOTFIN": "nbfc",
        "NAUKRI": "consumer_internet",
        "NESTLEIND": "fmcg",
        "NHPC": "utilities",
        "NMDC": "metals",
        "NTPC": "utilities",
        "OFSS": "it_services",
        "ONGC": "energy",
        "PAGEIND": "consumer",
        "PERSISTENT": "it_services",
        "PETRONET": "energy",
        "PFC": "nbfc",
        "PIDILITIND": "specialty_chem",
        "POLYCAB": "industrials",
        "POWERGRID": "utilities",
        "RECLTD": "nbfc",
        "RELIANCE": "energy_conglomerate",
        "SAIL": "metals",
        "SBICARD": "nbfc",
        "SBILIFE": "insurance",
        "SBIN": "banks",
        "SHREECEM": "cement",
        "SHRIRAMFIN": "nbfc",
        "SIEMENS": "industrials",
        "SRF": "specialty_chem",
        "SUNPHARMA": "pharma",
        "TATACONSUM": "fmcg",
        "TATAMOTORS": "auto",
        "TATASTEEL": "metals",
        "TCS": "it_services",
        "TECHM": "it_services",
        "TITAN": "consumer",
        "TRENT": "retail",
        "TVSMOTOR": "auto",
        "ULTRACEMCO": "cement",
        "VBL": "fmcg",
        "WIPRO": "it_services",
        "YESBANK": "banks",
        "ZOMATO": "consumer_internet",
        "ZYDUSLIFE": "pharma",
    }
    try:
        from knowledge_factory.nifty500_universe import NIFTY_500_SECTOR

        # Tier-2 overlays — same Infosys-class sector affinity for all 500.
        return {**base, **NIFTY_500_SECTOR}
    except Exception:
        return base

def macro_fixture() -> dict[str, Any]:
    return {
        "repo_rate": 0.065,
        "cpi": 0.045,
        "usd_inr": 83.5,
        "us_10y": 0.042,
        "us_cpi": 0.032,
        "unemployment_us": 0.039,
        "oil_brent": 82.0,
        "gdp_india_growth": 0.07,
        "pmi_india": 54.2,
    }


def filings_fixture(entity: str) -> list[dict[str, Any]]:
    e = entity.upper()
    return [
        {"filing_id": f"{e}-AR-2025", "title": "Annual Report FY25", "date": "2025-06-15", "type": "annual_report"},
        {"filing_id": f"{e}-Q4-2025", "title": "Q4 Results", "date": "2025-04-20", "type": "earnings"},
        {"filing_id": f"{e}-DIV-2025", "title": "Dividend Declaration", "date": "2025-05-10", "type": "dividend"},
    ]


def groww_book_fixture() -> dict[str, Any]:
    return {
        "holdings": [
            {"symbol": "INFY", "weight": 0.08, "sector": "it_services"},
            {"symbol": "TCS", "weight": 0.10, "sector": "it_services"},
            {"symbol": "HDFCBANK", "weight": 0.11, "sector": "banks"},
        ],
        "sector_allocation": {"it_services": 0.18, "banks": 0.11},
    }
