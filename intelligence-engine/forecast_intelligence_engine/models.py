"""Forecast Intelligence Engine — constants (Phase 8.5)."""

from __future__ import annotations

ENGINE_CODE = "forecast_intelligence_engine"
VERSION = "8.5"
ENGINE_LABEL = "Forecast Intelligence Engine"

WINDOWS = ("NQ", "FY+1", "FY+2", "FY+3", "FY+5")

MODULES = (
    "executive",
    "business",
    "growth",
    "profitability",
    "balance_sheet",
    "valuation",
    "scenarios",
    "sensitivity",
    "risks",
    "catalysts",
    "confidence",
    "history",
    "accuracy",
)

FORBIDDEN_TOKENS = (
    "buy",
    "sell",
    "hold",
    "overweight",
    "underweight",
    "accumulate",
    "reduce",
    "strong buy",
    "strong sell",
    "target price",
    "price target",
)

# Scenario multipliers on growth rates (deterministic, disclosed as assumptions).
SCENARIO_GROWTH_MULT = {"bull": 1.25, "base": 1.0, "bear": 0.55}
SCENARIO_MARGIN_DELTA_PP = {"bull": 1.0, "base": 0.0, "bear": -1.5}

MIN_ANNUAL_OBS = 2
