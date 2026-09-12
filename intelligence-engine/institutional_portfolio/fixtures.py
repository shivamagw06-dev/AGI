"""Demo Investment Office portfolio — Indian private banks core book."""

from __future__ import annotations

from typing import Any

from institutional_portfolio.portfolio_entities import HoldingRecord
from institutional_portfolio.schema import DEFAULT_PORTFOLIO_ID

# Weights sum to 0.92; cash 0.08
DEMO_HOLDINGS_RAW: tuple[dict[str, Any], ...] = (
    {
        "ticker": "HDFCBANK",
        "company": "HDFC Bank",
        "weight": 0.28,
        "market_value": 2800000,
        "quantity": 1000,
        "sector": "Banking",
        "industry": "Private Banks",
        "country": "IN",
    },
    {
        "ticker": "ICICIBANK",
        "company": "ICICI Bank",
        "weight": 0.26,
        "market_value": 2600000,
        "quantity": 1200,
        "sector": "Banking",
        "industry": "Private Banks",
        "country": "IN",
    },
    {
        "ticker": "AXISBANK",
        "company": "Axis Bank",
        "weight": 0.22,
        "market_value": 2200000,
        "quantity": 1500,
        "sector": "Banking",
        "industry": "Private Banks",
        "country": "IN",
    },
    {
        "ticker": "KOTAKBANK",
        "company": "Kotak Mahindra Bank",
        "weight": 0.16,
        "market_value": 1600000,
        "quantity": 800,
        "sector": "Banking",
        "industry": "Private Banks",
        "country": "IN",
    },
)

DEMO_PORTFOLIO = {
    "portfolio_id": DEFAULT_PORTFOLIO_ID,
    "name": "AGI Core Equity",
    "cash_weight": 0.08,
    "base_currency": "INR",
    "benchmark": "NIFTY BANK",
    "description": "Phase 4 demo book — private bank core for Portfolio Knowledge Graph",
}


def demo_holdings() -> list[HoldingRecord]:
    return [
        HoldingRecord(
            ticker=str(h["ticker"]),
            company=str(h["company"]),
            weight=float(h["weight"]),
            market_value=float(h["market_value"]),
            quantity=float(h["quantity"]),
            sector=str(h["sector"]),
            industry=str(h["industry"]),
            country=str(h["country"]),
        )
        for h in DEMO_HOLDINGS_RAW
    ]


def demo_portfolio_spec() -> dict[str, Any]:
    return dict(DEMO_PORTFOLIO)
