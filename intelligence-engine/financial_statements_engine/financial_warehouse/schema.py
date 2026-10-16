"""FSE-06 Financial Warehouse contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FSE-06"
VERSION = "1.0.0"
SUBSYSTEM = "financial_warehouse"
PROGRAMME = "Financial Statements Engine"
WAREHOUSE_VERSION = "fwh-v1.0.0"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "warehouse_storage_retrieval_only_no_buy_sell_no_validation"

PUBLISHABLE_STATUSES = frozenset({"APPROVED", "APPROVED_WITH_WARNINGS"})
BLOCKED_STATUSES = frozenset({"REJECTED", "QUARANTINED"})

# Time-travel / restatement views
VIEWS = (
    "latest",
    "original",
    "as_reported",
    "as_restated",
    "as_published",
    "as_of_date",
    "as_originally_filed",
    "as_validated",
)

# Versioned consumer contracts
CONTRACT_IDS = (
    "dcf.v1",
    "forecast.v1",
    "screener.v1",
    "api.v1",
    "ask_agib.v1",
)

QUALITY_GUARANTEES = (
    "validated",
    "versioned",
    "traceable",
    "auditable",
    "immutable",
)
