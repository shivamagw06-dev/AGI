"""FSE-03 Metric Registry — version & record contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FSE-03"
SUBSYSTEM = "metric_registry"
REGISTRY_VERSION = "cfdm-metric-registry-v1.0.0"
PROGRAMME = "AGIB_FINANCIAL_STATEMENTS_ENGINE"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "schema_registry_only_no_buy_sell"

METRIC_STATUSES = ("active", "deprecated")
METRIC_KINDS = ("reported", "derived")

STATEMENT_TYPES = (
    "income_statement",
    "balance_sheet",
    "cash_flow",
    "segment_statement",
    "notes",
    "share_capital",
    "eps",
)

CATEGORIES = (
    "income",
    "balance",
    "cash_flow",
    "segment",
    "capital_structure",
    "derived",
)

ALLOWED_SCALES = ("ones", "thousands", "lakhs", "crores", "millions", "billions")
