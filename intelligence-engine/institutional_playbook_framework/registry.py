"""Playbook registry — purpose, intelligence, validation, and journey per playbook."""

from __future__ import annotations

from typing import Any

from institutional_playbook_framework.schema import INVESTMENT_ASSESSMENT_JOURNEY, INTELLIGENCE_TYPES


def _pb(
    key: str,
    *,
    purpose: str,
    supported_intents: tuple[str, ...],
    question_cues: tuple[str, ...] = (),
    required_intelligence: tuple[str, ...],
    required_evidence: tuple[str, ...],
    reasoning_framework: tuple[str, ...],
    output_contract: tuple[str, ...],
    follow_up_templates: tuple[str, ...],
    acceptance_tests: tuple[str, ...],
    journey_steps: tuple[str, ...] | None = None,
    iap_playbook_id: str | None = None,
) -> dict[str, Any]:
    return {
        "playbook_key": key,
        "name": key.replace("_", " ").title(),
        "purpose": purpose,
        "supported_intents": supported_intents,
        "question_cues": question_cues,
        "required_intelligence": required_intelligence,
        "required_evidence": required_evidence,
        "reasoning_framework": reasoning_framework,
        "validation_rules": {
            "forbidden_outputs": True,
            "evidence_required": True,
            "reasoning_implications": True,
            "user_guidance_required": True,
        },
        "output_contract": output_contract,
        "follow_up_templates": follow_up_templates,
        "acceptance_tests": acceptance_tests,
        "journey_steps": journey_steps or INVESTMENT_ASSESSMENT_JOURNEY,
        "iap_playbook_id": iap_playbook_id,
    }


