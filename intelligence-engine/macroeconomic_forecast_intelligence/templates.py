"""Deterministic Bull / Base / Bear macro scenario templates."""

from __future__ import annotations

from typing import Any

from macroeconomic_forecast_intelligence.schema import ScenarioType

NARRATIVES: dict[str, list[str]] = {
    "Bull": [
        "Inflation moderates faster toward the lower half of the tolerance band.",
        "RBI begins a measured easing cycle.",
        "Credit growth accelerates with improving banking liquidity.",
        "Private capex improves alongside strong government capex.",
        "Exports recover as global growth stabilises.",
    ],
    "Base": [
        "Inflation remains near the RBI target with occasional food/fuel noise.",
        "GDP grows steadily without a hard landing.",
        "RBI maintains a cautious, data-dependent stance.",
        "Corporate earnings remain resilient with selective margin pressure.",
        "Fiscal consolidation proceeds gradually.",
    ],
    "Bear": [
        "Oil prices rise sharply and transmit into WPI/CPI.",
        "Inflation re-accelerates above the comfort zone.",
        "Rate cuts are delayed or reversed.",
        "Corporate margins weaken on input costs and slower demand.",
        "Consumption slows; risk appetite fades.",
    ],
}

DRIVERS: dict[str, list[str]] = {
    "Bull": [
        "Faster disinflation opens policy space",
        "Liquidity surplus supports credit transmission",
        "Capex multiplier from public + private investment",
        "External demand recovery",
    ],
    "Base": [
        "Inflation near target anchors policy",
        "Domestic demand resilience",
        "Orderly fiscal path",
        "Contained global volatility",
    ],
    "Bear": [
        "Commodity / oil shock",
        "Sticky core inflation",
        "Currency depreciation pressure",
        "Global growth disappointment",
    ],
}

# Indicator deltas vs current tip (absolute levels computed in engine)
INDICATOR_PATHS: dict[str, dict[str, float]] = {
    # keys: Repo Rate, CPI, GDP, Fiscal Deficit, USDINR, Banking Liquidity, Credit Growth, WPI, G-Sec 10Y
    "Bull": {
        "Repo Rate": -0.75,
        "CPI": -0.6,
        "GDP": 0.4,
        "Fiscal Deficit": -0.3,
        "USDINR": -1.5,
        "Banking Liquidity": 0.8,
        "Credit Growth": 1.5,
        "WPI": -0.8,
        "G-Sec 10Y": -0.5,
        "Core Inflation": -0.5,
        "IIP": 0.6,
        "Forex Reserves": 25.0,
    },
    "Base": {
        "Repo Rate": -0.25,
        "CPI": 0.2,
        "GDP": -0.3,
        "Fiscal Deficit": -0.2,
        "USDINR": 1.5,
        "Banking Liquidity": 0.0,
        "Credit Growth": 0.0,
        "WPI": 0.3,
        "G-Sec 10Y": -0.1,
        "Core Inflation": 0.1,
        "IIP": -0.2,
        "Forex Reserves": 10.0,
    },
    "Bear": {
        "Repo Rate": 0.25,
        "CPI": 1.4,
        "GDP": -1.2,
        "Fiscal Deficit": 0.5,
        "USDINR": 4.0,
        "Banking Liquidity": -1.2,
        "Credit Growth": -2.5,
        "WPI": 3.5,
        "G-Sec 10Y": 0.6,
        "Core Inflation": 1.0,
        "IIP": -1.5,
        "Forex Reserves": -20.0,
    },
}

UNITS: dict[str, str] = {
    "Repo Rate": "%",
    "CPI": "% yoy",
    "Core Inflation": "% yoy",
    "WPI": "% yoy",
    "GDP": "% yoy",
    "GVA": "% yoy",
    "IIP": "% yoy",
    "Fiscal Deficit": "% of GDP",
    "USDINR": "INR per USD",
    "Banking Liquidity": "INR lakh crore surplus",
    "Credit Growth": "% yoy",
    "G-Sec 10Y": "%",
    "Forex Reserves": "USD bn",
}

RISKS: dict[str, list[dict[str, Any]]] = {
    "Bull": [
        {"risk": "Premature easing reignites inflation", "severity": "Medium"},
        {"risk": "Global growth disappoints despite domestic strength", "severity": "Medium"},
    ],
    "Base": [
        {"risk": "Food/fuel shock temporarily lifts CPI", "severity": "Medium"},
        {"risk": "Fiscal slippage delays consolidation", "severity": "Low"},
    ],
    "Bear": [
        {"risk": "Sustained oil shock and INR stress", "severity": "High"},
        {"risk": "Policy stuck higher-for-longer", "severity": "High"},
        {"risk": "Credit slowdown amplifies growth soft-patch", "severity": "High"},
    ],
}


def narratives_for(scenario: ScenarioType) -> list[str]:
    return list(NARRATIVES[scenario])


def drivers_for(scenario: ScenarioType) -> list[str]:
    return list(DRIVERS[scenario])


def risks_for(scenario: ScenarioType) -> list[dict[str, Any]]:
    return list(RISKS[scenario])


def path_deltas(scenario: ScenarioType) -> dict[str, float]:
    return dict(INDICATOR_PATHS[scenario])
