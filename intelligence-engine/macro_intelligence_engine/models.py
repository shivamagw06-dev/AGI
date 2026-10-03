"""Macro Intelligence Engine — constants (Phase 9.0)."""

from __future__ import annotations

ENGINE_CODE = "macro_intelligence_engine"
VERSION = "9.0"
ENGINE_LABEL = "Macro Intelligence Engine"

DEFAULT_COUNTRY = "India"

MODULES = (
    "executive",
    "dashboard",
    "regime",
    "cycle",
    "economy",
    "inflation",
    "rates",
    "liquidity",
    "currency",
    "commodities",
    "bonds",
    "fiscal",
    "external",
    "sector_impact",
    "industry_impact",
    "company_exposure",
    "attribution",
    "forecast",
    "scenarios",
    "risks",
    "relationships",
    "confidence",
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

SECTORS = (
    "IT",
    "Banks",
    "Real Estate",
    "Auto",
    "Consumer",
    "Energy",
    "Materials",
    "Healthcare",
    "Industrials",
    "Utilities",
    "Telecom",
)

REGIMES = (
    "Expansion",
    "Slowdown",
    "Recovery",
    "Recession",
    "Disinflation",
    "Inflation",
    "Stagflation",
)

CYCLES = (
    "Early Cycle",
    "Mid Cycle",
    "Late Cycle",
    "Contraction",
    "Recovery",
)

DOMAINS = (
    "growth",
    "inflation",
    "rates",
    "liquidity",
    "employment",
    "currency",
    "commodities",
    "bonds",
    "fiscal",
    "external",
    "credit",
)