PLAYBOOK_REGISTRY: dict[str, dict[str, Any]] = {
    "investment_assessment": _pb(
        "investment_assessment",
        purpose="Determine whether a company deserves institutional investment consideration",
        supported_intents=("Analyse", "Assess", "CrossDomain"),
        question_cues=("should i buy", "worth investing", "investment case", "deserves consideration"),
        required_intelligence=(
            "Company Intelligence",
            "Financial Intelligence",
            "Valuation Intelligence",
            "Evidence Intelligence",
            "Sector Intelligence",
            "Risk Intelligence",
        ),
        required_evidence=("financials", "annual_report", "peer_metrics", "valuation"),
        reasoning_framework=(
            "Business Quality",
            "Financial Strength",
            "Management",
            "Growth",
            "Valuation",
            "Risks",
            "Portfolio Context",
            "Research Conclusion",
        ),
        output_contract=(
            "Executive Summary",
            "Business Quality",
            "Financial Strength",
            "Valuation",
            "Risks",
            "Research Conclusion",
            "Questions Before You Decide",
            "Supporting Evidence",
            "Confidence",
        ),
        follow_up_templates=(
            "Compare {ticker} with top peer",
            "Review {ticker} valuation history",
            "Understand {ticker} earnings drivers",
            "Assess {ticker} portfolio fit",
            "Review {ticker} management execution",
        ),
        acceptance_tests=(
            "Business Quality",
            "Financial Strength",
            "Valuation",
            "Risks",
            "Growth",
            "Research Conclusion",
            "Questions Before You Decide",
            "Supporting Evidence",
            "Confidence explained",
            "No BUY/SELL",
        ),
        iap_playbook_id="PB_COMPANY_QUALITY",
    ),
    "valuation_assessment": _pb(
        "valuation_assessment",
        purpose="Evaluate current valuation versus history, peers, and expectations",
        supported_intents=("Valuation",),
        question_cues=("expensive", "cheap", "overvalued", "undervalued", "pe ratio", "valuation"),
        required_intelligence=("Valuation Intelligence", "Financial Intelligence", "Historical Intelligence"),
        required_evidence=("valuation", "peer_metrics", "historical_multiples"),
        reasoning_framework=(
            "Current Level",
            "Historical Context",
            "Peer Context",
            "Growth/ROE Context",
            "Implications",
        ),
        output_contract=("Valuation Assessment", "Historical Context", "Peer Context", "Implications", "Questions Before You Decide"),
        follow_up_templates=(
            "Show {ticker} valuation vs 5-year history",
            "Compare {ticker} multiples with peers",
            "What growth is priced into {ticker}?",
        ),
        acceptance_tests=("Valuation", "Historical Context", "Peer Context", "No BUY/SELL"),
        journey_steps=("Valuation", "Historical Context", "Peer Comparison", "Growth Assumptions", "Thesis Review", "Decision Complete"),
        iap_playbook_id="PB_VALUATION_RELATIVE",
    ),
    "earnings_review": _pb(
        "earnings_review",
        purpose="Determine whether earnings changed the investment thesis",
        supported_intents=("Analyse", "Explain", "Documents"),
        question_cues=("earnings", "results", "quarter", "q1", "q2", "q3", "q4"),
        required_intelligence=("Financial Intelligence", "Forecast Intelligence", "Evidence Intelligence"),
        required_evidence=("earnings", "financials", "management_commentary"),
        reasoning_framework=("What Changed", "Why", "Temporary vs Structural", "Thesis Impact", "Research Conclusion"),
        output_contract=("What Changed", "Why It Matters", "Thesis Impact", "Research Conclusion", "Questions Before You Decide"),
        follow_up_templates=(
            "Did {ticker} earnings change the thesis?",
            "Compare {ticker} margin trend with peers",
            "Review {ticker} guidance vs consensus",
        ),
        acceptance_tests=("What Changed", "Thesis Impact", "Research Conclusion", "No BUY/SELL"),
        journey_steps=("Earnings Review", "Financial Quality", "Growth", "Valuation", "Thesis Review", "Decision Complete"),
        iap_playbook_id="PB_COMPANY_EARNINGS",
    ),
    "business_quality_assessment": _pb(
        "business_quality_assessment",
        purpose="Assess sustainable competitive advantage and franchise quality",
        supported_intents=("Analyse", "Explain"),
        question_cues=("business quality", "moat", "competitive advantage", "franchise"),
        required_intelligence=("Company Intelligence", "Evidence Intelligence", "Sector Intelligence"),
        required_evidence=("annual_report", "peer_metrics", "governance"),
        reasoning_framework=("Business Model", "Moat", "Revenue Drivers", "Profit Drivers", "Risks"),
        output_contract=("Business Quality", "Competitive Advantage", "Risks", "Research Conclusion"),
        follow_up_templates=("Assess {ticker} moat durability", "Compare {ticker} ROIC with peers"),
        acceptance_tests=("Business Quality", "Research Conclusion", "No BUY/SELL"),
        journey_steps=("Business Quality", "Financial Quality", "Valuation", "Risks", "Thesis Review", "Decision Complete"),
        iap_playbook_id="PB_COMPANY_QUALITY",
    ),
    "peer_comparison": _pb(
        "peer_comparison",
        purpose="Compare quality, growth, and valuation across peers",
        supported_intents=("Compare",),
        question_cues=("compare", " vs ", " versus ", "better than", "peer"),
        required_intelligence=("Company Intelligence", "Valuation Intelligence", "Financial Intelligence"),
        required_evidence=("peer_metrics", "valuation"),
        reasoning_framework=("Peer Set", "Quality Differences", "Valuation Differences", "Research Conclusion"),
        output_contract=("Peer Set", "Comparison", "Research Conclusion", "Questions Before You Decide"),
        follow_up_templates=("Deep dive {ticker} business quality", "Review valuation gap drivers"),
        acceptance_tests=("Peer Comparison", "Research Conclusion", "No BUY/SELL"),
        journey_steps=("Peer Comparison", "Business Quality", "Valuation", "Portfolio Fit", "Decision Complete"),
        iap_playbook_id="PB_VALUATION_PEER",
    ),
    "portfolio_assessment": _pb(
        "portfolio_assessment",
        purpose="Evaluate holdings, concentration, and opportunity cost",
        supported_intents=("Portfolio",),
        question_cues=("portfolio", "holdings", "allocation", "diversification"),
        required_intelligence=("Portfolio Intelligence", "Valuation Intelligence", "Risk Intelligence"),
        required_evidence=("portfolio_holdings", "correlation", "valuation"),
        reasoning_framework=("Holdings Context", "Concentration", "Correlation", "Opportunity Cost", "Research Conclusion"),
        output_contract=("Portfolio Context", "Concentration", "Research Conclusion", "Questions Before You Decide"),
        follow_up_templates=("Review sector concentration", "Assess correlation risk", "Compare with benchmark"),
        acceptance_tests=("Portfolio Context", "Research Conclusion", "No BUY/SELL"),
        journey_steps=("Portfolio Assessment", "Diversification", "Risk", "Opportunity Cost", "Decision Complete"),
    ),
    "market_overview": _pb(
        "market_overview",
        purpose="Understand current market state and institutional research priorities",
        supported_intents=("Macro", "Industry"),
        question_cues=("market outlook", "nifty", "sensex", "market today", "market tomorrow"),
        required_intelligence=("Market Intelligence", "Macro Intelligence", "Sector Intelligence"),
        required_evidence=("market_data", "flows", "breadth"),
        reasoning_framework=("Regime", "Valuation", "Breadth", "Flows", "Research Priorities"),
        output_contract=("Market Overview", "Drivers", "Risks", "Research Priorities"),
        follow_up_templates=("Which sectors lead rotation?", "Review FII/DII flow trend", "Assess market valuation"),
        acceptance_tests=("Market Overview", "Research Priorities", "No BUY/SELL"),
        journey_steps=("Market Overview", "Macro", "Sector Rotation", "Risk", "Decision Complete"),
        iap_playbook_id="PB_MACRO_REGIME",
    ),
    "education": _pb(
        "education",
        purpose="Explain concepts with investment relevance",
        supported_intents=("Explain", "Education", "Unknown"),
        question_cues=("what is", "explain", "how does", "define"),
        required_intelligence=("Evidence Intelligence",),
        required_evidence=("reference"),
        reasoning_framework=("Concept", "Mechanism", "Investment Relevance", "Examples"),
        output_contract=("Concept", "Investment Relevance", "Examples"),
        follow_up_templates=("Show a real company example", "How would an investor use this?"),
        acceptance_tests=("Concept explained", "No BUY/SELL"),
        journey_steps=("Education", "Examples", "Application", "Decision Complete"),
    ),
}

