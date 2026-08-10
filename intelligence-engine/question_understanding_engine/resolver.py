"""Deterministic question understanding — 10-step QUE pipeline."""

from __future__ import annotations

import re
from typing import Any

from question_understanding_engine.schema import (
    DECISION_TYPES,
    INFORMATION_CATEGORIES,
    RESEARCH_OBJECTIVES,
    RESPONSE_OBJECTIVES,
    RESPONSE_STRUCTURE_BY_DECISION,
)

# Pattern rules: (regex, decision_type, investor_meaning_template, response_objective, confidence_boost)
_RULES: tuple[tuple[re.Pattern[str], str, str, str, int], ...] = (
    (re.compile(r"\bshould\s+i\s+(buy|invest|allocate|own)\b", re.I), "Capital Allocation",
     "Should I allocate capital here instead of another opportunity?", "Evaluate", 25),
    (re.compile(r"\bdeserve\s+research\b|\binitiate\s+coverage\b|\bworth\s+research\b", re.I), "Research Priority",
     "Should analyst resources be allocated to this company?", "Prioritize", 25),
    (re.compile(
        r"\b(?:agi(?:['’]s)?|your|our|house)\s+(?:current\s+)?view\b|"
        r"\bview\s+on\b|\binvestment\s+(?:view|thesis|case)\b|"
        r"\b(?:bull|bear|base)\s+case\b|\bwhat\s+(?:would|could)\s+change\s+.*\bview\b",
        re.I,
     ), "Thesis Validation",
     "Does the current evidence strengthen or weaken the investment thesis?", "Challenge", 25),
    (re.compile(
        r"\b(?:order wins?|contracts?|tenders?|acquisitions?|guidance)\b.*"
        r"\b(?:impact|material|thesis|view|outlook|case)\b|"
        r"\b(?:impact|material|thesis|view|outlook|case)\b.*"
        r"\b(?:order wins?|contracts?|tenders?|acquisitions?|guidance)\b",
        re.I,
     ), "Thesis Validation",
     "Does this corporate event materially change the investment thesis?", "Evaluate", 23),
    (re.compile(r"\bcompare\b|\bvs\.?\b|\bversus\b|\bwhich\s+one\b", re.I), "Peer Selection",
     "If I only invest in one company, which differences matter?", "Compare", 22),
    (re.compile(r"\bexpensive\b|\bcheap\b|\bvaluation\b|\bpremium\b|\bmultiple\b|\bfairly\s+valued\b", re.I),
     "Valuation Assessment", "What expectations are embedded in today's valuation and are they justified?", "Explain", 22),
    (re.compile(r"\bportfolio\b|\ballocation\b|\boverlap\b|\bdiversif", re.I), "Portfolio Construction",
     "What role should this company play in the portfolio?", "Evaluate", 20),
    (re.compile(r"\brisk\b|\bdownside\b|\bthreat\b|\binvalidate\b", re.I), "Risk Assessment",
     "What could permanently damage the investment thesis?", "Evaluate", 20),
    (re.compile(r"\bmonitor\b|\bwatch\b|\bKPI\b|\btrigger\b|\bearly\s+warning\b", re.I), "Monitoring",
     "What events should trigger thesis review?", "Monitor", 20),
    (re.compile(r"\bthesis\b|\bchanged\b|\bstill\s+hold\b|\bconviction\b", re.I), "Thesis Validation",
     "Did the investment thesis change?", "Challenge", 18),
    (re.compile(r"\bearnings\b|\bquarter\b|\bresults\b|\bwhat\s+changed\b", re.I), "Earnings Review",
     "Did recent results strengthen or weaken the thesis?", "Evaluate", 18),
    (re.compile(r"\binterest\s+rate\b|\bmacro\b|\bUSD\b|\bINR\b|\brecession\b|\bRBI\b", re.I), "Macro Impact",
     "How do macro variables affect the investment case?", "Explain", 18),
    (re.compile(r"\bsector\b|\bindustry\b|\bstructural\s+trend\b", re.I), "Sector Allocation",
     "Is the sector attractive and how does the company benefit?", "Evaluate", 16),
    (re.compile(r"\bwhich\s+companies\b|\binteresting\b|\bidea\s+generation\b|\bscreen\b", re.I), "Idea Generation",
     "Which companies deserve research attention?", "Prioritize", 16),
    (re.compile(r"\bshow\s+evidence\b|\bwhy\s+do\s+you\s+believe\b|\bhow\s+confident\b|\bcontradict", re.I),
     "Explainability", "What evidence supports or contradicts the conclusion?", "Explain", 16),
    (re.compile(r"\bexplain\b|\bwhat\s+is\b|\bplain\s+english\b|\bnew\s+investor\b", re.I), "Education",
     "Help me understand this concept or business clearly.", "Teach", 14),
    (re.compile(r"\bhow\s+does\b.*\bmake\s+money\b|\bbusiness\s+model\b|\bmoat\b|\bpricing\s+power\b", re.I),
     "Business Understanding", "How does this business work and create value?", "Explain", 18),
    (re.compile(r"\bstock\s+fell\b|\bwhy\s+did\b.*\bfall\b|\bdrop\b|\bcrash\b", re.I), "Thesis Validation",
     "Did the investment thesis change?", "Evaluate", 18),
    (re.compile(r"\bmanagement\b|\bcapital\s+allocation\b|\bguidance\b", re.I), "Business Understanding",
     "Can management be trusted to create shareholder value?", "Evaluate", 14),
    (re.compile(r"\bcash\s+flow\b|\bmargin\b|\bbalance\s+sheet\b|\bfinancials\b", re.I), "Business Understanding",
     "How strong and durable are the financials?", "Explain", 14),
)


