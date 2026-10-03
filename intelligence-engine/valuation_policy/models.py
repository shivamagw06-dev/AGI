"""Canonical VPAE model identifiers and status vocabulary."""

from __future__ import annotations

# Internal metric keys (warehouse / UVE) ↔ institutional model codes.
METRIC_TO_MODEL: dict[str, str] = {
    "pe": "PE",
    "forward_pe": "FORWARD_PE",
    "pb": "PRICE_TO_BOOK",
    "ev_ebitda": "EV_EBITDA",
    "ev_sales": "EV_SALES",
    "ps": "PRICE_TO_SALES",
    "roe": "ROE",
    "roa": "ROA",
    "roce": "ROCE",
    "eps": "EPS",
    "book_value": "BOOK_VALUE",
    "dividend_yield": "DIVIDEND_YIELD",
    "profit_margin": "MARGIN",
    "debt_to_equity": "DEBT_TO_EQUITY",
    "market_cap": "MARKET_CAP",
    "price": "NAV",  # ETF / fund NAV proxy until dedicated NAV feed lands
    "nav": "NAV",
    "price_nav": "PRICE_TO_NAV",
    "embedded_value": "PRICE_TO_EMBEDDED_VALUE",
    "aum_growth": "AUM_GROWTH",
    "revenue_growth": "REVENUE_GROWTH",
    "gross_margin": "GROSS_MARGIN",
    "cash_burn": "CASH_BURN",
    "ffo": "FFO",
    "affo": "AFFO",
    "distribution_yield": "DISTRIBUTION_YIELD",
    "tracking_error": "TRACKING_ERROR",
    "expense_ratio": "EXPENSE_RATIO",
    "order_book": "ORDER_BOOK",
    "nim": "NIM",
    "credit_cost": "CREDIT_COST",
    "roev": "ROEV",
    "vnb": "VNB",
}

MODEL_TO_METRIC: dict[str, str] = {v: k for k, v in METRIC_TO_MODEL.items()}
# Prefer PRICE_TO_BOOK over any reverse collision from aliases.
MODEL_TO_METRIC["PRICE_TO_BOOK"] = "pb"
MODEL_TO_METRIC["PRICE_TO_NAV"] = "pb"
MODEL_TO_METRIC["NAV"] = "price"
MODEL_TO_METRIC["PRICE_TO_EMBEDDED_VALUE"] = "pb"

STATUSES = (
    "VALID",
    "LOSS_MAKING",
    "EXTREME_VALUATION",
    "INSUFFICIENT_DATA",
    "UNDER_REVIEW",
    "NOT_APPLICABLE",
    "ETF",
    "REIT",
    "INVIT",
    "BANKING_MODEL",
    "INSURANCE_MODEL",
    "NBFC_MODEL",
)

CONFIDENCE_LEVELS = ("HIGH", "MEDIUM", "LOW")

COVERAGE_LEVELS = ("FULL", "PARTIAL", "THIN", "NONE")

METRIC_STATES = ("Applicable", "Hidden", "Unavailable", "Suppressed")

EXTREME_PE = 250.0
EXTREME_EV_EBITDA = 80.0
EXTREME_PB = 20.0

ENGINE_CODE = "valuation_policy_applicability_engine"
VERSION = "8.2A"
