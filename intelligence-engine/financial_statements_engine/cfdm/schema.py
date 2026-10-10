"""FSE-03 Canonical Financial Data Model — enums & contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FSE-03"
SUBSYSTEM = "cfdm"
VERSION = "fse-03-cfdm-v1.0.0"
PROGRAMME = "AGIB_FINANCIAL_STATEMENTS_ENGINE"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "canonical_schema_only_no_buy_sell"

COMPANY_STATUSES = ("active", "suspended", "delisted")
REPORTING_STANDARDS = ("IND_AS", "IFRS", "US_GAAP", "OTHER", "UNKNOWN")

PERIOD_KINDS = ("annual", "quarterly", "half_year", "nine_months", "other")
CONSOLIDATION_TYPES = ("standalone", "consolidated", "unknown")
STATEMENT_SCOPES = ("as_reported", "restated", "revised")

STATEMENT_TYPES = (
    "income_statement",
    "balance_sheet",
    "cash_flow",
    "segment_statement",
    "notes",
    "share_capital",
    "eps",
)

FACT_STATUSES = ("draft", "published", "withheld", "flagged", "superseded")
VALIDATION_STATUSES = ("pending", "passed", "failed", "flagged")

CANONICAL_OBJECTS = (
    "company",
    "reporting_period",
    "statement",
    "financial_fact",
    "derived_metric",
    "validation_result",
    "version",
    "evidence_reference",
)
