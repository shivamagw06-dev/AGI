"""CIO-01 Comparative Intelligence Office — schema constants."""

from __future__ import annotations

CIO01_WORKSTREAM_ID = "CIO-01"
CIO01_PRODUCT = "Comparative Intelligence Office"
CIO01_VERSION = "cio-01-v1.0.0"
CIO01_SUBSYSTEM = "comparative_intelligence_office"
CIO01_SPEC = "docs/CIO_01_COMPARATIVE_INTELLIGENCE_OFFICE.md"
CIO01_RECOMMENDATION_POLICY = "comparison_only_no_buy_sell_no_new_analysis"
CIO01_PROGRAMME = "AGI_COMPARATIVE_INTELLIGENCE"

MODULE_FIRE01 = "FIRE-01"
MODULE_FIRE02 = "FIRE-02"
MODULE_FIRE03 = "FIRE-03"
MODULE_FIRE04 = "FIRE-04"
MODULE_FIRE05 = "FIRE-05"
MODULE_FIRE06 = "FIRE-06"

# Default modules for a full institutional comparison
DEFAULT_COMPARE_MODULES = (
    MODULE_FIRE06,
    MODULE_FIRE01,
    MODULE_FIRE02,
    MODULE_FIRE03,
    MODULE_FIRE04,
    MODULE_FIRE05,
)

COMPARISON_TYPES = (
    "Institutional Comparison",
    "Business Quality Comparison",
    "Balance Sheet Comparison",
    "Growth Comparison",
    "Execution Comparison",
    "Evidence Comparison",
    "Cash Flow Comparison",
    "Financial Health Comparison",
)

ICR_SECTIONS = (
    "executive_summary",
    "business_quality_comparison",
    "growth",
    "margins",
    "cash_flow",
    "balance_sheet",
    "capital_allocation",
    "management_execution",
    "evidence_alignment",
    "key_differences",
    "evidence_coverage",
    "confidence",
    "references",
)

ICR_SECTION_TITLES = {
    "executive_summary": "Executive Summary",
    "business_quality_comparison": "Business Quality Comparison",
    "growth": "Growth",
    "margins": "Margins",
    "cash_flow": "Cash Flow",
    "balance_sheet": "Balance Sheet",
    "capital_allocation": "Capital Allocation",
    "management_execution": "Management Execution",
    "evidence_alignment": "Evidence Alignment",
    "key_differences": "Key Differences",
    "evidence_coverage": "Evidence Coverage",
    "confidence": "Confidence",
    "references": "References",
}
