"""Institutional Writing Constitution v1.1 — IRE writing layer schema."""

from __future__ import annotations

CONSTITUTION_VERSION = "1.1"
PROGRAMME = "AGI Institutional Writing Constitution — How AGI Explains"
LAYER = "Institutional Research Engine (IRE)"
SCOPE = "Every user-facing research response"

# Default narrative hierarchy — institutional analyst voice, not template sections
RESPONSE_HIERARCHY: tuple[str, ...] = (
    "executive_summary",
    "what_matters_most",
    "investment_debate",
    "supporting_evidence",
    "key_uncertainties",
    "research_conclusion",
    "questions_before_you_decide",
)

SECTION_LABELS: dict[str, str] = {
    "executive_summary": "Executive Summary",
    "what_matters_most": "What Matters Most",
    "investment_debate": "The Investment Debate",
    "supporting_evidence": "Supporting Evidence",
    "key_uncertainties": "Key Uncertainties",
    "research_conclusion": "Research Conclusion",
    "questions_before_you_decide": "Questions Before You Decide",
    # Template-specific sections
    "what_changed": "What Changed",
    "what_didnt_change": "What Didn't Change",
    "market_implications": "Market Implications",
    "monitoring": "Monitoring",
    "current_expectations": "Current Expectations",
    "historical_context": "Historical Context",
    "business_comparison": "Business Comparison",
    "financial_comparison": "Financial Comparison",
    "competitive_position": "Competitive Position",
    "primary_risks": "Primary Risks",
    "probability": "Probability",
    "trade_offs": "Trade-offs",
}

# Legacy v1.0 keys → v1.1 (downstream compatibility)
LEGACY_SECTION_ALIASES: dict[str, str] = {
    "investment_meaning": "what_matters_most",
    "what_evidence_suggests": "supporting_evidence",
    "what_could_change_view": "key_uncertainties",
}

EXECUTIVE_SUMMARY_MAX_WORDS = 150
EVIDENCE_OBSERVATIONS_MIN = 3
EVIDENCE_OBSERVATIONS_MAX = 6
QUESTIONS_MIN = 3
QUESTIONS_MAX = 5

# Varied institutional evidence phrasing — never repeat "Evidence suggests..." on every line
EVIDENCE_PHRASE_TEMPLATES: tuple[str, ...] = (
    "Current evidence indicates",
    "Historical evidence shows",
    "Recent developments suggest",
    "Management commentary implies",
    "Financial performance indicates",
    "Market expectations suggest",
    "Operating trends indicate",
    "Available evidence does not currently support",
    "Current data suggests",
)

LENGTH_SIMPLE = (300, 500)
LENGTH_RESEARCH = (700, 1200)
LENGTH_DEEP = (2000, 4000)

FORBIDDEN_PHRASES: tuple[str, ...] = (
    "must buy",
    "must sell",
    "strong buy",
    "strong sell",
    "huge upside",
    "amazing",
    "excellent stock",
    "great company",
    "bullish",
    "bearish",
    "undervalued",
    "overvalued",
    "cheap",
    "expensive stock",
    "guaranteed",
    "multi-bagger",
    "target price",
    "entry price",
    "exit price",
)

PREFERRED_PHRASES: tuple[str, ...] = (
    "current evidence indicates",
    "the central investment debate",
    "the investment debate has shifted",
    "market expectations imply",
    "the business appears",
    "the primary uncertainty",
    "future value creation depends on",
    "future returns depend",
    "historical evidence indicates",
    "the thesis remains intact because",
    "evidence does not currently suggest",
    "institutional investors would likely focus on",
    "few investors question",
    "the real debate is",
)

FORBIDDEN_CLASSIFICATIONS: tuple[str, ...] = (
    "business quality: supportive",
    "risk: high",
    "growth: positive",
    "valuation: fair",
)

# Writing evaluation (release gate)
EVALUATION_DIMENSIONS: tuple[str, ...] = (
    "executive_summary_quality",
    "institutional_tone",
    "clarity",
    "evidence_usage",
    "prioritization",
    "implication_explanation",
    "uncertainty_handling",
    "readability",
)

# Investor-facing readability score
INSTITUTIONAL_READABILITY_DIMENSIONS: tuple[str, ...] = (
    "clarity",
    "institutional_tone",
    "prioritization",
    "evidence_integration",
    "narrative_flow",
    "investor_usefulness",
)

QUALITY_TEST_QUESTIONS: tuple[str, ...] = (
    "Does this improve understanding?",
    "Does this explain why?",
    "Does this connect evidence?",
    "Does this expose uncertainty?",
    "Does this avoid unnecessary facts?",
    "Would a portfolio manager forward this to the investment committee without editing?",
)

WRITING_PHILOSOPHY: tuple[str, ...] = (
    "Never summarize information — explain meaning",
    "Never list facts — connect facts",
    "Never report numbers — explain implications",
    "Never say what happened — explain why it matters",
    "Never tell users what to buy — help them understand what they are buying",
    "Write in narrative — not in rigid template repetition",
)