# Extended registry keys (metadata-only stubs linking to nearest full playbook)
_EXTENDED_KEYS: tuple[tuple[str, str], ...] = (
    ("financial_analysis", "investment_assessment"),
    ("risk_assessment", "investment_assessment"),
    ("management_assessment", "business_quality_assessment"),
    ("competitive_position", "business_quality_assessment"),
    ("economic_moat", "business_quality_assessment"),
    ("capital_allocation", "business_quality_assessment"),
    ("corporate_governance", "business_quality_assessment"),
    ("industry_analysis", "market_overview"),
    ("sector_analysis", "market_overview"),
    ("macro_analysis", "market_overview"),
    ("portfolio_diversification", "portfolio_assessment"),
    ("portfolio_monitoring", "portfolio_assessment"),
    ("investment_thesis", "investment_assessment"),
    ("thesis_evolution", "investment_assessment"),
    ("news_impact", "earnings_review"),
    ("corporate_action_analysis", "earnings_review"),
    ("dividend_analysis", "financial_analysis"),
    ("technical_analysis", "valuation_assessment"),
    ("forecast_analysis", "earnings_review"),
    ("historical_analysis", "valuation_assessment"),
    ("scenario_analysis", "investment_assessment"),
    ("stress_testing", "risk_assessment"),
    ("alternative_data_assessment", "business_quality_assessment"),
    ("watchlist_review", "investment_assessment"),
    ("institutional_monitoring", "portfolio_assessment"),
)

for _alias, _base in _EXTENDED_KEYS:
    if _alias not in PLAYBOOK_REGISTRY and _base in PLAYBOOK_REGISTRY:
        row = dict(PLAYBOOK_REGISTRY[_base])
        row["playbook_key"] = _alias
        row["name"] = _alias.replace("_", " ").title()
        row["alias_of"] = _base
        row["question_cues"] = ()  # aliases resolve via IRL/IAP — avoid duplicate cue hits
        PLAYBOOK_REGISTRY[_alias] = row


def list_playbook_keys() -> list[str]:
    return sorted(PLAYBOOK_REGISTRY.keys())


def get_playbook(key: str) -> dict[str, Any] | None:
    return PLAYBOOK_REGISTRY.get(key)


def registry_summary() -> dict[str, Any]:
    return {
        "version": "1.0",
        "count": len(PLAYBOOK_REGISTRY),
        "playbook_keys": list_playbook_keys(),
        "intelligence_types": list(INTELLIGENCE_TYPES),
    }
