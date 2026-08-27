"""PRE-01 factor engine — style / sector / macro sensitivity proxies."""

from __future__ import annotations

from typing import Sequence

from institutional_portfolio.portfolio_entities import HoldingRecord
from institutional_portfolio_risk.models import FactorExposure

# Sector → primary factor mapping (deterministic institutional taxonomy)
_SECTOR_FACTOR: dict[str, str] = {
    "banking": "Financials",
    "banks": "Financials",
    "financials": "Financials",
    "finance": "Financials",
    "information technology": "Technology",
    "it": "Technology",
    "technology": "Technology",
    "energy": "Energy",
    "oil & gas": "Energy",
    "oil and gas": "Energy",
    "consumer": "Quality",
    "fmcg": "Quality",
    "pharma": "Quality",
    "healthcare": "Quality",
    "industrials": "Momentum",
    "auto": "Momentum",
    "metals": "Value",
    "materials": "Value",
}

_STYLE_BY_TICKER: dict[str, tuple[str, ...]] = {
    "HDFCBANK": ("Quality", "Financials", "Size"),
    "ICICIBANK": ("Growth", "Financials", "Momentum"),
    "AXISBANK": ("Value", "Financials"),
    "KOTAKBANK": ("Quality", "Financials", "Growth"),
    "TCS": ("Quality", "Technology", "Growth"),
    "INFY": ("Quality", "Technology"),
    "RELIANCE": ("Energy", "Size", "Momentum"),
}


def evaluate_factors(holdings: Sequence[HoldingRecord]) -> FactorExposure:
    buckets: dict[str, float] = {}
    for h in holdings:
        w = float(h.weight or 0.0)
        styles = list(_STYLE_BY_TICKER.get(h.ticker.upper(), ()))
        if not styles:
            sector_key = (h.sector or "").strip().lower()
            primary = _SECTOR_FACTOR.get(sector_key, "Size")
            styles = [primary]
        # Equal split across tagged factors for the holding weight
        share = w / len(styles)
        for s in styles:
            buckets[s] = buckets.get(s, 0.0) + share
        # Macro sensitivity: India financials/energy get Rate / Oil tags
        if (h.sector or "").lower() in {"banking", "banks", "financials", "finance"}:
            buckets["MacroRates"] = buckets.get("MacroRates", 0.0) + w * 0.35
        if (h.sector or "").lower() in {"energy", "oil & gas", "oil and gas"}:
            buckets["MacroOil"] = buckets.get("MacroOil", 0.0) + w * 0.40

    ordered = sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)
    factors = tuple({"factor": name, "weight": round(weight, 6)} for name, weight in ordered)
    dominant = ordered[0][0] if ordered else ""
    dominant_w = float(ordered[0][1]) if ordered else 0.0
    return FactorExposure(
        factors=factors,
        dominant_factor=dominant,
        dominant_weight=round(dominant_w, 6),
    )


def market_beta_estimate(holdings: Sequence[HoldingRecord]) -> float:
    """Crude portfolio beta — financials ~1.1, tech ~0.9, energy ~1.2, default 1.0."""
    beta_map = {
        "banking": 1.15,
        "banks": 1.15,
        "financials": 1.10,
        "technology": 0.90,
        "information technology": 0.90,
        "it": 0.90,
        "energy": 1.20,
    }
    total_w = 0.0
    weighted = 0.0
    for h in holdings:
        w = float(h.weight or 0.0)
        b = beta_map.get((h.sector or "").strip().lower(), 1.0)
        weighted += w * b
        total_w += w
    if total_w <= 0:
        return 1.0
    return round(weighted / total_w, 4)
