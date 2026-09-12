"""QUE v1.1 — Research Brief Generator (steps 6–10)."""

from __future__ import annotations

from typing import Any

from question_understanding_engine.resolver import understand_question
from question_understanding_engine.schema import RESEARCH_OBJECTIVES

# Information need resolver: required, optional, ignore per decision
_INFORMATION_NEEDS: dict[str, dict[str, list[str]]] = {
    "Capital Allocation": {
        "required": ["Business Quality", "Valuation", "Risks", "Evidence"],
        "optional": ["Management", "Growth", "Portfolio Fit"],
        "ignore": ["Dividend history", "Employee count", "Historical timeline"],
    },
    "Research Priority": {
        "required": ["Business Quality", "Competitive Position", "Industry", "Evidence"],
        "optional": ["Valuation", "Management"],
        "ignore": ["Price targets", "Technical analysis", "Historical dividend record"],
    },
    "Valuation Assessment": {
        "required": ["Valuation", "Growth", "Competitive Position", "Evidence"],
        "optional": ["Management", "Industry"],
        "ignore": ["Dividend history", "Employee count", "Corporate timeline from 10+ years ago"],
    },
    "Peer Selection": {
        "required": ["Business Quality", "Financial Quality", "Competitive Position", "Valuation"],
        "optional": ["Growth", "Management"],
        "ignore": ["Unrelated macro history", "Generic industry trivia"],
    },
    "Portfolio Construction": {
        "required": ["Portfolio Fit", "Risks", "Valuation", "Evidence"],
        "optional": ["Macro", "Business Quality"],
        "ignore": ["Historical IPO details", "Founder biography"],
    },
    "Risk Assessment": {
        "required": ["Risks", "Business Quality", "Evidence"],
        "optional": ["Macro", "Financial Quality"],
        "ignore": ["Short-term price noise", "Technical chart patterns"],
    },
    "Monitoring": {
        "required": ["Evidence", "Risks", "Financial Quality"],
        "optional": ["Industry", "Macro"],
        "ignore": ["Historical IPO details", "Corporate events from 10+ years ago"],
    },
    "Thesis Validation": {
        "required": ["Evidence", "Business Quality", "Valuation", "Risks"],
        "optional": ["Growth", "Management"],
        "ignore": ["Irrelevant historical trivia"],
    },
    "Decision Review": {
        "required": ["Evidence", "Business Quality", "Valuation"],
        "optional": ["Management", "Risks"],
        "ignore": ["Short-term price targets", "Technical analysis"],
    },
    "Business Understanding": {
        "required": ["Business Quality", "Competitive Position", "Management"],
        "optional": ["Growth", "Financial Quality"],
        "ignore": ["Trading mechanics", "Broker recommendations"],
    },
}

_KNOWLEDGE_GAPS: dict[str, str] = {
    "Capital Allocation": "The investor understands the company but may not know whether future returns justify today's valuation.",
    "Research Priority": "The investor may not know whether additional work could materially change today's investment conclusion.",
    "Valuation Assessment": "The investor understands price but may not understand embedded expectations.",
    "Peer Selection": "The investor may see similarities but not which differences actually drive investment outcomes.",
    "Portfolio Construction": "The investor may not understand overlap, correlation, or opportunity cost.",
    "Risk Assessment": "The investor may know headline risks but not which could permanently impair the thesis.",
    "Monitoring": "The investor may not know which signals should trigger a thesis review.",
    "Thesis Validation": "The investor may not know whether recent events changed the investment case.",
    "Decision Review": "The investor may not have calibrated prior assumptions against new evidence.",
    "Business Understanding": "The investor may know the brand but not how value is created and sustained.",
    "Earnings Review": "The investor may know headline numbers but not what changed for the thesis.",
    "Macro Impact": "The investor may not understand transmission from macro variables to earnings.",
    "Sector Allocation": "The investor may not understand sector dynamics relative to company positioning.",
    "Idea Generation": "The investor may not know why this company deserves attention versus alternatives.",
    "Education": "The investor lacks foundational understanding needed to evaluate the opportunity.",
    "Explainability": "The investor may not see the evidence chain behind the conclusion.",
}

_TOP_QUESTIONS: dict[str, tuple[str, str, str]] = {
    "Capital Allocation": (
        "Can earnings continue growing?",
        "Is valuation already pricing that growth?",
        "What could invalidate the thesis?",
    ),
    "Research Priority": (
        "What uncertainty remains unresolved?",
        "Could future research change valuation assumptions?",
        "Why should analyst time be allocated here instead of another company?",
    ),
    "Valuation Assessment": (
        "What growth is implied by today's price?",
        "Are expectations supported by fundamentals?",
        "What could compress or expand multiples?",
    ),
    "Peer Selection": (
        "Which business model differences matter most?",
        "Which financial differences change the investment case?",
        "If choosing one name, which has better risk-adjusted prospects?",
    ),
    "Portfolio Construction": (
        "What role would this name play in the portfolio?",
        "Which existing holdings overlap?",
        "What is the opportunity cost?",
    ),
    "Risk Assessment": (
        "What are the three biggest risks?",
        "Which risk is most underestimated?",
        "What would permanently damage the thesis?",
    ),
    "Monitoring": (
        "Which KPIs matter most?",
        "What events would strengthen the thesis?",
        "What events would weaken the thesis?",
    ),
    "Thesis Validation": (
        "Did the thesis change?",
        "Which assumptions proved wrong?",
        "Would today's evidence change the conclusion?",
    ),
    "Decision Review": (
        "What changed since research began?",
        "Which assumptions were correct vs wrong?",
        "What institutional lesson should be retained?",
    ),
    "Business Understanding": (
        "How does the company make money?",
        "Why do customers stay?",
        "What makes the advantage durable?",
    ),
}

