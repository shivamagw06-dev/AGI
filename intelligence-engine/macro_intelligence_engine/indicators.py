"""Deterministic indicator taxonomy + sector/industry impact rules for MIE."""

from __future__ import annotations

from typing import Any, Optional

from macro_intelligence_engine.models import SECTORS

# Canonical series catalogue — warehouse keys, not live vendor IDs.
SERIES_CATALOGUE: dict[str, dict[str, str]] = {
    "gdp_growth": {"domain": "growth", "label": "GDP Growth", "unit": "%"},
    "gva_growth": {"domain": "growth", "label": "GVA Growth", "unit": "%"},
    "iip": {"domain": "growth", "label": "Industrial Production", "unit": "index"},
    "pmi_manufacturing": {"domain": "growth", "label": "PMI Manufacturing", "unit": "index"},
    "pmi_services": {"domain": "growth", "label": "PMI Services", "unit": "index"},
    "capacity_utilisation": {"domain": "growth", "label": "Capacity Utilisation", "unit": "%"},
    "cpi": {"domain": "inflation", "label": "CPI", "unit": "%"},
    "core_cpi": {"domain": "inflation", "label": "Core CPI", "unit": "%"},
    "wpi": {"domain": "inflation", "label": "WPI", "unit": "%"},
    "food_inflation": {"domain": "inflation", "label": "Food Inflation", "unit": "%"},
    "fuel_inflation": {"domain": "inflation", "label": "Fuel Inflation", "unit": "%"},
    "repo_rate": {"domain": "rates", "label": "RBI Repo Rate", "unit": "%"},
    "reverse_repo": {"domain": "rates", "label": "Reverse Repo", "unit": "%"},
    "fed_funds": {"domain": "rates", "label": "US Fed Funds", "unit": "%"},
    "ecb_rate": {"domain": "rates", "label": "ECB Rate", "unit": "%"},
    "banking_liquidity": {"domain": "liquidity", "label": "Banking System Liquidity", "unit": "INR cr"},
    "money_supply": {"domain": "liquidity", "label": "Money Supply", "unit": "%"},
    "credit_growth": {"domain": "liquidity", "label": "Credit Growth", "unit": "%"},
    "deposit_growth": {"domain": "liquidity", "label": "Deposit Growth", "unit": "%"},
    "unemployment": {"domain": "employment", "label": "Unemployment", "unit": "%"},
    "usdinr": {"domain": "currency", "label": "USDINR", "unit": "INR"},
    "dxy": {"domain": "currency", "label": "DXY", "unit": "index"},
    "reer": {"domain": "currency", "label": "REER", "unit": "index"},
    "brent": {"domain": "commodities", "label": "Brent", "unit": "USD/bbl"},
    "wti": {"domain": "commodities", "label": "WTI", "unit": "USD/bbl"},
    "gold": {"domain": "commodities", "label": "Gold", "unit": "USD/oz"},
    "copper": {"domain": "commodities", "label": "Copper", "unit": "USD/t"},
    "india_10y": {"domain": "bonds", "label": "India 10Y", "unit": "%"},
    "us_10y": {"domain": "bonds", "label": "US 10Y", "unit": "%"},
    "fiscal_deficit": {"domain": "fiscal", "label": "Fiscal Deficit", "unit": "% GDP"},
    "tax_collection": {"domain": "fiscal", "label": "Tax Collection", "unit": "INR cr"},
    "trade_balance": {"domain": "external", "label": "Trade Balance", "unit": "USD bn"},
    "current_account": {"domain": "external", "label": "Current Account", "unit": "% GDP"},
    "fx_reserves": {"domain": "external", "label": "FX Reserves", "unit": "USD bn"},
    "bank_credit": {"domain": "credit", "label": "Bank Credit", "unit": "%"},
    "nbfc_credit": {"domain": "credit", "label": "NBFC Credit", "unit": "%"},
}

