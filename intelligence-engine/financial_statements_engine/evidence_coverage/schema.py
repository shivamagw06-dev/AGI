"""FSE-ECD Evidence Coverage Dashboard contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FSE-ECD"
VERSION = "1.0.0"
SUBSYSTEM = "evidence_coverage_dashboard"
PROGRAMME = "Financial Statements Engine"
ECD_VERSION = "ecd-v1.0.0"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "coverage_measurement_only_no_buy_sell"

# Funnel stages in pipeline order — every target is 100% of selected universe
FUNNEL_STAGES = (
    "discovered",
    "latest_annual_filing",
    "latest_quarterly_filing",
    "parsed",
    "validated",
    "published",
    "derived_metrics",
)

STAGE_TARGETS = {stage: 1.0 for stage in FUNNEL_STAGES}

STAGE_LABELS = {
    "discovered": "Companies discovered",
    "latest_annual_filing": "Companies with latest annual filing",
    "latest_quarterly_filing": "Companies with latest quarterly filing",
    "parsed": "Companies parsed",
    "validated": "Companies validated",
    "published": "Companies published",
    "derived_metrics": "Companies with derived metrics",
}

# Freshness windows for "latest" filings (India FY ends March)
ANNUAL_FRESHNESS_DAYS = 550  # ~18 months — FY25 still acceptable mid-FY26
QUARTERLY_FRESHNESS_DAYS = 180  # ~6 months — covers latest quarter lag
