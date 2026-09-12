"""Mandatory benchmark companies for ACS Level 16."""

from __future__ import annotations

from typing import Any

BENCHMARK_COMPANIES: list[dict[str, Any]] = [
    # Banks
    {"ticker": "HDFCBANK", "name": "HDFC Bank", "sector": "Banks"},
    {"ticker": "ICICIBANK", "name": "ICICI Bank", "sector": "Banks"},
    {"ticker": "SBIN", "name": "SBI", "sector": "Banks"},
    {"ticker": "AXISBANK", "name": "Axis Bank", "sector": "Banks"},
    # FMCG
    {"ticker": "NESTLEIND", "name": "Nestlé India", "sector": "FMCG"},
    {"ticker": "HINDUNILVR", "name": "HUL", "sector": "FMCG"},
    {"ticker": "ITC", "name": "ITC", "sector": "FMCG"},
    # IT
    {"ticker": "TCS", "name": "TCS", "sector": "IT"},
    {"ticker": "INFY", "name": "Infosys", "sector": "IT"},
    {"ticker": "TECHM", "name": "Tech Mahindra", "sector": "IT"},
    # Consumer Internet
    {"ticker": "ETERNAL", "name": "Eternal", "sector": "Consumer Internet"},
    {"ticker": "NYKAA", "name": "Nykaa", "sector": "Consumer Internet"},
    # Auto
    {"ticker": "MARUTI", "name": "Maruti", "sector": "Auto"},
    {"ticker": "TATAMOTORS", "name": "Tata Motors", "sector": "Auto"},
    # Industrials
    {"ticker": "LT", "name": "L&T", "sector": "Industrials"},
    {"ticker": "SIEMENS", "name": "Siemens", "sector": "Industrials"},
    # Global
    {"ticker": "AAPL", "name": "Apple", "sector": "Global"},
    {"ticker": "MSFT", "name": "Microsoft", "sector": "Global"},
    {"ticker": "AMZN", "name": "Amazon", "sector": "Global"},
    {"ticker": "GOOGL", "name": "Alphabet", "sector": "Global"},
    {"ticker": "META", "name": "Meta", "sector": "Global"},
    {"ticker": "NVDA", "name": "Nvidia", "sector": "Global"},
    {"ticker": "BRK.B", "name": "Berkshire", "sector": "Global"},
    {"ticker": "JPM", "name": "JPMorgan", "sector": "Global"},
    {"ticker": "COST", "name": "Costco", "sector": "Global"},
    {"ticker": "KO", "name": "Coca-Cola", "sector": "Global"},
]


def all_benchmarks() -> list[dict[str, Any]]:
    return list(BENCHMARK_COMPANIES)


def by_sector() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for c in BENCHMARK_COMPANIES:
        out.setdefault(c["sector"], []).append(c)
    return out