# Sector impact matrix: Positive / Neutral / Negative under rising rates / inflation / oil / USD.
# Keys are directional drivers used by the sector impact engine.
_SECTOR_RULES: dict[str, dict[str, str]] = {
    "IT": {"rates_up": "Neutral", "inflation_up": "Neutral", "oil_up": "Neutral", "usd_up": "Positive", "growth_up": "Positive", "liquidity_tight": "Neutral"},
    "Banks": {"rates_up": "Positive", "inflation_up": "Neutral", "oil_up": "Neutral", "usd_up": "Neutral", "growth_up": "Positive", "liquidity_tight": "Negative"},
    "Real Estate": {"rates_up": "Negative", "inflation_up": "Negative", "oil_up": "Neutral", "usd_up": "Neutral", "growth_up": "Positive", "liquidity_tight": "Negative"},
    "Auto": {"rates_up": "Negative", "inflation_up": "Negative", "oil_up": "Negative", "usd_up": "Negative", "growth_up": "Positive", "liquidity_tight": "Negative"},
    "Consumer": {"rates_up": "Negative", "inflation_up": "Negative", "oil_up": "Negative", "usd_up": "Neutral", "growth_up": "Positive", "liquidity_tight": "Negative"},
    "Energy": {"rates_up": "Neutral", "inflation_up": "Positive", "oil_up": "Positive", "usd_up": "Positive", "growth_up": "Positive", "liquidity_tight": "Neutral"},
    "Materials": {"rates_up": "Negative", "inflation_up": "Positive", "oil_up": "Negative", "usd_up": "Positive", "growth_up": "Positive", "liquidity_tight": "Negative"},
    "Healthcare": {"rates_up": "Neutral", "inflation_up": "Neutral", "oil_up": "Neutral", "usd_up": "Positive", "growth_up": "Neutral", "liquidity_tight": "Neutral"},
    "Industrials": {"rates_up": "Negative", "inflation_up": "Neutral", "oil_up": "Negative", "usd_up": "Neutral", "growth_up": "Positive", "liquidity_tight": "Negative"},
    "Utilities": {"rates_up": "Negative", "inflation_up": "Negative", "oil_up": "Negative", "usd_up": "Neutral", "growth_up": "Neutral", "liquidity_tight": "Negative"},
    "Telecom": {"rates_up": "Negative", "inflation_up": "Neutral", "oil_up": "Neutral", "usd_up": "Negative", "growth_up": "Neutral", "liquidity_tight": "Negative"},
}

_INDUSTRY_MAP: dict[str, str] = {
    "IT Services": "IT",
    "Software": "IT",
    "Private Banks": "Banks",
    "PSU Banks": "Banks",
    "NBFCs": "Banks",
    "Housing Finance": "Real Estate",
    "Realty": "Real Estate",
    "Automobiles": "Auto",
    "Auto Ancillary": "Auto",
    "FMCG": "Consumer",
    "Retail": "Consumer",
    "Oil & Gas": "Energy",
    "Refineries": "Energy",
    "Metals": "Materials",
    "Chemicals": "Materials",
    "Cement": "Materials",
    "Paints": "Materials",
    "Pharma": "Healthcare",
    "Hospitals": "Healthcare",
    "Capital Goods": "Industrials",
    "Engineering": "Industrials",
    "Power": "Utilities",
    "Telecom Services": "Telecom",
}


def _score_to_label(score: float) -> str:
    if score >= 0.5:
        return "Positive"
    if score <= -0.5:
        return "Negative"
    return "Neutral"


def active_drivers(snapshot: dict[str, Any]) -> dict[str, bool]:
    """Derive boolean macro drivers from latest snapshot values / directions."""
    def _dir(key: str) -> Optional[str]:
        row = snapshot.get(key) or {}
        return row.get("direction") or row.get("trend")

    rates_dir = _dir("repo_rate") or _dir("india_10y")
    cpi_dir = _dir("cpi")
    oil_dir = _dir("brent") or _dir("wti")
    fx_dir = _dir("usdinr") or _dir("dxy")
    growth_dir = _dir("gdp_growth") or _dir("pmi_manufacturing")
    liq_dir = _dir("banking_liquidity") or _dir("credit_growth")

    return {
        "rates_up": rates_dir == "up",
        "inflation_up": cpi_dir == "up",
        "oil_up": oil_dir == "up",
        "usd_up": fx_dir == "up",
        "growth_up": growth_dir == "up" or growth_dir is None,
        "liquidity_tight": liq_dir == "down",
    }


