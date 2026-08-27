"""Deterministic Bull / Base / Bear market scenario templates."""

from __future__ import annotations

from typing import Any

from market_forecast_intelligence.schema import ScenarioType

MARKET_NARRATIVES: dict[str, dict[str, list[str]]] = {
    "India": {
        "Bull": [
            "Inflation moderates toward target; RBI begins a measured easing cycle.",
            "Liquidity expands; FII inflows strengthen alongside resilient DII bid.",
            "Market breadth improves; midcaps participate with large-cap leadership.",
            "Banking, Capital Goods and Defence lead; market rerates on earnings visibility.",
        ],
        "Base": [
            "Growth remains stable; inflation stays near target.",
            "Liquidity stays balanced; corporate earnings broadly meet expectations.",
            "Breadth is mixed-to-stable; leadership remains quality-biased.",
            "Markets deliver moderate returns without a decisive regime break.",
        ],
        "Bear": [
            "Inflation re-accelerates; global bond yields rise and USD strengthens.",
            "FII selling intensifies; liquidity weakens and breadth deteriorates.",
            "Volatility rises; mid/small underperform as risk appetite compresses.",
            "A corrective phase follows with defensive sector leadership.",
        ],
    },
    "Global": {
        "Bull": [
            "Disinflation continues; major central banks ease gradually.",
            "Global liquidity expands; risk appetite returns to EM and DM equities.",
            "Volatility compresses; growth and cyclicals lead.",
        ],
        "Base": [
            "Soft-landing path holds; policy stays data-dependent.",
            "Liquidity adequate; equity returns moderate with style rotation.",
        ],
        "Bear": [
            "Sticky inflation or growth shock tightens financial conditions.",
            "USD strengthens; EM equities and risk assets de-rate.",
            "Volatility spikes; defensive leadership returns.",
        ],
    },
}

MARKET_DRIVERS: dict[str, dict[str, list[str]]] = {
    "India": {
        "Bull": ["RBI easing", "Falling inflation", "FII inflows", "Earnings delivery"],
        "Base": ["Stable growth", "Balanced liquidity", "Earnings in-line", "DII cushion"],
        "Bear": ["Sticky inflation", "Rising global yields", "FII outflows", "Breadth collapse"],
    },
    "Global": {
        "Bull": ["Policy easing", "Disinflation", "Risk-on liquidity"],
        "Base": ["Soft landing", "Stable USD", "Moderate growth"],
        "Bear": ["Re-acceleration of inflation", "USD spike", "Geopolitical shock"],
    },
}

SCENARIO_DIMENSIONS: dict[ScenarioType, dict[str, str]] = {
    "Bull": {
        "market_direction": "Bullish",
        "market_regime": "Bull",
        "breadth": "Improving",
        "liquidity": "Expanding",
        "volatility": "Falling",
        "institutional_flows": "Positive",
    },
    "Base": {
        "market_direction": "Neutral",
        "market_regime": "Sideways",
        "breadth": "Stable",
        "liquidity": "Stable",
        "volatility": "Moderate",
        "institutional_flows": "Balanced",
    },
    "Bear": {
        "market_direction": "Bearish",
        "market_regime": "Correction",
        "breadth": "Weakening",
        "liquidity": "Contracting",
        "volatility": "Rising",
        "institutional_flows": "Negative",
    },
}

LEADERSHIP: dict[str, dict[str, dict[str, list[str]]]] = {
    "India": {
        "Bull": {
            "leaders": ["Banking", "Capital Goods", "Defence", "Auto"],
            "weak": ["Defensives", "High-duration growth"],
        },
        "Base": {
            "leaders": ["Banking", "IT Services", "FMCG"],
            "weak": ["High-beta midcaps"],
        },
        "Bear": {
            "leaders": ["FMCG", "Pharma", "Defensives"],
            "weak": ["Midcaps", "Small Caps", "High-beta cyclicals"],
        },
    },
    "Global": {
        "Bull": {"leaders": ["Technology", "Cyclicals"], "weak": ["Defensives"]},
        "Base": {"leaders": ["Quality large-caps"], "weak": ["Speculative growth"]},
        "Bear": {"leaders": ["Defensives", "Gold proxies"], "weak": ["EM equities", "High-beta"]},
    },
}

CROSS_ASSET: dict[ScenarioType, dict[str, str]] = {
    "Bull": {
        "bonds": "Supportive / yields easing",
        "gold": "Mixed / less urgent bid",
        "oil": "Stable to soft",
        "usd": "Stable to softer",
        "emerging_markets": "Risk-on",
        "developed_markets": "Risk-on",
    },
    "Base": {
        "bonds": "Range-bound",
        "gold": "Mixed",
        "oil": "Mixed",
        "usd": "Stable",
        "emerging_markets": "Selective",
        "developed_markets": "Moderate",
    },
    "Bear": {
        "bonds": "Yields rising / pressure",
        "gold": "Bid",
        "oil": "Spike risk",
        "usd": "Strong",
        "emerging_markets": "Risk-off",
        "developed_markets": "Defensive",
    },
}

