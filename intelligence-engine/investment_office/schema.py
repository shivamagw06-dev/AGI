"""Investment Office schema constants."""

from __future__ import annotations

IO_VERSION = "investment-office-v1.0.0"
PROGRAMME = "AGI_INVESTMENT_OFFICE"
PROGRAMME_SHORT = "Investment Office"

PRIORITY = ("Critical", "High", "Medium", "Low")

ATTENTION_REASONS = (
    "Results Released",
    "Guidance Changed",
    "Margins Compressed",
    "Valuation Expanded",
    "Debt Increased",
    "Credit Rating Changed",
    "Management Change",
    "Research Outdated",
    "Prediction Failed",
    "Knowledge Coverage Low",
    "House View Review Suggested",
    "Material Monitor Change",
)

COPILOT_PROMPTS = (
    "What deserves my attention today?",
    "Which companies changed materially overnight?",
    "Which sectors improved?",
    "What research should I publish today?",
    "Which predictions are failing?",
    "What knowledge did AGI learn in the last 24 hours?",
)

# --- IO-01 Institutional Research Package (additive orchestration layer) ---

IO01_WORKSTREAM_ID = "IO-01"
IO01_PRODUCT = "Investment Office"
IO01_VERSION = "io-01-v1.0.0"
IO01_SUBSYSTEM = "institutional_investment_office"
IO01_SPEC = "docs/IO_01_INSTITUTIONAL_INVESTMENT_OFFICE.md"
IO01_RECOMMENDATION_POLICY = "orchestration_only_no_buy_sell_no_new_analysis"

# Human titles for IRP section keys (report presentation)
IRP_SECTION_TITLES = {
    "executive_summary": "Executive Summary",
    "company_snapshot": "Company Snapshot",
    "business_quality": "Business Quality",
    "financial_trends": "Financial Trends",
    "financial_relationships": "Financial Relationships",
    "business_strategy": "Business Strategy",
    "management_execution": "Management Execution",
    "evidence_consistency": "Evidence Consistency",
    "key_strengths": "Key Strengths",
    "key_risks": "Key Risks",
    "outstanding_questions": "Outstanding Questions",
    "confidence_summary": "Confidence Summary",
    "evidence_references": "Evidence References",
}

PACKAGE_FINANCIAL_HEALTH = "Financial Health"
PACKAGE_BUSINESS_QUALITY = "Business Quality"
PACKAGE_MANAGEMENT_REVIEW = "Management Review"
PACKAGE_EVIDENCE_REVIEW = "Evidence Review"
PACKAGE_EXECUTION_REVIEW = "Execution Review"
PACKAGE_CAPITAL_ALLOCATION = "Capital Allocation"
PACKAGE_CASH_FLOW = "Cash Flow Review"
PACKAGE_BALANCE_SHEET = "Balance Sheet Review"
PACKAGE_GROWTH = "Growth Review"
PACKAGE_SNAPSHOT = "Company Snapshot"
PACKAGE_INSTITUTIONAL_BRIEF = "Institutional Brief"

PACKAGE_TYPES = (
    PACKAGE_FINANCIAL_HEALTH,
    PACKAGE_BUSINESS_QUALITY,
    PACKAGE_MANAGEMENT_REVIEW,
    PACKAGE_EVIDENCE_REVIEW,
    PACKAGE_EXECUTION_REVIEW,
    PACKAGE_CAPITAL_ALLOCATION,
    PACKAGE_CASH_FLOW,
    PACKAGE_BALANCE_SHEET,
    PACKAGE_GROWTH,
    PACKAGE_SNAPSHOT,
    PACKAGE_INSTITUTIONAL_BRIEF,
)

MODULE_FIRE01 = "FIRE-01"
MODULE_FIRE02 = "FIRE-02"
MODULE_FIRE03 = "FIRE-03"
MODULE_FIRE04 = "FIRE-04"
MODULE_FIRE05 = "FIRE-05"
MODULE_FIRE06 = "FIRE-06"
MODULE_FKB = "FKB"

IRP_SECTIONS = (
    "executive_summary",
    "company_snapshot",
    "business_quality",
    "financial_trends",
    "financial_relationships",
    "business_strategy",
    "management_execution",
    "evidence_consistency",
    "key_strengths",
    "key_risks",
    "outstanding_questions",
    "confidence_summary",
    "evidence_references",
)
