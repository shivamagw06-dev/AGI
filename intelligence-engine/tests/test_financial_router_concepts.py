"""Module 11 — Financial Router extension for Phase 2.6 concept questions.

Regression suite for the specific AFI Acceptance Test v1.0 Section C
(Valuation & Ratios) and Section D (Business Intelligence) concept
questions that scored below the routing bar pre-Phase-2.6 (see PR #448).
"""

from __future__ import annotations

import pytest

from app.ui.financial_router import route

CONCEPT_ROUTED_QUESTIONS = [
    # Section C — Valuation & Ratios
    "Why do banks trade on Price-to-Book instead of EV/EBITDA?",
    "When should EV/EBITDA be preferred over P/E?",
    "Why is ROIC important?",
    "Explain Free Cash Flow Yield.",
    "Why is Enterprise Value used instead of Market Capitalization?",
    "Why can ROCE increase while ROE falls?",
    "Explain the DuPont model.",
    "Why can Gross Margin fall while EBITDA Margin rises?",
    # Section D — Business Intelligence (concept-only, not company-specific)
    "Explain operating leverage using airlines.",
    "What creates pricing power?",
    "Explain network effects.",
    "What is a competitive moat?",
    # Phase 2.6 brief's own mission questions
    "What is the DuPont Model?",
    "What is Economic Profit?",
    "What is EVA?",
    "What is Residual Income?",
    "What is NOPAT?",
]


@pytest.mark.parametrize("question", CONCEPT_ROUTED_QUESTIONS)
def test_concept_question_routes_to_a_deterministic_engine(question):
    result = route(question)
    assert result is not None, f"Router failed to match: {question!r}"
    assert result["engine"] in ("financial_concepts", "financial_foundations", "financial_statement_intelligence")
    assert result["summary"].strip()
    assert result["evidence"]


def test_enterprise_value_question_specifically_routes_to_financial_concepts():
    # A comparison question genuinely touches both concepts; either is a
    # correct, non-hallucinated answer (the longest-literal-match lookup
    # picks whichever phrase is more specific in the exact wording used).
    result = route("Why is Enterprise Value used instead of Market Capitalization?")
    assert result["engine"] == "financial_concepts"
    assert result["key"] in ("enterprise_value", "market_capitalization", "ev_vs_market_cap")


def test_dupont_question_specifically_routes_to_financial_concepts():
    result = route("Explain the DuPont model.")
    assert result["engine"] == "financial_concepts"
    assert result["key"] == "dupont_model"


def test_moat_question_specifically_routes_to_financial_concepts():
    result = route("What is a competitive moat?")
    assert result["engine"] == "financial_concepts"
    assert result["key"] == "economic_moat"


def test_company_specific_questions_still_do_not_route_financially():
    """The concept fallback must never hijack genuinely company-specific
    questions — those still need entity resolution / retrieval / the
    coverage policy, not a generic concept explanation."""

    assert route("Explain Reliance Industries' business model.") is None
    assert route("Should I buy HDFC Bank tomorrow?") is None
    assert route("Explain XYZ Quantum Robotics Pvt Ltd.") is None


def test_accounting_foundations_questions_still_route_via_financial_foundations():
    """Regression guard: the Phase 2.6 addition must not change existing
    Phase 2.5 (PR #447) Financial Foundations routing."""

    result = route("Founder invests ₹1 crore. Build the journal entry and opening balance sheet.")
    assert result is not None
    assert result["engine"] == "financial_foundations"
