"""FIRE-05 — Management Execution & Temporal Evidence Engine contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FIRE-05"
PROGRAMME = "AGIB_FINANCIAL_INTELLIGENCE_REASONING_ENGINE"
SUBSYSTEM = "management_execution_temporal_engine"
VERSION = "fire-05-v1.0.0"
PHASE = "phase_5"
SPEC = "docs/FIRE_05_MANAGEMENT_EXECUTION_TEMPORAL_ENGINE.md"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "execution_tracking_only_no_honesty_judgment_no_buy_sell"

CONF_HIGH = "High"
CONF_MEDIUM = "Medium"
CONF_LOW = "Low"

STATUS_DELIVERED = "Delivered"
STATUS_PARTIAL = "Partially Delivered"
STATUS_NOT_YET = "Not Yet Delivered"
STATUS_CANNOT = "Cannot Yet Evaluate"
STATUS_SUPERSEDED = "Superseded"

EXECUTION_STATUSES = (
    STATUS_DELIVERED,
    STATUS_PARTIAL,
    STATUS_NOT_YET,
    STATUS_CANNOT,
    STATUS_SUPERSEDED,
)

# Time windows (months)
WINDOWS = {
    "quarter": 3,
    "year": 12,
    "y2": 24,
    "y3": 36,
    "y5": 60,
}
DEFAULT_WINDOWS = ("year", "y2", "y3")

REPORT_SECTIONS = (
    "executive_summary",
    "delivered_objectives",
    "partially_delivered",
    "outstanding_objectives",
    "superseded_objectives",
    "cannot_yet_evaluate",
    "execution_timeline",
    "capital_allocation_delivery",
    "strategy_delivery",
    "overall_execution_score",
)

# Canonical statement-type categories (spec)
CAT_GROWTH = "Growth"
CAT_MARGIN = "Margin"
CAT_DEBT = "Debt"
CAT_LIQUIDITY = "Liquidity"
CAT_CAPITAL = "Capital Allocation"
CAT_EXPANSION = "Expansion"
CAT_CAPACITY = "Capacity"
CAT_DIGITAL = "Digital Transformation"
CAT_ACQUISITIONS = "Acquisitions"
CAT_DIVESTITURES = "Divestitures"
CAT_EXPORTS = "Exports"
CAT_PRODUCTS = "Products"
CAT_EFFICIENCY = "Efficiency"
CAT_COST = "Cost Optimisation"
CAT_GOVERNANCE = "Governance"
CAT_ESG = "ESG"
CAT_RISK = "Risk Mitigation"

EXECUTION_METRICS = (
    "revenue",
    "operating_margin",
    "ebitda_margin",
    "net_margin",
    "operating_cash_flow",
    "free_cash_flow",
    "working_capital",
    "total_debt",
    "net_debt",
    "interest_coverage",
    "cash",
    "capex",
    "dividends",
    "share_buybacks",
)