def sector_impacts(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    drivers = active_drivers(snapshot)
    out: list[dict[str, Any]] = []
    for sector in SECTORS:
        rules = _SECTOR_RULES.get(sector) or {}
        score = 0.0
        evidence: list[str] = []
        for driver, active in drivers.items():
            if not active:
                continue
            impact = rules.get(driver) or "Neutral"
            if impact == "Positive":
                score += 1.0
            elif impact == "Negative":
                score -= 1.0
            evidence.append(f"{driver}→{impact}")
        label = _score_to_label(score)
        out.append({
            "sector": sector,
            "impact": label,
            "score": round(score, 2),
            "evidence": evidence[:6],
        })
    return out


def industry_impacts(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    by_sector = {r["sector"]: r for r in sector_impacts(snapshot)}
    out: list[dict[str, Any]] = []
    for industry, sector in _INDUSTRY_MAP.items():
        base = by_sector.get(sector) or {"impact": "Neutral", "score": 0, "evidence": []}
        out.append({
            "industry": industry,
            "sector": sector,
            "impact": base["impact"],
            "score": base["score"],
            "evidence": list(base.get("evidence") or [])[:4],
        })
    return out


def company_sensitivity(sector: Optional[str], industry: Optional[str] = None) -> dict[str, str]:
    """Map company sector/industry to exposure sensitivities (High/Medium/Low)."""
    sec = (sector or "").strip()
    ind = (industry or "").strip()
    mapped = _INDUSTRY_MAP.get(ind) or sec
    # Normalize common warehouse sector names
    aliases = {
        "Information Technology": "IT",
        "Technology": "IT",
        "Financials": "Banks",
        "Financial Services": "Banks",
        "Banking": "Banks",
        "Consumer Discretionary": "Consumer",
        "Consumer Staples": "Consumer",
        "Oil Gas & Consumable Fuels": "Energy",
    }
    mapped = aliases.get(mapped, mapped)
    if mapped not in SECTORS:
        for s in SECTORS:
            if s.lower() in mapped.lower() or mapped.lower() in s.lower():
                mapped = s
                break
        else:
            mapped = "Industrials"

    high_rate = {"Banks", "Real Estate", "Auto", "Utilities", "Telecom"}
    high_oil = {"Energy", "Auto", "Materials", "Utilities"}
    high_fx = {"IT", "Healthcare", "Materials", "Energy"}
    high_commodity = {"Materials", "Energy"}
    high_credit = {"Banks", "Real Estate", "Auto"}
    high_demand = {"Consumer", "Auto", "Real Estate", "Industrials"}

    def _lvl(bucket: set[str]) -> str:
        return "High" if mapped in bucket else ("Medium" if mapped in {"Industrials", "Consumer", "Healthcare"} else "Low")

    return {
        "sector": mapped,
        "interest_rate_sensitivity": "High" if mapped in high_rate else "Medium",
        "oil_sensitivity": _lvl(high_oil),
        "fx_sensitivity": _lvl(high_fx),
        "commodity_sensitivity": _lvl(high_commodity),
        "credit_sensitivity": _lvl(high_credit),
        "consumer_demand_sensitivity": _lvl(high_demand),
    }


def regime_label(value: Any) -> str:
    """Normalize HMAI / rule-engine regime payloads to a short display label."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("label", "regime", "name", "regime_label", "current_regime"):
            inner = value.get(key)
            if isinstance(inner, str) and inner.strip():
                # Prefer human label; strip verbose "India 2026 current regime" → keep as-is if short
                text = inner.strip()
                if key == "label" and " current regime" in text.lower():
                    # Fall through to rule classification preference when label is generic catalog text
                    continue
                if key != "label":
                    return regime_label(inner) if isinstance(inner, dict) else text
                return text
        # Catalog rows often only have features — no named Expansion/Slowdown label
        return ""
    return str(value).strip()


def classify_regime(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Rule-based regime from growth + inflation directions."""
    drivers = active_drivers(snapshot)
    growth_up = drivers.get("growth_up")
    inflation_up = drivers.get("inflation_up")
    rates_up = drivers.get("rates_up")

    if growth_up and inflation_up and rates_up:
        regime = "Inflation"
        cycle = "Late Cycle"
    elif growth_up and not inflation_up:
        regime = "Expansion" if not rates_up else "Disinflation"
        cycle = "Mid Cycle" if not rates_up else "Early Cycle"
    elif not growth_up and inflation_up:
        regime = "Stagflation"
        cycle = "Contraction"
    elif not growth_up and not inflation_up:
        regime = "Slowdown" if rates_up else "Recovery"
        cycle = "Contraction" if rates_up else "Recovery"
    else:
        regime = "Recovery"
        cycle = "Early Cycle"

    return {
        "regime": regime,
        "cycle": cycle,
        "drivers": drivers,
        "basis": "growth_inflation_rates_directional_rules",
    }


def scenario_probabilities(regime: str, confidence_score: float) -> dict[str, float]:
    """Bull/Base/Bear for economy — always totals 100."""
    base = 55.0
    if regime in {"Expansion", "Recovery", "Disinflation"}:
        bull, bear = 28.0, 17.0
    elif regime in {"Slowdown", "Inflation"}:
        bull, bear = 18.0, 27.0
    elif regime in {"Recession", "Stagflation"}:
        bull, bear = 12.0, 33.0
    else:
        bull, bear = 22.0, 23.0
    # Shrink tails when confidence is low
    if confidence_score < 0.5:
        bull *= 0.85
        bear *= 0.85
    base = 100.0 - bull - bear
    # Round to 1dp and fix remainder on base
    b = round(bull, 1)
    e = round(bear, 1)
    a = round(100.0 - b - e, 1)
    return {"bull": b, "base": a, "bear": e}
