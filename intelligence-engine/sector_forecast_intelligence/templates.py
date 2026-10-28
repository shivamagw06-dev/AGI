"""Deterministic Bull / Base / Bear sector scenario templates."""

from __future__ import annotations

from typing import Any

from sector_forecast_intelligence.schema import ScenarioType

# Per-sector narrative overlays keyed by scenario
SECTOR_NARRATIVES: dict[str, dict[str, list[str]]] = {
    "Banking": {
        "Bull": [
            "RBI delivers measured easing; credit growth re-accelerates.",
            "NIMs normalise orderly while volumes expand.",
            "Asset quality remains benign; ROE sustains mid-teens.",
            "Private banks lead market leadership and relative performance.",
        ],
        "Base": [
            "Credit growth stays in the low-teens with deposit competition.",
            "NIMs ease modestly from cycle peaks; ROE remains resilient.",
            "Sector performs broadly in line with the market.",
            "Policy remains data-dependent without a hard landing.",
        ],
        "Bear": [
            "Rate cuts delayed; deposit costs stay elevated.",
            "Credit growth slows; unsecured stress rises at the margin.",
            "ROE compresses; valuation multiples de-rate.",
            "Relative underperformance versus defensives.",
        ],
    },
    "IT Services": {
        "Bull": [
            "GenAI deal conversion accelerates; discretionary spend recovers.",
            "USD/INR softens, supporting reported growth.",
            "Margins stabilise as wage pressure eases.",
            "Tier-1 franchises re-rate on pipeline visibility.",
        ],
        "Base": [
            "High-single-digit growth with selective AI contribution.",
            "Currency broadly stable; margins range-bound.",
            "Sector tracks market with modest relative swings.",
        ],
        "Bear": [
            "Global discretionary IT budgets freeze again.",
            "Deal TCV softens; attrition cost lag pressures margins.",
            "Valuation multiples compress versus domestic cyclicals.",
        ],
    },
    "FMCG": {
        "Bull": [
            "Rural volume recovery broadens; pricing power holds.",
            "Gross margins repair as input costs cool.",
            "Premium mix improves; leaders re-rate.",
        ],
        "Base": [
            "Volume-led mid/high-single-digit growth.",
            "Margins repair gradually; valuations stay elevated.",
            "Sector tracks market with defensive bias.",
        ],
        "Bear": [
            "Food/fuel inflation returns; rural demand softens.",
            "Aggressive pricing hits volumes; margins compress.",
            "Premium valuations de-rate.",
        ],
    },
    "Auto": {
        "Bull": [
            "Financing availability improves with easing; PV demand firms.",
            "Commodity costs ease; operating leverage expands margins.",
            "EV transition adds narrative premium for leaders.",
        ],
        "Base": [
            "Steady PV demand; financing supportive but not exuberant.",
            "Margins stable; sector performs near market.",
        ],
        "Bear": [
            "Higher-for-longer rates cool vehicle financing.",
            "Commodity spike and demand soft-patch compress margins.",
            "Relative underperformance versus defensives.",
        ],
    },
    "Capital Goods": {
        "Bull": [
            "Government infrastructure spending accelerates.",
            "Order books expand; capacity utilisation improves.",
            "Margins widen; valuations rerate.",
        ],
        "Base": [
            "Infrastructure spending remains steady.",
            "Order inflows continue; margins remain stable.",
            "Sector performs broadly in line with the market.",
        ],
        "Bear": [
            "Government capex slows; commodity costs rise.",
            "Project execution weakens; margins contract.",
            "Valuation multiples compress.",
        ],
    },
    "Pharma": {
        "Bull": [
            "US price erosion eases; complex generics ramps succeed.",
            "India chronic therapies grow steadily; INR softens helpfully.",
            "Quality franchises re-rate.",
        ],
        "Base": [
            "High-single / low-double digit growth.",
            "Margins stable; selective US recovery.",
            "Sector tracks market with stock-specific divergence.",
        ],
        "Bear": [
            "USFDA / pricing shocks return for select names.",
            "Currency or API cost pressure compresses margins.",
            "Valuation premium compresses.",
        ],
    },
}

SECTOR_DRIVERS: dict[str, dict[str, list[str]]] = {
    "Banking": {
        "Bull": ["Policy easing", "Credit acceleration", "Stable asset quality"],
        "Base": ["Steady credit", "NIM normalisation", "Deposit competition"],
        "Bear": ["Delayed cuts", "Credit slowdown", "Unsecured stress"],
    },
    "IT Services": {
        "Bull": ["AI deal conversion", "INR softness", "Discretionary recovery"],
        "Base": ["Selective AI", "Stable FX", "Wage normalisation"],
        "Bear": ["Budget freezes", "Deal delays", "Margin lag"],
    },
    "FMCG": {
        "Bull": ["Rural recovery", "Input cost cool-down", "Premium mix"],
        "Base": ["Volume normalisation", "Gradual margin repair"],
        "Bear": ["CPI spike", "Volume pressure", "Input costs"],
    },
    "Auto": {
        "Bull": ["Financing impulse", "Commodity cool-down", "EV narrative"],
        "Base": ["Steady PV", "Supportive financing"],
        "Bear": ["Rate sensitivity", "Commodity shock", "Demand soft-patch"],
    },
    "Capital Goods": {
        "Bull": ["Capex acceleration", "Order book expansion", "Utilisation lift"],
        "Base": ["Steady infra", "Stable execution"],
        "Bear": ["Capex slowdown", "Commodity costs", "Execution slippage"],
    },
    "Pharma": {
        "Bull": ["US recovery", "India chronic growth", "FX tailwind"],
        "Base": ["Selective US", "Steady India"],
        "Bear": ["USFDA / pricing", "Cost pressure"],
    },
}