ASSUMPTIONS: dict[ScenarioType, list[str]] = {
    "Bull": [
        "Inflation continues to moderate without a growth collapse",
        "Policy response remains supportive of liquidity",
        "Corporate earnings broadly deliver",
    ],
    "Base": [
        "No major policy shock",
        "Earnings remain near consensus",
        "Domestic flows continue to cushion volatility",
    ],
    "Bear": [
        "External financial conditions tighten materially",
        "Inflation or geopolitics re-price risk premia",
        "Breadth deterioration confirms distribution",
    ],
}

RISKS: dict[ScenarioType, list[dict[str, Any]]] = {
    "Bull": [
        {"risk": "Sticky inflation delays easing", "severity": "High"},
        {"risk": "Earnings miss at the index level", "severity": "Medium"},
        {"risk": "Geopolitical oil spike", "severity": "High"},
    ],
    "Base": [
        {"risk": "Valuation compression on higher real yields", "severity": "Medium"},
        {"risk": "FII flow volatility", "severity": "Medium"},
        {"risk": "Currency depreciation episode", "severity": "Medium"},
    ],
    "Bear": [
        {"risk": "Liquidity tightening / funding stress", "severity": "High"},
        {"risk": "Sharp breadth collapse", "severity": "High"},
        {"risk": "Policy mistake / unexpected tightening", "severity": "Critical"},
    ],
}

INVALIDATORS: dict[ScenarioType, list[str]] = {
    "Bull": [
        "Inflation exceeds forecast range for two consecutive prints",
        "Unexpected policy tightening",
        "Material earnings deterioration across index heavyweights",
    ],
    "Base": [
        "Sharp deterioration in market breadth",
        "Sustained FII selling with DII exhaustion",
        "Global yield shock transmits to India equities",
    ],
    "Bear": [
        "Decisive policy easing with breadth repair",
        "FII inflow surge with liquidity expansion",
        "Inflation and yields fall faster than assumed",
    ],
}

CATALYSTS: dict[ScenarioType, list[dict[str, Any]]] = {
    "Bull": [
        {"catalyst": "RBI rate cuts", "polarity": "positive"},
        {"catalyst": "Falling inflation", "polarity": "positive"},
        {"catalyst": "Strong earnings", "polarity": "positive"},
        {"catalyst": "Increased FII inflows", "polarity": "positive"},
        {"catalyst": "Government reforms / capex", "polarity": "positive"},
    ],
    "Base": [
        {"catalyst": "Stable policy path", "polarity": "mixed"},
        {"catalyst": "Earnings in-line", "polarity": "mixed"},
        {"catalyst": "DII cushion", "polarity": "positive"},
    ],
    "Bear": [
        {"catalyst": "Sticky inflation", "polarity": "negative"},
        {"catalyst": "Global bond yield spike", "polarity": "negative"},
        {"catalyst": "Oil price spike", "polarity": "negative"},
        {"catalyst": "Weak earnings", "polarity": "negative"},
        {"catalyst": "Currency depreciation", "polarity": "negative"},
    ],
}


def narratives_for(market: str, scenario: ScenarioType) -> list[str]:
    return list((MARKET_NARRATIVES.get(market) or MARKET_NARRATIVES["India"]).get(scenario) or [])


def drivers_for(market: str, scenario: ScenarioType) -> list[str]:
    return list((MARKET_DRIVERS.get(market) or MARKET_DRIVERS["India"]).get(scenario) or [])


def dimensions_for(scenario: ScenarioType) -> dict[str, str]:
    return dict(SCENARIO_DIMENSIONS[scenario])


def leadership_for(market: str, scenario: ScenarioType) -> dict[str, list[str]]:
    block = (LEADERSHIP.get(market) or LEADERSHIP["India"]).get(scenario) or {}
    return {
        "leaders": list(block.get("leaders") or []),
        "weak": list(block.get("weak") or []),
    }


def cross_asset_for(scenario: ScenarioType) -> dict[str, str]:
    return dict(CROSS_ASSET[scenario])


def assumptions_for(scenario: ScenarioType) -> list[str]:
    return list(ASSUMPTIONS[scenario])


def risks_for(scenario: ScenarioType) -> list[dict[str, Any]]:
    return [dict(r) for r in RISKS[scenario]]


def invalidators_for(scenario: ScenarioType) -> list[str]:
    return list(INVALIDATORS[scenario])


def catalysts_for(scenario: ScenarioType) -> list[dict[str, Any]]:
    return [dict(c) for c in CATALYSTS[scenario]]


def horizon_tilt(horizon: str, scenario: ScenarioType) -> float:
    """Small deterministic tilt: nearer horizons lean Base; longer allow more Bull/Bear."""
    months = {"1 Month": 1, "3 Months": 3, "6 Months": 6, "12 Months": 12}.get(horizon, 6)
    if scenario == "Base":
        return max(0.0, 4.0 - months * 0.25)
    if scenario in {"Bull", "Bear"}:
        return min(3.0, months * 0.15)
    return 0.0
