"""Deterministic company → sector map (soft, extendable)."""

from __future__ import annotations

COMPANY_SECTOR: dict[str, str] = {
    "HDFCBANK": "banks",
    "ICICIBANK": "banks",
    "SBIN": "banks",
    "KOTAKBANK": "banks",
    "AXISBANK": "banks",
    "INFY": "it_services",
    "TCS": "it_services",
    "WIPRO": "it_services",
    "HCLTECH": "it_services",
    "TECHM": "it_services",
    "RELIANCE": "conglomerates",
    "INDIGO": "airlines",
    "ASIANPAINT": "consumer_staples",
    "HINDUNILVR": "consumer_staples",
    "ITC": "consumer_staples",
    "TITAN": "consumer_staples",
    "MARUTI": "auto",
    "TATASTEEL": "steel",
    "JSWSTEEL": "steel",
    "ULTRACEMCO": "cement",
    "AMBUJACEM": "cement",
    "SHREECEM": "cement",
    "APOLLOHOSP": "hospitals",
    "MAXHEALTH": "hospitals",
    "DLF": "real_estate",
    "BHARTIARTL": "telecom",
    "NTPC": "utilities",
    "POWERGRID": "utilities",
    "BAJFINANCE": "nbfc",
    "HDFCLIFE": "insurance",
    "SBILIFE": "insurance",
}


def sector_for_company(ticker: str | None) -> str | None:
    if not ticker:
        return None
    return COMPANY_SECTOR.get(str(ticker).upper().strip())