# Metric deltas vs current tip (absolute levels computed in engine)
METRIC_PATHS: dict[str, dict[str, float]] = {
    "Bull": {
        "Revenue Growth": 3.0,
        "Earnings Growth": 5.0,
        "EBITDA Margin": 1.0,
        "ROE": 1.5,
        "PE": 2.5,
        "Relative Performance": 8.0,
    },
    "Base": {
        "Revenue Growth": 0.0,
        "Earnings Growth": 0.0,
        "EBITDA Margin": 0.0,
        "ROE": 0.0,
        "PE": 0.0,
        "Relative Performance": 0.0,
    },
    "Bear": {
        "Revenue Growth": -4.0,
        "Earnings Growth": -7.0,
        "EBITDA Margin": -1.5,
        "ROE": -2.5,
        "PE": -4.0,
        "Relative Performance": -10.0,
    },
}

# Sector-specific base tip levels (catalog fill when CSKP empty)
BASE_LEVELS: dict[str, dict[str, float]] = {
    "Banking": {
        "Revenue Growth": 12.5,
        "Earnings Growth": 13.0,
        "EBITDA Margin": 3.55,
        "ROE": 15.2,
        "PE": 17.0,
        "Relative Performance": 3.0,
    },
    "IT Services": {
        "Revenue Growth": 6.5,
        "Earnings Growth": 7.5,
        "EBITDA Margin": 23.8,
        "ROE": 24.5,
        "PE": 25.0,
        "Relative Performance": 2.0,
    },
    "FMCG": {
        "Revenue Growth": 7.5,
        "Earnings Growth": 10.5,
        "EBITDA Margin": 19.2,
        "ROE": 25.5,
        "PE": 49.0,
        "Relative Performance": 1.5,
    },
    "Auto": {
        "Revenue Growth": 9.5,
        "Earnings Growth": 11.0,
        "EBITDA Margin": 13.2,
        "ROE": 16.5,
        "PE": 27.0,
        "Relative Performance": 2.5,
    },
    "Capital Goods": {
        "Revenue Growth": 13.5,
        "Earnings Growth": 15.0,
        "EBITDA Margin": 13.2,
        "ROE": 16.5,
        "PE": 35.0,
        "Relative Performance": 7.0,
    },
    "Pharma": {
        "Revenue Growth": 9.5,
        "Earnings Growth": 11.5,
        "EBITDA Margin": 20.0,
        "ROE": 14.5,
        "PE": 29.0,
        "Relative Performance": 3.5,
    },
}

UNITS: dict[str, str] = {
    "Revenue Growth": "% yoy",
    "Earnings Growth": "% yoy",
    "EBITDA Margin": "%",
    "ROE": "%",
    "PE": "x",
    "Relative Performance": "pp vs NIFTY",
}

RISKS: dict[str, list[dict[str, Any]]] = {
    "Bull": [
        {"risk": "Optimism overshoots execution", "severity": "Medium"},
        {"risk": "Macro inheritance turns less supportive", "severity": "Medium"},
    ],
    "Base": [
        {"risk": "Idiosyncratic sector shock", "severity": "Medium"},
        {"risk": "Valuation digest without growth surprise", "severity": "Low"},
    ],
    "Bear": [
        {"risk": "Macro stress amplifies sector cyclicality", "severity": "High"},
        {"risk": "Margin and multiple compression coincide", "severity": "High"},
    ],
}

ASSUMPTIONS: dict[str, list[str]] = {
    "Bull": [
        "Macro Forecast Bull/Base bias inherited — no independent macro view",
        "Historical analogues with constructive outcomes remain relevant",
        "Validated sector relationships continue to transmit",
    ],
    "Base": [
        "Macro Forecast Base path inherited",
        "Current sector tip remains the central tendency",
        "No structural break in industry structure",
    ],
    "Bear": [
        "Macro Forecast Bear risks inherited",
        "Historical stress analogues inform downside paths",
        "Relationship transmission can amplify shocks",
    ],
}


def narratives_for(sector: str, scenario: ScenarioType) -> list[str]:
    return list((SECTOR_NARRATIVES.get(sector) or SECTOR_NARRATIVES["Banking"])[scenario])


def drivers_for(sector: str, scenario: ScenarioType) -> list[str]:
    return list((SECTOR_DRIVERS.get(sector) or SECTOR_DRIVERS["Banking"])[scenario])


def risks_for(scenario: ScenarioType) -> list[dict[str, Any]]:
    return list(RISKS[scenario])


def assumptions_for(scenario: ScenarioType) -> list[str]:
    return list(ASSUMPTIONS[scenario])


def path_deltas(scenario: ScenarioType) -> dict[str, float]:
    return dict(METRIC_PATHS[scenario])


def base_levels_for(sector: str) -> dict[str, float]:
    return dict(BASE_LEVELS.get(sector) or BASE_LEVELS["Banking"])
