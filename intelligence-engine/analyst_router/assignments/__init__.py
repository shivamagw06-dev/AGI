"""Research Assignments — investigators with a defined mandate (IAR enhancement)."""

from __future__ import annotations

from typing import Any

from analyst_router.mandates import get_mandate

_ASSIGNMENTS: dict[str, dict[str, Any]] = {
    "Business": {
        "assignment": "Determine whether the business has a durable competitive advantage.",
        "questions_to_answer": [
            "What creates the moat?",
            "Is it strengthening or weakening?",
            "What evidence supports this?",
            "What evidence contradicts this?",
            "Confidence?",
        ],
        "success_criteria": "Produce one institutional judgement.",
        "maximum_length_words": 600,
    },
    "Financial": {
        "assignment": "Determine whether the financial statements support the investment thesis.",
        "questions_to_answer": [
            "Is earnings quality high?",
            "Is cash conversion sustainable?",
            "Is capital allocation value creating?",
            "What evidence weakens this conclusion?",
        ],
        "success_criteria": "Produce one institutional judgement on financial quality.",
        "maximum_length_words": 600,
    },
    "Valuation": {
        "assignment": "Determine whether current valuation already discounts expected business quality.",
        "questions_to_answer": [
            "What is priced in?",
            "Where is the margin of safety?",
            "Which assumptions matter most?",
        ],
        "success_criteria": "Produce one institutional valuation judgement.",
        "maximum_length_words": 600,
    },
    "Risk": {
        "assignment": "Identify risks that can permanently impair capital.",
        "questions_to_answer": [
            "What are the material downside paths?",
            "Which risks are underappreciated?",
            "What mitigants exist?",
        ],
        "success_criteria": "Produce a prioritised risk map with one institutional judgement.",
        "maximum_length_words": 500,
    },
    "Forecast": {
        "assignment": "Establish a disciplined base-case path for key drivers.",
        "questions_to_answer": [
            "What is the base case?",
            "What are the key sensitivities?",
            "What could break the forecast?",
        ],
        "success_criteria": "Produce a forecast with explicit assumptions.",
        "maximum_length_words": 500,
    },
    "Portfolio": {
        "assignment": "Determine portfolio fit, sizing, and risk-budget implications.",
        "questions_to_answer": [
            "Does this improve diversification?",
            "What size is appropriate?",
            "What concentration / factor risks arise?",
        ],
        "success_criteria": "Produce a portfolio recommendation consistent with mandate.",
        "maximum_length_words": 400,
    },
    "Macro": {
        "assignment": "Identify macro impulses that change the investment decision.",
        "questions_to_answer": [
            "Which macro variables matter?",
            "How do they transmit to the sector/company?",
            "What is the near-term path?",
        ],
        "success_criteria": "Produce one macro judgement with transmission channels.",
        "maximum_length_words": 500,
    },
    "Sector": {
        "assignment": "Assess sector attractiveness and relative positioning.",
        "questions_to_answer": [
            "Is the sector structurally attractive?",
            "Where does the subject sit versus peers?",
            "What cycle risks matter?",
        ],
        "success_criteria": "Produce one sector judgement.",
        "maximum_length_words": 500,
    },
    "Academy": {
        "assignment": "Teach the concept clearly with institutional precision.",
        "questions_to_answer": [
            "What is the definition?",
            "Why does it matter for investors?",
            "How is it calculated or applied?",
            "What are common pitfalls?",
        ],
        "success_criteria": "Produce an educational guide with one worked example.",
        "maximum_length_words": 800,
    },
    "Accounting": {
        "assignment": "Determine whether reported numbers are trustworthy.",
        "questions_to_answer": [
            "Are there forensic red flags?",
            "Is earnings quality acceptable?",
            "What would change the conclusion?",
        ],
        "success_criteria": "Produce one accounting quality judgement.",
        "maximum_length_words": 500,
    },
    "Management": {
        "assignment": "Assess management capability and alignment.",
        "questions_to_answer": [
            "Is leadership credible?",
            "Is capital allocation disciplined?",
            "What evidence contradicts a positive view?",
        ],
        "success_criteria": "Produce one management judgement.",
        "maximum_length_words": 400,
    },
    "Ownership": {
        "assignment": "Assess whether ownership structure supports minority investors.",
        "questions_to_answer": [
            "How is ownership concentrated?",
            "Are there pledge or governance risks?",
            "What changed recently?",
        ],
        "success_criteria": "Produce one ownership judgement.",
        "maximum_length_words": 350,
    },
    "Market": {
        "assignment": "Characterise the market regime relevant to the decision.",
        "questions_to_answer": [
            "What is the regime?",
            "Is liquidity supportive?",
            "What technical risks matter?",
        ],
        "success_criteria": "Produce one market-regime judgement.",
        "maximum_length_words": 350,
    },
    "News": {
        "assignment": "Isolate material news that changes the thesis.",
        "questions_to_answer": [
            "What is material?",
            "Is the market reaction proportional?",
            "Does it change the investment case?",
        ],
        "success_criteria": "Produce one news-impact judgement.",
        "maximum_length_words": 350,
    },
    "Committee": {
        "assignment": "Synthesise participating specialists into an institutional view.",
        "questions_to_answer": [
            "Where is there agreement?",
            "Where is there disagreement?",
            "What is the committee recommendation status?",
        ],
        "success_criteria": "Produce a committee minute with clear recommendation status.",
        "maximum_length_words": 700,
    },
    "CIO": {
        "assignment": "Frame the final institutional decision and reversal conditions.",
        "questions_to_answer": [
            "What decision do we take?",
            "Under what conditions would we reverse?",
            "What must be monitored?",
        ],
        "success_criteria": "Produce a CIO decision note.",
        "maximum_length_words": 400,
    },
}


def build_assignments(
    participants: list[str],
    *,
    primary_objective: str | None = None,
    question: str | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for analyst in participants:
        base = dict(_ASSIGNMENTS.get(analyst) or {})
        mandate = get_mandate(analyst) or {}
        if not base:
            base = {
                "assignment": mandate.get("primary_questions", ["Complete your mandated analysis."])[0]
                if mandate.get("primary_questions")
                else "Complete your mandated analysis.",
                "questions_to_answer": list(mandate.get("secondary_questions") or []),
                "success_criteria": "Produce one institutional judgement inside mandate.",
                "maximum_length_words": 500,
            }
        out.append(
            {
                "analyst": analyst,
                "role": mandate.get("role") or analyst,
                "assignment": base.get("assignment"),
                "questions_to_answer": list(base.get("questions_to_answer") or []),
                "success_criteria": base.get("success_criteria"),
                "maximum_length_words": base.get("maximum_length_words"),
                "allowed": list(mandate.get("allowed") or []),
                "never": list(mandate.get("never") or []),
                "output_contract": list(mandate.get("output_contract") or []),
                "primary_objective": primary_objective,
                "question_context": question,
            }
        )
    return out
