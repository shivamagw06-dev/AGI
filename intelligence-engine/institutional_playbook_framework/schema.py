"""Institutional Playbook Framework v1.0 — methodology layer between Ask and Investment OS."""

from __future__ import annotations

FRAMEWORK_VERSION = "1.0"
PROGRAMME = "AGI Institutional Playbook Framework — Standardized Research Methodology"
SCOPE = "Every Ask response; consumed by Investment OS"

EXECUTION_PIPELINE: tuple[str, ...] = (
    "Intent",
    "Evidence",
    "Reasoning",
    "Trade-offs",
    "Research Conclusion",
    "Questions Before You Decide",
)

INTELLIGENCE_TYPES: tuple[str, ...] = (
    "Company Intelligence",
    "Financial Intelligence",
    "Valuation Intelligence",
    "Forecast Intelligence",
    "Evidence Intelligence",
    "Sector Intelligence",
    "Macro Intelligence",
    "Portfolio Intelligence",
    "Historical Intelligence",
    "Risk Intelligence",
    "Governance Intelligence",
    "Management Intelligence",
    "Alternative Data Intelligence",
    "Technical Intelligence",
    "Market Intelligence",
)

REASONING_RULES: tuple[str, ...] = (
    "What happened",
    "Why it happened",
    "What it implies",
    "What remains uncertain",
    "What evidence would change the conclusion",
)

OUTPUT_PRINCIPLES: tuple[str, ...] = (
    "What does this mean?",
    "Why does it matter?",
    "What evidence supports it?",
    "What risks remain?",
    "What should an institutional investor investigate next?",
)

USER_GUIDANCE_QUESTIONS: tuple[str, ...] = (
    "Does current valuation justify expected growth?",
    "Has the investment thesis changed?",
    "What assumptions are already reflected in today's price?",
    "What evidence could invalidate today's thesis?",
    "How does this compare with alternatives?",
    "Does this improve portfolio diversification?",
)

FORBIDDEN_OUTPUTS: tuple[str, ...] = (
    "buy this stock",
    "sell this stock",
    "strong buy",
    "strong sell",
    "target price",
    "entry price",
    "exit price",
    "guaranteed returns",
    "multi-bagger",
)

# Standard journey for full investment assessment workflows
INVESTMENT_ASSESSMENT_JOURNEY: tuple[str, ...] = (
    "Investment Assessment",
    "Business Quality",
    "Financial Quality",
    "Valuation",
    "Growth",
    "Risks",
    "Peer Comparison",
    "Portfolio Fit",
    "Thesis Review",
    "Decision Complete",
)

JOURNEY_STEP_ALIASES: dict[str, str] = {
    "business": "Business Quality",
    "business quality": "Business Quality",
    "financial": "Financial Quality",
    "financial quality": "Financial Quality",
    "financial strength": "Financial Quality",
    "valuation": "Valuation",
    "growth": "Growth",
    "risk": "Risks",
    "risks": "Risks",
    "peer": "Peer Comparison",
    "peer comparison": "Peer Comparison",
    "compare": "Peer Comparison",
    "portfolio": "Portfolio Fit",
    "portfolio fit": "Portfolio Fit",
    "thesis": "Thesis Review",
    "thesis review": "Thesis Review",
    "earnings": "Financial Quality",
    "management": "Business Quality",
    "moat": "Business Quality",
}
