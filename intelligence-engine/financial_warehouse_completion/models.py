"""Phase 7.4F — Institutional Financial Warehouse Completion Programme (FWCP)."""

from __future__ import annotations

PROGRAMME_CODE = "financial_warehouse_completion"
PROGRAMME_VERSION = "1.0"
ENGINE_CODE = "financial_warehouse_completion"

# Coverage targets (success metrics).
TARGETS = {
    "annual_pct": 95.0,
    "quarterly_pct": 95.0,
    "share_count_pct": 99.0,
    "company_financial_pct": 95.0,
    "consensus_pct": 90.0,
    "ownership_pct": 90.0,
    "peers_pct": 80.0,
    "profile_pct": 80.0,
    "hvie_eligible_pct": 95.0,
    "hvie_complete_pct": 90.0,
    "failed_import_pct": 1.0,
}

# Minimum history for “covered”.
MIN_ANNUAL_YEARS = 3
MIN_QUARTERLY_PERIODS = 4
PREFERRED_ANNUAL_YEARS = 10
PREFERRED_QUARTERLY_PERIODS = 20

PACKS = (
    "company_master",
    "financials_annual",
    "financials_quarterly",
    "share_count_history",
    "consensus",
    "ownership",
    "peer_relationships",
    "profile_history",
)

PRIMARY_SOURCES = (
    "capital_iq",
    "upstox",
    "financial_connector",
)
SECONDARY_SOURCES = (
    "yahoo_finance_statements",
    "yahoo_finance_history",
    "warehouse_history",
)

# Never import these as vendor history — HVIE reconstructs them.
FORBIDDEN_VENDOR_MULTIPLES = ("pe", "pb", "ev_ebitda", "price_to_sales", "historical_pe")
