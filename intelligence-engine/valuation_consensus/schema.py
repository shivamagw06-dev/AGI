"""Canonical schema for valuation_consensus rows + CapIQ column mapping.

Everything from a CapIQ export is retained. Known consensus / identity fields
are promoted onto first-class keys; remaining columns land in `extras`.
"""

from __future__ import annotations

import re
from typing import Any

# First-class fields persisted on every row (ticker is PK).
CANONICAL_FIELDS: tuple[str, ...] = (
    "ticker",
    "security_name",
    "company_name",
    "exchange",
    "primary_exchange",
    "all_listings",
    "indices",
    "trading_status",
    "cmp",
    "currency",
    "sector",
    "industry",
    "industry_classification",
    "parent",
    "investors",
    "competitors",
    "subsidiaries",
    "company_type",
    "country",
    "website",
    "products",
    "description",
    "market_cap",
    "enterprise_value",
    "revenue",
    "ebitda",
    "target_price",
    "target_high",
    "target_low",
    "target_std_dev",
    "upside",
    "buy_count",
    "outperform_count",
    "hold_count",
    "sell_count",
    "no_opinion_count",
    "coverage",
    "avg_volume",
    "return_ytd",
    "return_1d",
    "return_1w",
    "return_1m",
    "return_3m",
    "return_6m",
    "return_9m",
    "return_1y",
    "return_3y",
    "return_5y",
    "updated_at",
    "source_file",
    "version_id",
)

# Normalized CapIQ header → canonical field (exact match after normalize).
COLUMN_MAP: dict[str, str] = {
    "ticker": "ticker",
    "symbol": "ticker",
    "nse symbol": "ticker",
    "security name": "security_name",
    "company name": "company_name",
    "company": "company_name",
    "name": "company_name",
    "exchange": "exchange",
    "primary exchange": "primary_exchange",
    "all listings": "all_listings",
    "trading status": "trading_status",
    "equity currency": "currency",
    "currency": "currency",
    "primary sector": "sector",
    "sector": "sector",
    "primary industry": "industry",
    "industry": "industry",
    "industry classifications": "industry_classification",
    "industry classification": "industry_classification",
    "ultimate corporate parent": "parent",
    "parent": "parent",
    "current and pending investors": "investors",
    "investors": "investors",
    "competitors": "competitors",
    "of total investments / subsidiaries": "subsidiaries",
    "subsidiaries": "subsidiaries",
    "company type": "company_type",
    "exchange country/region": "country",
    "country": "country",
    "website": "website",
    "web site": "website",
    "product name": "products",
    "products": "products",
    "long business description": "description",
    "business description": "description",
    "target price": "target_price",
    "consensus target": "target_price",
    "consensus target price": "target_price",
    "mean target price": "target_price",
    "target high": "target_high",
    "high target": "target_high",
    "target price high": "target_high",
    "target low": "target_low",
    "low target": "target_low",
    "target price low": "target_low",
    "std dev": "target_std_dev",
    "target std dev": "target_std_dev",
    "standard deviation": "target_std_dev",
    "upside": "upside",
    "upside %": "upside",
    "upside potential": "upside",
    "potential upside": "upside",
    "last price": "cmp",
    "most recent trade price": "cmp",
    "buy": "buy_count",
    "buy count": "buy_count",
    "# buy": "buy_count",
    "outperform": "outperform_count",
    "outperform count": "outperform_count",
    "hold": "hold_count",
    "hold count": "hold_count",
    "sell": "sell_count",
    "sell count": "sell_count",
    "no opinion": "no_opinion_count",
    "no opinion count": "no_opinion_count",
    "coverage": "coverage",
    "analyst coverage": "coverage",
    "research coverage": "coverage",
    "of estimates": "coverage",
}

