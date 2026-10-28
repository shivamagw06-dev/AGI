"""Configuration-driven FLE taxonomies — no company-specific hardcoding."""

from __future__ import annotations

FORECAST_CATEGORIES: list[str] = [
    "company",
    "sector",
    "macro",
    "market",
    "commodity",
    "currency",
    "interest_rate",
    "industry",
    "government_policy",
    "theme",
    "portfolio",
    "risk",
    "valuation",
    "earnings",
    "capital_allocation",
    "demand",
    "supply",
    "corporate_actions",
]

COMPANY_METRICS: list[str] = [
    "revenue",
    "eps",
    "ebitda",
    "pat",
    "margins",
    "roe",
    "roce",
    "debt",
    "cash_flow",
    "working_capital",
    "capex",
    "market_share",
    "order_book",
    "capacity",
    "hiring",
    "attrition",
    "guidance",
    "pricing",
    "volumes",
]

MARKET_METRICS: list[str] = [
    "nifty",
    "sensex",
    "bank_nifty",
    "volatility",
    "liquidity",
    "breadth",
    "market_sentiment",
    "sector_rotation",
    "valuation_expansion",
]

MACRO_METRICS: list[str] = [
    "gdp",
    "inflation",
    "repo_rate",
    "bond_yields",
    "oil",
    "natural_gas",
    "copper",
    "coal",
    "usd_inr",
    "eur_usd",
    "fiscal_deficit",
    "government_spending",
    "pmi",
    "industrial_production",
]

FORECAST_ORIGINS: list[str] = [
    "iie",
    "analyst_agent",
    "user_request",
    "scheduled_job",
    "portfolio_review",
    "macro_event",
    "theme_change",
    "risk_alert",
]

FORECAST_STATUSES: list[str] = [
    "pending",
    "active",
    "review_due",
    "resolved",
    "expired",
    "superseded",
]

# Metric → category hint
METRIC_CATEGORY: dict[str, str] = {
    **{m: "earnings" if m in {"revenue", "eps", "ebitda", "pat", "margins"} else "company" for m in COMPANY_METRICS},
    **{m: "market" for m in MARKET_METRICS},
    **{m: "macro" for m in MACRO_METRICS},
    "oil": "commodity",
    "natural_gas": "commodity",
    "copper": "commodity",
    "coal": "commodity",
    "usd_inr": "currency",
    "eur_usd": "currency",
    "repo_rate": "interest_rate",
    "bond_yields": "interest_rate",
}

# Calibration buckets: predicted confidence band → historical success tracking
CALIBRATION_BANDS: list[tuple[float, float, str]] = [
    (0.0, 0.5, "low"),
    (0.5, 0.7, "medium"),
    (0.7, 0.85, "high"),
    (0.85, 1.01, "very_high"),
]

DEFAULT_HORIZON_DAYS = 90
MIN_EVIDENCE_FOR_FORECAST = 1