def _match_rule(query: str) -> tuple[str, str, str, int]:
    for pattern, decision, meaning, objective, boost in _RULES:
        if pattern.search(query):
            return decision, meaning, objective, boost
    return "Business Understanding", "What should an institutional investor understand before deciding?", "Research", 5


def _primary_investment_question(literal: str, decision: str, *, ticker: str | None = None) -> str:
    company = ticker or "this company"
    templates = {
        "Capital Allocation": f"What evidence supports allocating capital to {company} today rather than another opportunity?",
        "Research Priority": f"Are there unresolved questions about {company} that could materially affect the investment thesis?",
        "Valuation Assessment": f"What expectations justify {company}'s current valuation?",
        "Peer Selection": f"If investing in only one name, which investment-relevant differences matter most?",
        "Portfolio Construction": f"What role should {company} play given existing portfolio exposures?",
        "Risk Assessment": f"What risks could permanently impair the investment thesis on {company}?",
        "Monitoring": f"What should investors monitor to know when to revisit the thesis on {company}?",
        "Thesis Validation": f"Does today's evidence still support the investment thesis on {company}?",
        "Earnings Review": f"What changed after the latest results and did it strengthen or weaken the thesis on {company}?",
        "Macro Impact": f"Which macro variables most affect {company}'s investment case?",
        "Sector Allocation": f"How attractive is the sector and how well is {company} positioned?",
        "Idea Generation": f"Does {company} deserve research attention today?",
        "Education": f"What must an investor understand to evaluate {company} intelligently?",
        "Explainability": f"What evidence supports and contradicts the current view on {company}?",
        "Business Understanding": f"How does {company} create value and what drives durability?",
        "Unknown": f"What investment decision is the investor trying to make about {company}?",
    }
    if decision in templates:
        return templates[decision]
    return f"What investment decision does this question about {company} require?"


def _required_information(decision: str) -> list[str]:
    base: dict[str, list[str]] = {
        "Capital Allocation": ["Business Quality", "Valuation", "Risks", "Evidence", "Portfolio Fit"],
        "Research Priority": ["Business Quality", "Evidence", "Industry"],
        "Valuation Assessment": ["Valuation", "Growth", "Competitive Position", "Evidence"],
        "Peer Selection": ["Business Quality", "Financial Quality", "Competitive Position", "Valuation"],
        "Portfolio Construction": ["Portfolio Fit", "Risks", "Macro", "Valuation"],
        "Risk Assessment": ["Risks", "Business Quality", "Macro", "Evidence"],
        "Monitoring": ["Evidence", "Risks", "Financial Quality"],
        "Thesis Validation": ["Evidence", "Business Quality", "Valuation", "Risks"],
        "Earnings Review": ["Financial Quality", "Evidence", "Growth"],
        "Macro Impact": ["Macro", "Industry", "Financial Quality"],
        "Sector Allocation": ["Industry", "Competitive Position", "Macro"],
        "Idea Generation": ["Industry", "Business Quality", "Evidence"],
        "Education": ["Business Quality"],
        "Explainability": ["Evidence", "Business Quality"],
        "Business Understanding": ["Business Quality", "Competitive Position", "Management", "Growth"],
    }
    return base.get(decision, ["Business Quality", "Evidence"])


