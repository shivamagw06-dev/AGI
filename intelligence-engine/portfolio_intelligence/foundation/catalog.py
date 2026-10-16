"""Deterministic sample portfolios for Phase 3.3 Portfolio Intelligence."""

from __future__ import annotations

from typing import Any, Optional

# Seed books — institutional demo portfolios (not live brokerage sync).
PORTFOLIOS: dict[str, dict[str, Any]] = {
    "agib_core_india": {
        "portfolio_id": "agib_core_india",
        "name": "AGIB Core India Equity",
        "objective": "Long-term compounding via high-quality India franchises",
        "benchmark": "Nifty 50 TRI",
        "base_currency": "INR",
        "risk_tolerance": "moderate",
        "constraints": {
            "single_name_limit": 0.12,
            "sector_limits": {"banks": 0.35, "it_services": 0.25, "fmcg": 0.20},
        },
        "cash_weight": 0.27,
        "holdings": [
            {"ticker": "HDFCBANK", "weight": 0.11, "sector": "banks", "industry": "banks", "country": "IN", "market_cap": "large", "style": "quality", "conviction": "high", "inv_key": "hdfc_bank"},
            {"ticker": "ICICIBANK", "weight": 0.09, "sector": "banks", "industry": "banks", "country": "IN", "market_cap": "large", "style": "quality", "conviction": "high", "inv_key": None},
            {"ticker": "TCS", "weight": 0.10, "sector": "it_services", "industry": "it_services", "country": "IN", "market_cap": "large", "style": "quality", "conviction": "high", "inv_key": "tcs"},
            {"ticker": "INFY", "weight": 0.08, "sector": "it_services", "industry": "it_services", "country": "IN", "market_cap": "large", "style": "quality", "conviction": "medium", "inv_key": "infosys"},
            {"ticker": "NESTLEIND", "weight": 0.07, "sector": "fmcg", "industry": "fmcg", "country": "IN", "market_cap": "large", "style": "quality", "conviction": "medium", "inv_key": None},
            {"ticker": "RELIANCE", "weight": 0.08, "sector": "energy", "industry": "oil_gas", "country": "IN", "market_cap": "large", "style": "blend", "conviction": "medium", "inv_key": "reliance"},
            {"ticker": "BHARTIARTL", "weight": 0.06, "sector": "telecom", "industry": "telecom", "country": "IN", "market_cap": "large", "style": "growth", "conviction": "medium", "inv_key": None},
            {"ticker": "ASIANPAINT", "weight": 0.05, "sector": "fmcg", "industry": "fmcg", "country": "IN", "market_cap": "large", "style": "quality", "conviction": "medium", "inv_key": "asian_paints"},
            {"ticker": "AXISBANK", "weight": 0.05, "sector": "banks", "industry": "banks", "country": "IN", "market_cap": "large", "style": "blend", "conviction": "low", "inv_key": None},
            {"ticker": "ETERNAL", "weight": 0.04, "sector": "consumer_internet", "industry": "internet_platforms", "country": "IN", "market_cap": "large", "style": "growth", "conviction": "low", "inv_key": None},
        ],
        "benchmark_sector_weights": {
            "banks": 0.28, "it_services": 0.14, "fmcg": 0.10, "energy": 0.10, "telecom": 0.04, "consumer_internet": 0.03,
        },
        "unknowns": ["Exact pairwise return correlations", "Live brokerage fills", "Intra-quarter drift magnitudes"],
    },
    "agib_concentrated_growth": {
        "portfolio_id": "agib_concentrated_growth",
        "name": "AGIB Concentrated Growth Book",
        "objective": "Higher conviction growth with accepted concentration risk",
        "benchmark": "Nifty 50 TRI",
        "base_currency": "INR",
        "risk_tolerance": "aggressive",
        "constraints": {"single_name_limit": 0.20, "sector_limits": {"it_services": 0.40, "consumer_internet": 0.25}},
        "cash_weight": 0.10,
        "holdings": [
            {"ticker": "TCS", "weight": 0.18, "sector": "it_services", "industry": "it_services", "country": "IN", "market_cap": "large", "style": "quality", "conviction": "high", "inv_key": "tcs"},
            {"ticker": "INFY", "weight": 0.16, "sector": "it_services", "industry": "it_services", "country": "IN", "market_cap": "large", "style": "growth", "conviction": "high", "inv_key": "infosys"},
            {"ticker": "ETERNAL", "weight": 0.14, "sector": "consumer_internet", "industry": "internet_platforms", "country": "IN", "market_cap": "large", "style": "growth", "conviction": "medium", "inv_key": None},
            {"ticker": "BHARTIARTL", "weight": 0.12, "sector": "telecom", "industry": "telecom", "country": "IN", "market_cap": "large", "style": "growth", "conviction": "medium", "inv_key": None},
            {"ticker": "RELIANCE", "weight": 0.15, "sector": "energy", "industry": "oil_gas", "country": "IN", "market_cap": "large", "style": "growth", "conviction": "medium", "inv_key": "reliance"},
            {"ticker": "ASIANPAINT", "weight": 0.15, "sector": "fmcg", "industry": "fmcg", "country": "IN", "market_cap": "large", "style": "quality", "conviction": "medium", "inv_key": "asian_paints"},
        ],
        "benchmark_sector_weights": {
            "banks": 0.28, "it_services": 0.14, "fmcg": 0.10, "energy": 0.10, "telecom": 0.04, "consumer_internet": 0.03,
        },
        "unknowns": ["Growth drawdown path", "Internet unit-economics durability"],
    },
}

_ALIASES = {
    "default": "agib_core_india",
    "core": "agib_core_india",
    "india": "agib_core_india",
    "agib core": "agib_core_india",
    "core india": "agib_core_india",
    "concentrated": "agib_concentrated_growth",
    "growth book": "agib_concentrated_growth",
    "concentrated growth": "agib_concentrated_growth",
}


def list_portfolio_ids() -> list[str]:
    return sorted(PORTFOLIOS.keys())


def get_portfolio(portfolio_id: Optional[str] = None) -> Optional[dict[str, Any]]:
    if not portfolio_id:
        return dict(PORTFOLIOS["agib_core_india"])
    pid = str(portfolio_id).strip().lower().replace(" ", "_")
    pid = _ALIASES.get(pid, _ALIASES.get(pid.replace("_", " "), pid))
    p = PORTFOLIOS.get(pid)
    return dict(p) if p else None


def resolve_portfolio(text: Optional[str]) -> Optional[str]:
    if not text:
        return "agib_core_india"
    low = " ".join(str(text).lower().split())
    for alias, pid in sorted(_ALIASES.items(), key=lambda kv: -len(kv[0])):
        if alias in low:
            return pid
    if "concentrated" in low or "growth book" in low:
        return "agib_concentrated_growth"
    if "core" in low or "portfolio" in low or "diversif" in low or "sector" in low:
        return "agib_core_india"
    for pid in PORTFOLIOS:
        if pid.replace("_", " ") in low:
            return pid
    return "agib_core_india"
