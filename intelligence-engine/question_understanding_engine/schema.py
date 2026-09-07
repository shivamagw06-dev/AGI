"""Question Understanding Engine v1.0 — schema and constants."""

from __future__ import annotations

QUE_VERSION = "1.1"
QUE_NAME = "AGI Question Understanding Engine"
LAYER = "Institutional Research Engine (IRE)"
ARCHITECTURE_STATUS = "Architecture Freeze v1.1 — core runtime, research brief contract"

TARGET_TAXONOMY_COUNT = 500

DECISION_TYPES: tuple[str, ...] = (
    "Capital Allocation",
    "Research Priority",
    "Business Understanding",
    "Valuation Assessment",
    "Peer Selection",
    "Portfolio Construction",
    "Risk Assessment",
    "Monitoring",
    "Thesis Validation",
    "Earnings Review",
    "Macro Impact",
    "Sector Allocation",
    "Idea Generation",
    "Education",
    "Explainability",
    "Decision Review",
    "Unknown",
)

INFORMATION_CATEGORIES: tuple[str, ...] = (
    "Business Quality",
    "Competitive Position",
    "Financial Quality",
    "Valuation",
    "Management",
    "Growth",
    "Risks",
    "Industry",
    "Macro",
    "Portfolio Fit",
    "Evidence",
)

RESPONSE_OBJECTIVES: tuple[str, ...] = (
    "Teach",
    "Explain",
    "Evaluate",
    "Compare",
    "Prioritize",
    "Challenge",
    "Monitor",
    "Recommend",
    "Summarize",
    "Research",
)

EXPECTED_DELIVERABLES: tuple[str, ...] = (
    "Investment assessment clarity",
    "Expectations embedded in price",
    "Investment-relevant peer differences",
    "Monitoring checklist",
    "Thesis validation summary",
    "Risk prioritization",
    "Portfolio role clarity",
    "Research prioritization rationale",
    "Business model understanding",
    "Educational explanation",
)

# Domain → decision type (IIC alignment)
DOMAIN_DECISION_MAP: dict[str, str] = {
    "idea_generation": "Research Priority",
    "business_understanding": "Business Understanding",
    "competitive_advantage": "Business Understanding",
    "management_quality": "Business Understanding",
    "financial_quality": "Business Understanding",
    "valuation": "Valuation Assessment",
    "investment_debate": "Thesis Validation",
    "portfolio_construction": "Portfolio Construction",
    "monitoring": "Monitoring",
    "decision_review": "Decision Review",
}

RESEARCH_OBJECTIVES: dict[str, str] = {
    "Capital Allocation": "Determine whether expected return justifies risk.",
    "Research Priority": "Determine whether deeper research could materially change investment conclusions.",
    "Business Understanding": "Explain how the business works and what drives value.",
    "Valuation Assessment": "Determine what expectations are embedded in price and whether they are justified.",
    "Peer Selection": "Identify differences that matter for investment decisions.",
    "Portfolio Construction": "Determine how this company fits alongside other holdings.",
    "Risk Assessment": "Identify and prioritize risks that could impair the thesis.",
    "Monitoring": "Identify events that should trigger thesis review.",
    "Thesis Validation": "Determine whether the investment thesis still holds.",
    "Earnings Review": "Determine what changed and whether the thesis strengthened or weakened.",
    "Macro Impact": "Determine how macro variables affect the investment case.",
    "Sector Allocation": "Determine sector attractiveness and company positioning.",
    "Idea Generation": "Determine whether the company deserves analyst attention.",
    "Education": "Build investor understanding of concepts or businesses.",
    "Explainability": "Show evidence chain and confidence behind conclusions.",
    "Decision Review": "Determine what was learned and how conclusions evolved.",
    "Unknown": "Clarify the underlying investment decision before proceeding.",
}

RESPONSE_STRUCTURE_BY_DECISION: dict[str, str] = {
    "Capital Allocation": "executive_summary → investment_debate → evidence → uncertainties → conclusion → questions",
    "Research Priority": "executive_summary → research_gaps → evidence → priorities → conclusion",
    "Business Understanding": "executive_summary → business_model → competitive_position → evidence → conclusion",
    "Valuation Assessment": "executive_summary → expectations → historical_context → evidence → risks → conclusion",
    "Peer Selection": "executive_summary → business_comparison → financial_comparison → decision_differences → conclusion",
    "Portfolio Construction": "executive_summary → portfolio_role → overlap → alternatives → conclusion",
    "Risk Assessment": "executive_summary → primary_risks → evidence → monitoring → conclusion",
    "Monitoring": "executive_summary → KPIs → thesis_triggers → evidence → conclusion",
    "Thesis Validation": "executive_summary → investment_debate → evidence_balance → what_changes_view → conclusion",
    "Earnings Review": "executive_summary → what_changed → what_didnt → thesis_impact → monitoring",
    "Macro Impact": "executive_summary → macro_drivers → company_implications → evidence → conclusion",
    "Sector Allocation": "executive_summary → sector_context → company_implications → conclusion",
    "Idea Generation": "executive_summary → why_interesting → catalysts → research_priority → conclusion",
    "Education": "executive_summary → plain_explanation → implications → conclusion",
    "Explainability": "executive_summary → thesis → supporting_evidence → contradicting_evidence → confidence",
    "Decision Review": "executive_summary → assumptions_review → lessons → evolved_conclusion",
    "Unknown": "executive_summary → clarifying_questions → evidence → conclusion",
}