# Prefix patterns for CapIQ headers with variable suffixes/dates.
# More-specific patterns MUST come before broader "target price" / "price" matches.
PREFIX_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Returns before generic price — CapIQ "% Price Change [...]" normalizes to "price change ..."
    (re.compile(r"^price change ytd"), "return_ytd"),
    (re.compile(r"^price change 1 day"), "return_1d"),
    (re.compile(r"^price change 1 week"), "return_1w"),
    (re.compile(r"^price change 1 month"), "return_1m"),
    (re.compile(r"^price change 3 months"), "return_3m"),
    (re.compile(r"^price change 6 months"), "return_6m"),
    (re.compile(r"^price change 9 months"), "return_9m"),
    (re.compile(r"^price change 1 year"), "return_1y"),
    (re.compile(r"^price change 3 years"), "return_3y"),
    (re.compile(r"^price change 5 years"), "return_5y"),
    (re.compile(r"^day close price"), "cmp"),
    (re.compile(r"^close price"), "cmp"),
    (re.compile(r"^most recent trade price"), "cmp"),
    (re.compile(r"^last price"), "cmp"),
    (re.compile(r"^daily volume"), "avg_volume"),
    (re.compile(r"^average volume"), "avg_volume"),
    (re.compile(r"^total enterprise value"), "enterprise_value"),
    (re.compile(r"^enterprise value"), "enterprise_value"),
    (re.compile(r"^market capitalization"), "market_cap"),
    (re.compile(r"^market cap\b"), "market_cap"),
    (re.compile(r"^total revenue"), "revenue"),
    (re.compile(r"^revenue\b"), "revenue"),
    (re.compile(r"^ebitda\b"), "ebitda"),
    (re.compile(r"^index constituents"), "indices"),
    # CapIQ broker-estimate columns (export often replaces "–" with "0")
    (re.compile(r"^target price high"), "target_high"),
    (re.compile(r"^target price low"), "target_low"),
    (re.compile(r"^target price.*std\s*dev"), "target_std_dev"),
    (re.compile(r"^target price.*of estimates"), "coverage"),
    (re.compile(r"^target price.*# of estimates"), "coverage"),
    (re.compile(r"^target price"), "target_price"),
    (re.compile(r"^consensus target"), "target_price"),
    (re.compile(r"^potential upside"), "upside"),
    (re.compile(r"analyst buy"), "buy_count"),
    (re.compile(r"analyst outperform"), "outperform_count"),
    (re.compile(r"analyst hold"), "hold_count"),
    (re.compile(r"analyst sell"), "sell_count"),
    (re.compile(r"analyst no opinion"), "no_opinion_count"),
    (re.compile(r"^of analyst buy"), "buy_count"),
    (re.compile(r"^of analyst outperform"), "outperform_count"),
    (re.compile(r"^of analyst hold"), "hold_count"),
    (re.compile(r"^of analyst sell"), "sell_count"),
    (re.compile(r"^of analyst no opinion"), "no_opinion_count"),
    (re.compile(r"^number of investment research"), "coverage"),
    (re.compile(r"^research coverage"), "coverage"),
)

# Capital IQ "Primary Sector" values are GICS sectors — these are the exact
# labels present in the export, so cards match rows one-for-one (no fuzzy
# "Consumer" bucket double-counting Discretionary + Staples).
SECTOR_CARDS: tuple[str, ...] = (
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Information Technology",
    "Materials",
    "Real Estate",
    "Utilities",
)

# Back-compat alias — older imports referenced the NSE-style card list.
NSE_SECTOR_CARDS = SECTOR_CARDS


def normalize_header(header: Any) -> str:
    h = str(header or "").strip().lower().replace("_", " ")
    h = re.sub(r"[%$#]", " ", h)
    h = re.sub(r"[^a-z0-9/ ]", " ", h)
    return re.sub(r"\s+", " ", h).strip()


def map_header(header: Any) -> str | None:
    """Return canonical field for a CapIQ header, or None if unmapped."""
    norm = normalize_header(header)
    if not norm:
        return None
    if norm in COLUMN_MAP:
        return COLUMN_MAP[norm]
    for pattern, field in PREFIX_PATTERNS:
        if pattern.search(norm):
            return field
    return None


def empty_row(ticker: str) -> dict[str, Any]:
    row = {k: None for k in CANONICAL_FIELDS}
    row["ticker"] = str(ticker or "").strip().upper()
    row["extras"] = {}
    row["returns"] = {}
    return row
