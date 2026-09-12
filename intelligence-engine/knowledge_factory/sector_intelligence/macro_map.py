"""Sector ↔ macro relationships — institutional priors, evidence-tagged."""

from __future__ import annotations

from typing import Any

from knowledge_factory.sector_intelligence.dna.catalog import sector_dna
from knowledge_factory.sector_intelligence.schema import SECTOR_UNIVERSE, canonicalize

# Explicit directional maps: +1 benefits, -1 hurt, 0 neutral
_MACRO: dict[str, dict[str, int]] = {
    "it_services": {
        "higher_rates": 0,
        "lower_rates": 0,
        "higher_inflation": -1,
        "lower_inflation": 1,
        "oil_up": 0,
        "oil_down": 0,
        "usd_strength": 1,  # USD revenue
        "usd_weakness": -1,
        "gdp_growth": 1,
        "credit_growth": 0,
        "liquidity_expansion": 1,
        "liquidity_contraction": -1,
    },
    "banks": {
        "higher_rates": 1,  # NIM (lagged)
        "lower_rates": -1,
        "higher_inflation": 0,
        "lower_inflation": 0,
        "oil_up": -1,
        "oil_down": 1,
        "usd_strength": 0,
        "usd_weakness": 0,
        "gdp_growth": 2,
        "credit_growth": 2,
        "liquidity_expansion": 1,
        "liquidity_contraction": -2,
    },
    "nbfc": {
        "higher_rates": -1,
        "lower_rates": 2,
        "higher_inflation": -1,
        "lower_inflation": 1,
        "oil_up": -1,
        "oil_down": 1,
        "usd_strength": 0,
        "usd_weakness": 0,
        "gdp_growth": 2,
        "credit_growth": 2,
        "liquidity_expansion": 2,
        "liquidity_contraction": -2,
    },
    "auto": {
        "higher_rates": -2,
        "lower_rates": 2,
        "higher_inflation": -1,
        "lower_inflation": 1,
        "oil_up": -1,
        "oil_down": 1,
        "usd_strength": 0,
        "usd_weakness": 1,
        "gdp_growth": 2,
        "credit_growth": 2,
        "liquidity_expansion": 1,
        "liquidity_contraction": -1,
    },
    "fmcg": {
        "higher_rates": 0,
        "lower_rates": 0,
        "higher_inflation": -1,
        "lower_inflation": 1,
        "oil_up": -1,
        "oil_down": 1,
        "usd_strength": 0,
        "usd_weakness": 0,
        "gdp_growth": 1,
        "credit_growth": 0,
        "liquidity_expansion": 0,
        "liquidity_contraction": 0,
    },
    "utilities": {
        "higher_rates": -2,
        "lower_rates": 2,
        "higher_inflation": 0,
        "lower_inflation": 0,
        "oil_up": -1,
        "oil_down": 1,
        "usd_strength": 0,
        "usd_weakness": 0,
        "gdp_growth": 0,
        "credit_growth": 0,
        "liquidity_expansion": 1,
        "liquidity_contraction": -1,
    },
    "oil_gas": {
        "higher_rates": 0,
        "lower_rates": 0,
        "higher_inflation": 1,
        "lower_inflation": -1,
        "oil_up": 2,
        "oil_down": -2,
        "usd_strength": 1,
        "usd_weakness": -1,
        "gdp_growth": 1,
        "credit_growth": 0,
        "liquidity_expansion": 0,
        "liquidity_contraction": 0,
    },
    "metals": {
        "higher_rates": -1,
        "lower_rates": 1,
        "higher_inflation": 1,
        "lower_inflation": -1,
        "oil_up": -1,
        "oil_down": 1,
        "usd_strength": -1,
        "usd_weakness": 1,
        "gdp_growth": 2,
        "credit_growth": 1,
        "liquidity_expansion": 1,
        "liquidity_contraction": -1,
    },
    "real_estate": {
        "higher_rates": -2,
        "lower_rates": 2,
        "higher_inflation": 0,
        "lower_inflation": 0,
        "oil_up": 0,
        "oil_down": 0,
        "usd_strength": 0,
        "usd_weakness": 0,
        "gdp_growth": 2,
        "credit_growth": 2,
        "liquidity_expansion": 2,
        "liquidity_contraction": -2,
    },
    "industrials": {
        "higher_rates": -1,
        "lower_rates": 1,
        "higher_inflation": -1,
        "lower_inflation": 1,
        "oil_up": -1,
        "oil_down": 1,
        "usd_strength": 0,
        "usd_weakness": 1,
        "gdp_growth": 2,
        "credit_growth": 1,
        "liquidity_expansion": 1,
        "liquidity_contraction": -1,
    },
}


def macro_relationships(sector: str) -> dict[str, Any]:
    key = canonicalize(sector) or sector
    dna = sector_dna(key)
    rel = dict(
        _MACRO.get(
            key,
            {
                "higher_rates": int(dna.get("interest_rate_sensitivity") or 0),
                "lower_rates": -int(dna.get("interest_rate_sensitivity") or 0),
                "higher_inflation": int(dna.get("inflation_sensitivity") or 0),
                "lower_inflation": -int(dna.get("inflation_sensitivity") or 0),
                "oil_up": int(dna.get("commodity_sensitivity") or 0),
                "oil_down": -int(dna.get("commodity_sensitivity") or 0),
                "usd_strength": int(dna.get("fx_sensitivity") or 0),
                "usd_weakness": -int(dna.get("fx_sensitivity") or 0),
                "gdp_growth": int(dna.get("economic_sensitivity") or 0),
                "credit_growth": max(0, int(dna.get("economic_sensitivity") or 0)),
                "liquidity_expansion": 1,
                "liquidity_contraction": -1,
            },
        )
    )
    primary = [k for k, v in rel.items() if abs(v) >= 2]
    secondary = [k for k, v in rel.items() if abs(v) == 1]
    positive = [k for k, v in rel.items() if v > 0]
    negative = [k for k, v in rel.items() if v < 0]
    return {
        "sector": key,
        "relationships": rel,
        "primary_macro_drivers": primary or secondary[:3],
        "secondary_drivers": secondary,
        "positive_drivers": positive,
        "negative_drivers": negative,
        "evidence_class": "institutional_prior",
        "fabricated": False,
    }


def sectors_benefiting_from(driver: str, *, min_score: int = 1) -> dict[str, Any]:
    """Which sectors benefit when a macro driver fires (e.g. lower_rates)."""
    key = driver.strip().lower().replace(" ", "_")
    hits = []
    for s in SECTOR_UNIVERSE:
        rel = macro_relationships(s)
        score = int((rel.get("relationships") or {}).get(key) or 0)
        if score >= min_score:
            hits.append({"sector": s, "score": score, "display_name": sector_dna(s).get("display_name")})
    hits.sort(key=lambda x: -x["score"])
    return {
        "driver": key,
        "sectors": hits,
        "n": len(hits),
        "found": len(hits) > 0,
        "evidence_class": "macro_relationship",
        "fabricated": False,
    }
