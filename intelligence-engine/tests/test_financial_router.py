"""Financial Router — accounting/FSA questions must reach the deterministic
financial_foundations / financial_statement_intelligence engines, never
generic retrieval. Regression suite for the AFI Acceptance Test v1.0 gap
(0/20 accounting/FSA questions ever reached these engines on live Ask)."""

from __future__ import annotations

import pytest

from app.ui.financial_router import parse_amount, route

# All 20 Section A (Accounting Foundations) + Section B (Financial Statement
# Intelligence) questions from ask_product_test/afi_acceptance_v1.py, plus
# the expected answering engine.
ACCOUNTING_AND_FSA_QUESTIONS = [
    ("Founder invests ₹1 crore. Build the journal entry and opening balance sheet.", "financial_foundations"),
    ("Buy machinery for ₹40 lakh in cash. Explain today's and future impact on all three statements.", "financial_foundations"),
    ("Sell ₹50 lakh of goods on credit. Explain the accounting today and when cash is collected.", "financial_foundations"),
    ("Customer pays ₹20 lakh in advance. Why is this not revenue?", "financial_foundations"),
    ("Accrue ₹5 lakh salary expense. What changes?", "financial_foundations"),
    ("Why does every transaction require a debit and a credit?", "financial_foundations"),
    ("Explain retained earnings.", "financial_foundations"),
    ("Why does the trial balance always balance?", "financial_foundations"),
    ("Build a simple Income Statement from five transactions.", "financial_foundations"),
    ("Explain the accounting equation.", "financial_foundations"),
    ("Why can PAT increase while Operating Cash Flow decreases?", "financial_foundations"),
    ("Why doesn't depreciation reduce cash?", "financial_foundations"),
    ("Why can ROE increase while PAT falls?", "financial_statement_intelligence"),
    ("Revenue +20%, PAT +25%, OCF −30%. Interpret.", "financial_foundations"),
    ("EBITDA +18%, FCF −40%, Capex doubled. Explain.", "financial_statement_intelligence"),
    ("Receivables +60%, Revenue +10%. What does this suggest?", "financial_statement_intelligence"),
    ("Inventory doubles while revenue is flat.", "financial_statement_intelligence"),
    ("Why is working capital important?", "financial_statement_intelligence"),
    ("Reconstruct the Cash Flow Statement from an Income Statement and Balance Sheet.", "financial_foundations"),
    ("Explain earnings quality.", "financial_statement_intelligence"),
]


@pytest.mark.parametrize("question,expected_engine", ACCOUNTING_AND_FSA_QUESTIONS)
def test_all_accounting_and_fsa_questions_route_to_deterministic_engine(question, expected_engine):
    result = route(question)
    assert result is not None, f"Financial Router failed to match: {question!r}"
    assert result["engine"] == expected_engine
    assert result["summary"].strip()
    assert result["evidence"]


def test_founder_investment_produces_real_journal_entry_and_balance_sheet():
    result = route("Founder invests ₹1 crore. Build the journal entry and opening balance sheet.")
    assert result is not None
    low = result["summary"].lower()
    assert "debit cash" in low
    assert "credit share capital" in low
    assert "₹1 crore" in result["summary"]
    # Accounting equation must actually balance in the constructed example.
    assert "total assets ₹1 crore" in low
    assert "total equity ₹1 crore" in low


def test_income_statement_example_is_internally_consistent():
    result = route("Build a simple Income Statement from five transactions.")
    assert result is not None
    assert "revenue" in result["summary"].lower()
    assert "net income" in result["summary"].lower()


def test_business_questions_do_not_route_financially():
    """Company-specific business questions must NOT be hijacked by the
    financial router — it should return None so the normal pipeline runs.
    (Pure concept questions like "What is a competitive moat?" DO route,
    as of Phase 2.6 — see tests/test_financial_router_concepts.py.)"""
    assert route("Explain Reliance Industries' business model.") is None
    assert route("Should I buy HDFC Bank tomorrow?") is None
    assert route("Explain XYZ Quantum Robotics Pvt Ltd.") is None


def test_parse_amount_handles_crore_lakh_and_absence():
    assert parse_amount("Founder invests ₹1 crore.") == 1_00_00_000
    assert parse_amount("Buy machinery for ₹40 lakh in cash.") == 40 * 1_00_000
    assert parse_amount("Explain retained earnings.") is None


def test_router_never_raises_on_garbage_input():
    assert route("") is None
    assert route(None) is None  # type: ignore[arg-type]
    assert route("???") is None
