"""FIRE-04 — Evidence Fusion Engine contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FIRE-04"
PROGRAMME = "AGIB_FINANCIAL_INTELLIGENCE_REASONING_ENGINE"
SUBSYSTEM = "evidence_fusion_engine"
VERSION = "fire-04-v1.0.0"
PHASE = "phase_4"
SPEC = "docs/FIRE_04_EVIDENCE_FUSION_ENGINE.md"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "evidence_fusion_consistency_only_no_buy_sell"

CONF_HIGH = "High"
CONF_MEDIUM = "Medium"
CONF_LOW = "Low"

RESULT_SUPPORTED = "Supported"
RESULT_PARTIAL = "Partially Supported"
RESULT_NOT_SUPPORTED = "Not Supported"
RESULT_INSUFFICIENT = "Insufficient Evidence"

FUSION_RESULTS = (
    RESULT_SUPPORTED,
    RESULT_PARTIAL,
    RESULT_NOT_SUPPORTED,
    RESULT_INSUFFICIENT,
)

# EFR sections
REPORT_SECTIONS = (
    "executive_summary",
    "supported_statements",
    "partially_supported_statements",
    "unsupported_statements",
    "insufficient_evidence",
    "financial_consistency",
    "capital_allocation_consistency",
    "risk_consistency",
    "guidance_consistency",
    "overall_evidence_alignment",
)

# Finding theme categories
CAT_STRATEGY = "Management Strategy"
CAT_CASH = "Cash Generation"
CAT_DEBT = "Debt Reduction"
CAT_MARGIN = "Margin Consistency"
CAT_GROWTH = "Growth Consistency"
CAT_CAPITAL = "Capital Allocation Consistency"
CAT_RISK = "Risk Consistency"
CAT_GUIDANCE = "Guidance Consistency"
CAT_CAPACITY = "Capacity Expansion"
CAT_MISSING = "Missing Evidence"
CAT_CONTRADICTION = "Evidence Contradiction"

FUSION_METRICS = (
    "revenue",
    "operating_margin",
    "ebitda_margin",
    "net_margin",
    "gross_margin",
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
    "roe",
    "roce",
)
