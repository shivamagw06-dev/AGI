"""Module 12 — Unsupported Coverage Policy.

AFI Acceptance Test v1.0 found 3 hallucinations (Visa, Costco, Ferrari/
Toyota — see PR #448): real, well-known companies outside this platform's
verified coverage universe got irrelevant generic evidence instead of an
honest refusal. This is the regression suite for the fix.
"""

from __future__ import annotations

import pytest

from app.ui.coverage_policy import (
    detect_unsupported_company,
    unsupported_coverage_executive,
    unsupported_coverage_why,
)

UNSUPPORTED_QUESTIONS = [
    ("Why does Visa generate high free cash flow?", "Visa"),
    ("Why does Costco operate with low margins?", "Costco"),
    ("Why is Ferrari more profitable than Toyota?", "Ferrari"),
    ("What is Netflix's subscriber growth strategy?", "Netflix"),
    ("Explain Tesla's manufacturing model.", "Tesla"),
    ("How does Walmart maintain low prices?", "Walmart"),
    ("Explain Mastercard's business model.", "Mastercard"),
    ("What is PayPal's competitive position?", "PayPal"),
    ("Why is Boeing facing production issues?", "Boeing"),
    ("Explain JPMorgan's balance sheet.", "JPMorgan"),
    ("What is Berkshire Hathaway's capital allocation philosophy?", "Berkshire Hathaway"),
]


@pytest.mark.parametrize("question,expected_company", UNSUPPORTED_QUESTIONS)
def test_detects_unsupported_company(question, expected_company):
    detected = detect_unsupported_company(question)
    assert detected == expected_company


def test_ferrari_toyota_comparison_detects_first_match():
    # Both are unsupported; the policy should still fire (detecting either
    # is sufficient to trigger the honest refusal rather than fabrication).
    detected = detect_unsupported_company("Why is Ferrari more profitable than Toyota?")
    assert detected in ("Ferrari", "Toyota")


ALREADY_SUPPORTED_QUESTIONS = [
    "What did Meta say about AI infrastructure spending?",
    "Summarize Apple's latest quarterly earnings.",
    "Explain Microsoft's cloud business.",
    "How is Amazon's logistics network structured?",
    "What is Reliance Industries' business model?",
    "Explain Tata Motors.",
    "What is HDFC Bank's asset quality?",
]


@pytest.mark.parametrize("question", ALREADY_SUPPORTED_QUESTIONS)
def test_does_not_flag_already_aliased_companies(question):
    """Companies already handled via executive_composer's alias path must
    not be intercepted by this new, narrower policy — avoids regressing a
    working path (see founder_evaluation_v1.py FE-01/FE-04/FE-05)."""

    assert detect_unsupported_company(question) is None


FICTITIOUS_QUESTIONS = [
    "Explain XYZ Quantum Robotics Pvt Ltd.",
    "What is the business model of Acme Widgets Inc?",
    "Explain a company listed yesterday.",
]


@pytest.mark.parametrize("question", FICTITIOUS_QUESTIONS)
def test_does_not_flag_fictitious_companies(question):
    """Genuinely unknown/fictitious names are NOT this policy's concern —
    they continue through the existing unknown-entity hard stop, which
    already passes at 100% (see ask_product_test/founder_evaluation_v1.py
    FE-13/FE-14 and the AFI Acceptance Test's E39)."""

    assert detect_unsupported_company(question) is None


CONCEPT_ONLY_QUESTIONS = [
    "What is Free Cash Flow?",
    "Explain Enterprise Value.",
    "What is the DuPont Model?",
    "Why is working capital important?",
]


@pytest.mark.parametrize("question", CONCEPT_ONLY_QUESTIONS)
def test_does_not_flag_pure_concept_questions(question):
    assert detect_unsupported_company(question) is None


def test_refusal_text_matches_brief_wording():
    text = unsupported_coverage_executive("Visa")
    assert "do not currently have verified company coverage for Visa" in text
    assert "will not invent company-specific analysis" in text


def test_refusal_why_never_names_a_substitute_company():
    why = unsupported_coverage_why("Costco")
    assert any("Costco" in w for w in why)
    assert all("Reliance" not in w or "covered" in w.lower() for w in why)


def _build_ui_service():
    from app.aws.service import AwsService
    from app.cre.service import CREService
    from app.ioc.service import IocService
    from app.kip.service import KipService
    from app.rms.service import RmsService
    from app.rsp.service import RspService
    from app.ui.service import UiService
    from app.validation.service import ValidationService

    kip = KipService()
    rsp = RspService(kip=kip)
    rms = RmsService(kip=kip, rsp=rsp)
    cre = CREService()
    validation = ValidationService()
    aws = AwsService(kip=kip, rsp=rsp, rms=rms, cre=cre, validation=validation)
    ioc = IocService(kip=kip, rsp=rsp, rms=rms, aws=aws, cre=cre, validation=validation)
    return UiService(aws=aws, ioc=ioc, kip=kip, rsp=rsp, rms=rms, cre=cre, validation=validation)


def test_coverage_policy_wins_over_generic_concept_fallback_end_to_end():
    """Regression test for the exact ordering bug found during Phase 2.6
    development: 'Why does Visa generate high free cash flow?' also
    matches the generic 'free_cash_flow' concept card, so the Financial
    Router alone would answer with a company-blind concept explanation
    instead of the honest coverage refusal. app/ui/service.py must check
    the coverage policy BEFORE the financial router."""

    ui = _build_ui_service()
    view = ui.search("Why does Visa generate high free cash flow?")
    payload = view.model_dump(mode="json") if hasattr(view, "model_dump") else dict(view)
    orch = payload.get("ask_orchestration") or {}
    summary = (payload.get("answer") or {}).get("summary") or ""
    assert orch.get("short_circuit") == "unsupported_coverage_policy"
    assert "do not currently have verified company coverage for Visa" in summary


def test_pure_concept_question_still_routes_through_financial_router_end_to_end():
    ui = _build_ui_service()
    view = ui.search("What is Free Cash Flow?")
    payload = view.model_dump(mode="json") if hasattr(view, "model_dump") else dict(view)
    orch = payload.get("ask_orchestration") or {}
    # Phase 9.2 / KUL: pure concepts short-circuit via Knowledge Unification
    # (financial_concepts / foundations / FSI) rather than the legacy
    # financial_router label — same engines, unified planner path.
    sc = orch.get("short_circuit")
    assert sc in {"financial_router", "knowledge_unification"}
    sources = list((payload.get("meta") or {}).get("sources") or [])
    engine = orch.get("financial_engine")
    assert engine in {
        "financial_concepts",
        "financial_foundations",
        "financial_statement_intelligence",
        None,
    } or any(
        s in sources
        for s in (
            "financial_concepts",
            "financial_foundations",
            "financial_statement_intelligence",
            "knowledge_unification",
        )
    )
    summary = ((payload.get("answer") or {}).get("summary") or "").lower()
    assert "cash" in summary or "fcf" in summary
