"""Institutional portfolio book — seed holdings for policy/exposure/risk.

Not live brokerage sync. Soft institutional memory of a model book.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from institutional_reasoning.ipi.schema import PortfolioHolding, PortfolioPolicy

_BOOK: dict[str, Any] = {
    "portfolio_id": "agib_core_india",
    "name": "AGIB Core India Equity",
    "base_currency": "INR",
    "cash_weight": 0.12,
    "policy": PortfolioPolicy().to_dict(),
    "holdings": [
        PortfolioHolding(
            "HDFCBANK", 0.11, "banks", "private_bank", factors={"quality": 0.8, "value": 0.4, "growth": 0.5, "momentum": 0.3}
        ).to_dict(),
        PortfolioHolding(
            "ICICIBANK", 0.09, "banks", "private_bank", factors={"quality": 0.75, "value": 0.45, "growth": 0.55, "momentum": 0.4}
        ).to_dict(),
        PortfolioHolding(
            "TCS", 0.10, "it_services", "it_services", theme="ai_services",
            factors={"quality": 0.9, "value": 0.35, "growth": 0.45, "momentum": 0.35},
        ).to_dict(),
        PortfolioHolding(
            "INFY", 0.08, "it_services", "it_services", theme="ai_services",
            beta=0.95, volatility=0.24,
            factors={"quality": 0.85, "value": 0.4, "growth": 0.5, "momentum": 0.4},
        ).to_dict(),
        PortfolioHolding(
            "NESTLEIND", 0.07, "fmcg", "staples", volatility=0.16, beta=0.55,
            factors={"quality": 0.88, "value": 0.2, "growth": 0.55, "momentum": 0.35},
        ).to_dict(),
        PortfolioHolding(
            "RELIANCE", 0.08, "energy_conglomerate", "conglomerate", volatility=0.26, beta=1.1,
            factors={"quality": 0.65, "value": 0.5, "growth": 0.6, "momentum": 0.45},
        ).to_dict(),
        PortfolioHolding(
            "BHARTIARTL", 0.06, "telecom", "telecom", volatility=0.28, beta=1.05,
            factors={"quality": 0.6, "value": 0.4, "growth": 0.7, "momentum": 0.55},
        ).to_dict(),
        PortfolioHolding(
            "ASIANPAINT", 0.05, "fmcg", "paints", volatility=0.20, beta=0.7,
            factors={"quality": 0.8, "value": 0.3, "growth": 0.5, "momentum": 0.35},
        ).to_dict(),
        PortfolioHolding(
            "SBIN", 0.04, "banks", "psu_bank", liquidity_score=0.9, volatility=0.30, beta=1.2,
            factors={"quality": 0.55, "value": 0.65, "growth": 0.45, "momentum": 0.5},
        ).to_dict(),
        PortfolioHolding(
            "HCLTECH", 0.04, "it_services", "it_services", theme="ai_services",
            factors={"quality": 0.75, "value": 0.45, "growth": 0.5, "momentum": 0.4},
        ).to_dict(),
        # Illiquid mid-cap seed for liquidity-cap tests (tiny weight).
        PortfolioHolding(
            "PERSISTENT", 0.01, "it_services", "it_services", market_cap="mid",
            liquidity_score=0.35, volatility=0.38, beta=1.25, theme="ai_services",
            factors={"quality": 0.7, "value": 0.3, "growth": 0.75, "momentum": 0.6},
        ).to_dict(),
    ],
}

# High-IT overlay used by suite cases (32% IT).
_HIGH_IT_BOOK: dict[str, Any] = {
    "portfolio_id": "agib_high_it",
    "name": "AGIB High IT Concentration",
    "base_currency": "INR",
    "cash_weight": 0.08,
    "policy": PortfolioPolicy(max_sector_weight=0.25).to_dict(),
    "holdings": [
        PortfolioHolding("TCS", 0.12, "it_services", "it_services", theme="ai_services").to_dict(),
        PortfolioHolding("INFY", 0.10, "it_services", "it_services", theme="ai_services").to_dict(),
        PortfolioHolding("HCLTECH", 0.06, "it_services", "it_services", theme="ai_services").to_dict(),
        PortfolioHolding("WIPRO", 0.04, "it_services", "it_services", theme="ai_services").to_dict(),
        PortfolioHolding("HDFCBANK", 0.10, "banks", "private_bank").to_dict(),
        PortfolioHolding("ICICIBANK", 0.08, "banks", "private_bank").to_dict(),
        PortfolioHolding("RELIANCE", 0.08, "energy_conglomerate", "conglomerate").to_dict(),
        PortfolioHolding("NESTLEIND", 0.07, "fmcg", "staples").to_dict(),
        PortfolioHolding("BHARTIARTL", 0.05, "telecom", "telecom").to_dict(),
        PortfolioHolding("ASIANPAINT", 0.04, "fmcg", "paints").to_dict(),
    ],
}

_ACTIVE_OVERRIDE: dict[str, Any] | None = None


def default_book() -> dict[str, Any]:
    return deepcopy(_ACTIVE_OVERRIDE or _BOOK)


def high_it_book() -> dict[str, Any]:
    return deepcopy(_HIGH_IT_BOOK)


def set_active_book(book: dict[str, Any] | None) -> None:
    """Test/suite helper — swap the active institutional book."""
    global _ACTIVE_OVERRIDE
    _ACTIVE_OVERRIDE = deepcopy(book) if book else None


def reset_book() -> None:
    set_active_book(None)


def holding_for(symbol: str, book: dict[str, Any] | None = None) -> dict[str, Any] | None:
    bid = str(symbol or "").upper()
    for h in (book or default_book()).get("holdings") or []:
        if str(h.get("symbol") or "").upper() == bid:
            return h
    return None


def sector_weight(sector: str, book: dict[str, Any] | None = None) -> float:
    s = str(sector or "").lower()
    return round(sum(float(h.get("weight") or 0) for h in (book or default_book()).get("holdings") or [] if str(h.get("sector") or "").lower() == s), 6)


def total_invested(book: dict[str, Any] | None = None) -> float:
    return round(sum(float(h.get("weight") or 0) for h in (book or default_book()).get("holdings") or []), 6)
