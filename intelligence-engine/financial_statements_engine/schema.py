"""FSE-01 Financial Statements Engine — contracts, versions, statuses."""

from __future__ import annotations

ENGINE_CODE = "financial_statements_engine"
ENGINE_NAME = "Financial Statements Engine"
VERSION = "fse-01-v1.0.0"
WORKSTREAM_ID = "FSE-01"
MILESTONE = "financial_warehouse_v1"
PROGRAMME = "AGIB_FINANCIAL_STATEMENTS_ENGINE"
ROLE = "canonical_financial_warehouse"

# Compatibility / migration
PREDECESSOR_ENGINE = "earnings_intelligence"
PREDECESSOR_WORKSTREAM = "P2.1"

ISSUES_RECOMMENDATIONS = False
MODIFIES_DECISION_ENGINE = False
RECOMMENDATION_POLICY = "financial_warehouse_only_no_buy_sell"

LIFECYCLE_STATES = (
    "discovered",
    "downloaded",
    "raw_verified",
    "extracted",
    "normalized",
    "validation_pending",
    "validated",
    "validation_failed",
    "versioned",
    "published",
    "withheld",
    "indexed",
)

PUBLICATION_STATUSES = ("draft", "published", "withheld", "flagged")
VALIDATION_STATUSES = ("pending", "passed", "failed", "flagged")

STATEMENT_TYPES = (
    "income_statement",
    "balance_sheet",
    "cash_flow",
    "results_pack",
)

PERIOD_TYPES = ("annual", "quarterly")

PUBLICATION_TIERS = (
    "tier_a_publish",
    "tier_b_flagged",
    "tier_c_withheld",
)

VALIDATION_CODES = (
    "STRUCT_REQUIRED_KEYS",
    "ACCT_IS_IDENTITY",
    "ACCT_BS_BALANCE",
    "ACCT_CF_BRIDGE",
    "UNIT_CURRENCY",
    "COMPLETENESS_CORE",
    "OUTLIER_YOY",
    "TRACE_EVIDENCE",
)

LAYERS = (
    "raw_evidence",
    "extraction",
    "normalization",
    "canonical",
    "validation",
    "version_control",
    "warehouse",
    "derived_metrics",
)

FRESHNESS_SLA_DAYS = {
    "annual": 120,
    "quarterly": 45,
}

QUALITY_TARGETS = {
    "annual_completeness_pct": 99.0,
    "quarterly_completeness_pct": 98.0,
    "validation_success_pct": 99.5,
    "duplicate_facts_pct_max": 0.1,
    "restatement_detection_pct": 100.0,
    "source_traceability_pct": 100.0,
    "version_preservation_pct": 100.0,
    "canonical_consistency_pct": 100.0,
}

GOLD_UNIVERSE = (
    "TCS",
    "HDFCBANK",
    "RELIANCE",
    "NTPC",
    "TATAMOTORS",
)

COVERAGE_BEFORE_DEPTH = {
    "primary_universe": "nifty500",
    "min_annual_years": 5,
    "min_quarters": 8,
}
