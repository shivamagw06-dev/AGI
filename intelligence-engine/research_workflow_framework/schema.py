"""Research Workflow Framework v1.0 — institutional research process orchestration."""

from __future__ import annotations

FRAMEWORK_VERSION = "1.0"
PROGRAMME = "AGI Research Workflow Framework — Institutional Research Process"
SCOPE = "Above playbooks, below Investment OS"

REASONING_PIPELINE: tuple[str, ...] = (
    "Evidence",
    "Facts",
    "Drivers",
    "Implications",
    "Trade-offs",
    "Research Conclusion",
    "Open Questions",
)

QUALITY_STANDARDS: tuple[str, ...] = (
    "Evidence completeness",
    "Source traceability",
    "Coverage disclosure",
    "Confidence explanation",
    "Historical context",
    "Reasoning transparency",
    "Validation",
    "Reproducibility",
)

FORBIDDEN_OUTPUTS: tuple[str, ...] = (
    "buy",
    "sell",
    "target price",
    "entry price",
    "exit price",
    "strong buy",
    "strong sell",
    "guaranteed returns",
)

# Core reusable playbooks (workflow composition units)
CORE_PLAYBOOKS: tuple[str, ...] = (
    "business_quality",
    "financial_quality",
    "management_quality",
    "competitive_position",
    "economic_moat",
    "valuation",
    "growth_drivers",
    "risk_analysis",
    "capital_allocation",
    "governance",
    "forecast_analysis",
    "industry_analysis",
    "macro_analysis",
    "portfolio_fit",
    "investment_thesis",
    "evidence_review",
    "research_conclusion",
    "questions_before_you_decide",
)

# Map IPF playbook keys → core playbook / status label
PLAYBOOK_STATUS_LABELS: dict[str, str] = {
    "investment_assessment": "Investment Assessment",
    "business_quality_assessment": "Business Quality",
    "economic_moat": "Business Quality",
    "financial_analysis": "Financial Quality",
    "earnings_review": "Financial Quality",
    "management_assessment": "Management",
    "valuation_assessment": "Valuation",
    "risk_assessment": "Risks",
    "peer_comparison": "Peer Comparison",
    "portfolio_assessment": "Portfolio Fit",
    "investment_thesis": "Thesis Stress Test",
    "thesis_evolution": "Thesis Review",
    "market_overview": "Market Overview",
    "sector_analysis": "Sector Analysis",
    "macro_analysis": "Macro Assessment",
    "education": "Education",
}

STATUS_COMPLETE = "complete"
STATUS_NEEDS_REVIEW = "needs_review"
STATUS_PENDING = "pending"