_RESPONSE_PROMISES: dict[str, str] = {
    "Capital Allocation": (
        "After reading this response the investor should understand why this deserves capital, "
        "what evidence matters, what uncertainty remains, what should be monitored, "
        "and what could change today's conclusion."
    ),
    "Research Priority": (
        "By the end of this answer the investor will understand whether this company deserves "
        "analyst attention today, why research matters, what remains unknown, "
        "what evidence is missing, and whether further work could change today's investment conclusion."
    ),
    "Valuation Assessment": (
        "The investor will understand what expectations are embedded in price, "
        "whether they appear justified, and what could change the valuation view."
    ),
    "Peer Selection": (
        "The investor will understand which differences between peers actually matter for capital allocation."
    ),
}

_SUCCESS_CRITERIA: dict[str, list[str]] = {
    "Research Priority": [
        "The reader understands why research matters",
        "What remains unknown",
        "What evidence is missing",
        "Whether further work could change today's investment conclusion",
    ],
    "Capital Allocation": [
        "The reader understands whether expected reward justifies risk",
        "What evidence supports or challenges allocation",
        "What uncertainty remains",
        "What would change the conclusion",
    ],
    "Valuation Assessment": [
        "The reader understands embedded expectations",
        "Whether expectations appear justified",
        "What could change the valuation view",
    ],
}


def _primary_question_v11(decision: str, company: str) -> str | None:
    """v1.1 committee-ready phrasing overrides."""
    overrides = {
        "Research Priority": f"Could additional research materially change today's investment conclusion on {company}?",
        "Capital Allocation": f"What evidence supports allocating capital to {company} rather than another opportunity?",
    }
    return overrides.get(decision)


def generate_research_brief(understanding: dict[str, Any]) -> dict[str, Any]:
    """Extend question understanding into full research brief (QUE v1.1)."""
    decision = understanding.get("decision_type") or "Unknown"
    company = understanding.get("company") or understanding.get("ticker") or "this company"
    needs = _INFORMATION_NEEDS.get(decision, {
        "required": understanding.get("required_information") or ["Business Quality", "Evidence"],
        "optional": ["Management", "Industry"],
        "ignore": understanding.get("irrelevant_information") or [],
    })

    primary = understanding.get("primary_investment_question") or ""
    override = _primary_question_v11(decision, str(company))
    if override:
        primary = override

    top_q = _TOP_QUESTIONS.get(decision, (
        "What matters most for this decision?",
        "What evidence is decisive?",
        "What uncertainty remains?",
    ))

    research_objective = understanding.get("research_objective") or RESEARCH_OBJECTIVES.get(decision, "")
    if decision == "Capital Allocation":
        research_objective = "Determine whether expected reward justifies risk versus alternatives."
    elif decision == "Research Priority":
        research_objective = "Determine whether additional analysis could materially improve the investment thesis."

    promise = _RESPONSE_PROMISES.get(decision, (
        f"After reading this response the investor should understand what matters for the "
        f"{decision.lower()} decision and what uncertainty remains."
    ))
    success = _SUCCESS_CRITERIA.get(decision, [
        "The reader understands the underlying investment decision",
        "Required evidence is addressed",
        "Uncertainty is explicit",
        "The response answers the primary investment question",
    ])

    brief = {
        **understanding,
        "research_objective": research_objective,
        "primary_investment_question": primary,
        "required_information": list(needs["required"]),
        "optional_information": list(needs["optional"]),
        "irrelevant_information": list(needs["ignore"]),
        "knowledge_gap": _KNOWLEDGE_GAPS.get(decision, "The investor may not yet understand what drives this decision."),
        "top_research_questions": list(top_q),
        "response_promise": promise,
        "success_criteria": success,
        "brief_version": "1.1",
    }
    return brief


def build_research_brief(
    query: str,
    *,
    ticker: str | None = None,
    company: str | None = None,
    benchmark_id: str | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    """Full QUE v1.1 pipeline: understanding + research brief."""
    understanding = understand_question(
        query,
        ticker=ticker,
        company=company,
        benchmark_id=benchmark_id,
        domain=domain,
    )
    return generate_research_brief(understanding)


def downstream_contract(brief: dict[str, Any]) -> dict[str, Any]:
    """Operating contract for downstream engines — consume without reading original question."""
    return {
        "research_workflow": {
            "required_information": brief.get("required_information"),
            "optional_information": brief.get("optional_information"),
            "ignore": brief.get("irrelevant_information"),
            "top_research_questions": brief.get("top_research_questions"),
            "research_objective": brief.get("research_objective"),
        },
        "knowledge_retrieval": {
            "prioritize_categories": brief.get("required_information"),
            "deprioritize": brief.get("irrelevant_information"),
        },
        "evidence_graph": {
            "focus_questions": brief.get("top_research_questions"),
        },
        "response_planner": {
            "primary_investment_question": brief.get("primary_investment_question"),
            "response_promise": brief.get("response_promise"),
            "expected_deliverable": brief.get("expected_deliverable"),
            "success_criteria": brief.get("success_criteria"),
        },
        "editorial_review": {
            "success_criteria": brief.get("success_criteria"),
            "response_promise": brief.get("response_promise"),
        },
    }
