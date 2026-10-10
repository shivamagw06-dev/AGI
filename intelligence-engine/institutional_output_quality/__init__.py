"""Final evidence and presentation quality gates for Ask AGI."""

from institutional_output_quality.guards import (
    CONGLOMERATE_FRAMEWORK_GUARDS,
    dedupe_research_text,
    filter_company_framework_text,
    has_numeric_valuation_evidence,
    has_supported_financial_evidence,
    has_supported_valuation_evidence,
    requires_full_company_analysis,
)

__all__ = [
    "CONGLOMERATE_FRAMEWORK_GUARDS",
    "dedupe_research_text",
    "filter_company_framework_text",
    "has_numeric_valuation_evidence",
    "has_supported_financial_evidence",
    "has_supported_valuation_evidence",
    "requires_full_company_analysis",
]
