"""FSE-FDO Phase 1 contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FSE-FDO"
SUBSYSTEM = "financial_data_operations"
VERSION = "fdo-v1.0.0"
PROGRAMME = "AGIB_FINANCIAL_STATEMENTS_ENGINE"
PHASE = "phase_1"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "operations_observability_only_no_buy_sell"

SPEC = "docs/FSE_FDO_FINANCIAL_DATA_OPERATIONS.md"

# Completeness period statuses
PERIOD_PRESENT = "present"
PERIOD_MISSING = "missing"
PERIOD_EXPECTED = "expected"
PERIOD_NOT_RELEASED = "not_released"

# Alert severities
ALERT_INFO = "info"
ALERT_WARNING = "warning"
ALERT_CRITICAL = "critical"

# Scheduler score weights (higher = more urgent)
WEIGHT_ZERO_RAW_EVIDENCE = 100
WEIGHT_MISSING_LATEST_ANNUAL = 40
WEIGHT_MISSING_LATEST_QUARTER = 30
WEIGHT_LOW_COVERAGE = 25
WEIGHT_STALE_DAYS = 0.5  # per day beyond freshness
WEIGHT_HIGH_PRIORITY_TICKER = 10

ANNUAL_FRESHNESS_DAYS = 400
QUARTERLY_FRESHNESS_DAYS = 120
