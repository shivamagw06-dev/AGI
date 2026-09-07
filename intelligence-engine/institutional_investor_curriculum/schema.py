"""Institutional Investor Curriculum v1.0 — schema and constants."""

from __future__ import annotations

CURRICULUM_VERSION = "1.0"
CURRICULUM_NAME = "AGI Institutional Investor Curriculum"
LAYER = "Institutional Research Engine (IRE)"
ARCHITECTURE_STATUS = "Architecture Freeze v1.0 — research quality and communication only"

DECISION_DOMAIN_COUNT = 10
QUESTIONS_PER_DOMAIN = 10
UNIVERSAL_QUESTION_COUNT = 100
ANCHOR_COMPANY_COUNT = 10
TARGET_BENCHMARK_COUNT = 1000  # 100 universal × 10 anchors
HALL_OF_FAME_COUNT = 100  # universal curriculum on TCS anchor
WEEKLY_REVIEW_SAMPLE = 100
MONTHLY_REVIEW_SAMPLE = 100

DECISION_DOMAINS: tuple[str, ...] = (
    "idea_generation",
    "business_understanding",
    "competitive_advantage",
    "management_quality",
    "financial_quality",
    "valuation",
    "investment_debate",
    "portfolio_construction",
    "monitoring",
    "decision_review",
)

DOMAIN_TITLES: dict[str, str] = {
    "idea_generation": "Idea Generation",
    "business_understanding": "Business Understanding",
    "competitive_advantage": "Competitive Advantage",
    "management_quality": "Management Quality",
    "financial_quality": "Financial Quality",
    "valuation": "Valuation",
    "investment_debate": "Investment Debate",
    "portfolio_construction": "Portfolio Construction",
    "monitoring": "Monitoring",
    "decision_review": "Decision Review",
}

DOMAIN_PURPOSES: dict[str, str] = {
    "idea_generation": "Should this company even deserve research?",
    "business_understanding": "Understand the business before discussing valuation.",
    "competitive_advantage": "Determine long-term durability.",
    "management_quality": "Evaluate leadership.",
    "financial_quality": "Assess financial durability.",
    "valuation": "Understand expectations.",
    "investment_debate": "Explain what intelligent investors disagree about.",
    "portfolio_construction": "Think beyond one company.",
    "monitoring": "Teach continuous research.",
    "decision_review": "Teach learning.",
}

DOMAIN_EDITORIAL_OBJECTIVES: dict[str, str] = {
    "idea_generation": "Teach AGI to prioritize research.",
    "business_understanding": "Explain businesses clearly.",
    "competitive_advantage": "Teach structural thinking.",
    "management_quality": "Separate business quality from management quality.",
    "financial_quality": "Explain financial quality.",
    "valuation": "Teach expectations, not multiples.",
    "investment_debate": "Teach probabilistic thinking.",
    "portfolio_construction": "Teach allocation.",
    "monitoring": "Teach dynamic investing.",
    "decision_review": "Build institutional memory.",
}

# Phase 1 anchor companies — same 100 institutional questions each
ANCHOR_COMPANIES: tuple[tuple[str, str], ...] = (
    ("TCS", "Tata Consultancy Services"),
    ("INFY", "Infosys"),
    ("HDFCBANK", "HDFC Bank"),
    ("ICICIBANK", "ICICI Bank"),
    ("RELIANCE", "Reliance Industries"),
    ("TITAN", "Titan"),
    ("ASIANPAINT", "Asian Paints"),
    ("BHARTIARTL", "Bharti Airtel"),
    ("LT", "Larsen & Toubro"),
    ("MARUTI", "Maruti Suzuki"),
)

EDITORIAL_PRINCIPLES: tuple[str, ...] = (
    "Never answer the literal question only — answer the underlying investment question.",
    "Never explain facts without implications.",
    "Never present valuation without expectations.",
    "Never discuss risk without monitoring.",
    "Never conclude without uncertainty.",
    "Never summarize without teaching.",
)

# Curriculum scorecard dimensions (institutional thinking)
CURRICULUM_SCORECARD: tuple[str, ...] = (
    "clarity",
    "institutional_tone",
    "business_understanding",
    "investment_insight",
    "evidence_integration",
    "narrative_flow",
    "explanation_quality",
    "portfolio_relevance",
    "investor_usefulness",
    "forward_without_editing",
    "overall_editorial_score",
)

EDITORIAL_WORKFLOW: tuple[str, ...] = (
    "question",
    "decision_domain",
    "playbook",
    "research_workflow",
    "knowledge_objects",
    "evidence",
    "response_planning",
    "institutional_writing",
    "editorial_review",
    "hall_of_fame",
)

SUCCESS_QUOTE = (
    'Institutional investors say "This is how I would analyse the business." '
    'rather than "This is a good AI summary."'
)