def _irrelevant_information(decision: str) -> list[str]:
    ignore: dict[str, list[str]] = {
        "Valuation Assessment": ["Dividend history", "Employee count", "Corporate timeline"],
        "Research Priority": ["Short-term price targets", "Technical chart patterns"],
        "Peer Selection": ["Unrelated macro history", "Generic industry trivia"],
        "Monitoring": ["Historical IPO details", "Founder biography"],
        "Education": ["Trading mechanics", "Broker recommendations"],
        "Macro Impact": ["Product launch trivia", "Minor corporate events"],
    }
    return ignore.get(decision, ["Irrelevant historical trivia", "Non-investment operational detail"])


def _expected_deliverable(decision: str) -> str:
    mapping = {
        "Capital Allocation": "Investment assessment clarity",
        "Research Priority": "Research prioritization rationale",
        "Valuation Assessment": "Expectations embedded in price",
        "Peer Selection": "Investment-relevant peer differences",
        "Portfolio Construction": "Portfolio role clarity",
        "Risk Assessment": "Risk prioritization",
        "Monitoring": "Monitoring checklist",
        "Thesis Validation": "Thesis validation summary",
        "Earnings Review": "Thesis validation summary",
        "Macro Impact": "Business model understanding",
        "Sector Allocation": "Business model understanding",
        "Idea Generation": "Research prioritization rationale",
        "Education": "Educational explanation",
        "Explainability": "Thesis validation summary",
        "Business Understanding": "Business model understanding",
    }
    return mapping.get(decision, "Investment assessment clarity")


def _response_objective(decision: str, matched_objective: str) -> str:
    if matched_objective in RESPONSE_OBJECTIVES:
        return matched_objective
    defaults = {
        "Capital Allocation": "Evaluate",
        "Research Priority": "Prioritize",
        "Peer Selection": "Compare",
        "Valuation Assessment": "Explain",
        "Monitoring": "Monitor",
    }
    return defaults.get(decision, "Research")


def understand_question(
    query: str,
    *,
    ticker: str | None = None,
    company: str | None = None,
    benchmark_id: str | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    """Run 10-step QUE pipeline — deterministic, not LLM."""
    literal = str(query or "").strip()
    if not literal:
        return _empty_understanding()

    decision, investor_meaning, matched_obj, boost = _match_rule(literal)

    # IIC domain override when benchmark provides curriculum context
    if domain:
        from question_understanding_engine.schema import DOMAIN_DECISION_MAP

        decision = DOMAIN_DECISION_MAP.get(domain, decision)

    confidence = min(100, 55 + boost)
    if ticker or company:
        confidence = min(100, confidence + 10)

    research_objective = RESEARCH_OBJECTIVES.get(decision, RESEARCH_OBJECTIVES["Unknown"])
    primary = _primary_investment_question(literal, decision, ticker=ticker or company)
    required = _required_information(decision)
    irrelevant = _irrelevant_information(decision)
    response_objective = _response_objective(decision, matched_obj)
    expected_deliverable = _expected_deliverable(decision)

    return {
        "literal_question": literal,
        "investor_meaning": investor_meaning,
        "decision_type": decision,
        "research_objective": research_objective,
        "primary_investment_question": primary,
        "required_information": required,
        "irrelevant_information": irrelevant,
        "response_objective": response_objective,
        "expected_deliverable": expected_deliverable,
        "expected_response_structure": RESPONSE_STRUCTURE_BY_DECISION.get(
            decision, RESPONSE_STRUCTURE_BY_DECISION["Unknown"]
        ),
        "confidence": confidence,
        "success_test": "What decision is the investor trying to make?",
        "decision_answered": bool(decision and decision != "Unknown"),
        "answer_layer_2_not_layer_1": True,
        "ticker": ticker,
        "company": company,
        "benchmark_id": benchmark_id,
        "domain": domain,
    }


def _empty_understanding() -> dict[str, Any]:
    return {
        "literal_question": "",
        "investor_meaning": "",
        "decision_type": "Unknown",
        "research_objective": RESEARCH_OBJECTIVES["Unknown"],
        "primary_investment_question": "",
        "required_information": [],
        "irrelevant_information": [],
        "response_objective": "Research",
        "expected_deliverable": "",
        "expected_response_structure": RESPONSE_STRUCTURE_BY_DECISION["Unknown"],
        "confidence": 0,
        "success_test": "What decision is the investor trying to make?",
        "decision_answered": False,
        "answer_layer_2_not_layer_1": False,
    }
