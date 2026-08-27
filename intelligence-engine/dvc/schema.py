"""DVC constants — provider priority and field taxonomy."""

from __future__ import annotations

DVC_VERSION = "dvc-v1.0.0"

# Lower number = higher institutional priority (configurable)
DEFAULT_PROVIDER_PRIORITY: dict[str, int] = {
    "official_exchange": 1,
    "indianapi": 2,
    "finnhub": 3,
    "fmp": 4,
    "yahoo": 5,
}

# Fields DVC validates across quote / fundamentals
QUOTE_FIELDS = (
    "last",
    "previous_close",
    "open",
    "high",
    "low",
    "volume",
    "change_percent",
)

FUNDAMENTAL_FIELDS = (
    "market_cap",
    "enterprise_value",
    "shares_outstanding",
    "trailing_pe",
    "forward_pe",
    "price_to_book",
    "price_to_sales",
    "ev_ebitda",
    "peg",
    "roe",
    "roa",
    "revenue",
    "revenue_growth",
    "operating_margin",
    "profit_margin",
    "dividend_yield",
    "dividend_rate",
    "beta",
    "float_shares",
    "book_value_per_share",
    "ebitda",
    "net_income",
    "fifty_two_week_high",
    "fifty_two_week_low",
    "sector",
    "industry",
    "company_name",
)

SEVERITY_ORDER = ("low", "medium", "high", "critical")

# Fields watched for multi-provider conflict reports
CONFLICT_FIELDS = (
    "last",
    "market_cap",
    "shares_outstanding",
    "trailing_pe",
    "forward_pe",
    "price_to_book",
    "roe",
    "roa",
    "revenue",
    "enterprise_value",
    "dividend_yield",
    "sector",
    "industry",
)

# Relative spread thresholds for numeric conflicts
CONFLICT_THRESHOLDS: dict[str, dict[str, float]] = {
    "last": {"medium": 0.005, "high": 0.02, "critical": 0.05},
    "market_cap": {"medium": 0.03, "high": 0.10, "critical": 0.25},
    "shares_outstanding": {"medium": 0.02, "high": 0.08, "critical": 0.20},
    "trailing_pe": {"medium": 0.05, "high": 0.15, "critical": 0.40},
    "forward_pe": {"medium": 0.05, "high": 0.15, "critical": 0.40},
    "price_to_book": {"medium": 0.05, "high": 0.15, "critical": 0.40},
    "roe": {"medium": 0.05, "high": 0.15, "critical": 0.35},
    "roa": {"medium": 0.05, "high": 0.15, "critical": 0.35},
    "revenue": {"medium": 0.05, "high": 0.15, "critical": 0.40},
    "enterprise_value": {"medium": 0.05, "high": 0.15, "critical": 0.35},
    "dividend_yield": {"medium": 0.08, "high": 0.25, "critical": 0.50},
}

# Institutional Research Grade gates
GRADE_THRESHOLDS: dict[str, float] = {
    "coverage": 0.90,
    "freshness": 0.85,
    "confidence": 0.90,
    "consistency": 0.90,
    "validation": 0.90,
}
