"""Tier A — AGI Ask Product Smoke (founder acceptance).

Run:
  cd intelligence-engine && pytest tests/test_ask_product_smoke.py -q

Live gateway (optional):
  ASK_TEST_MODE=live ASK_TEST_BASE=https://finance-news-backend-19i5.onrender.com \\
    pytest tests/test_ask_product_smoke.py -q
"""

from __future__ import annotations

import os

import pytest

from ask_product_test.checks import (
    check_no_jargon,
    check_no_recommendation,
    has_usable_answer,
)
from ask_product_test.harness import AskProductHarness, write_report
from ask_product_test.prompts import SMOKE_PROMPTS


@pytest.fixture(scope="module")
def harness() -> AskProductHarness:
    return AskProductHarness(latency_budget_ms=int(os.environ.get("ASK_TEST_LATENCY_MS", "90000")))


def test_product_contract_helpers_unit():
    """Fast contract helpers — no engine call."""
    ok_payload = {
        "status": "ok",
        "executive_summary": "Reliance operates a diversified conglomerate across refining, retail, and digital.",
        "why": ["Segment mix supports cash generation."],
        "evidence_used": [{"source": "KF", "title": "Reliance profile"}],
        "entities": {"ticker": "RELIANCE", "companies": ["RELIANCE"]},
        "intent": "company_overview",
        "answer": {"summary": "Diversified platform business."},
    }
    assert has_usable_answer(ok_payload)
    assert check_no_jargon(ok_payload)[0]
    assert check_no_recommendation(ok_payload)[0]

    bad = {
        "executive_summary": "We recommend buying HDFC Bank. Target price 2000. Signal from E03 and FAA.",
        "answer": {},
    }
    assert check_no_recommendation(bad)[0] is False
    assert check_no_jargon(bad)[0] is False

    refusal = {
        "executive_summary": "AGIB does not issue buy or sell recommendations.",
        "answer": {"summary": "No buy/sell rating — monitoring framing only."},
    }
    assert check_no_recommendation(refusal)[0] is True


def test_tier_a_product_smoke(harness: AskProductHarness):
    prompts = list(SMOKE_PROMPTS)
    raw_limit = os.environ.get("ASK_TEST_SMOKE_LIMIT", "").strip()
    if raw_limit:
        try:
            prompts = prompts[: max(1, int(raw_limit))]
        except ValueError:
            pass

    report = harness.run_cases(prompts, suite="Tier A — Product Smoke")
    filename = (os.environ.get("ASK_TEST_REPORT_NAME") or "ask_test_report.json").strip()
    path = write_report(report, filename=filename or "ask_test_report.json")
    # Optional durable baseline alias (does not overwrite the primary report name)
    baseline = (os.environ.get("ASK_TEST_BASELINE_NAME") or "").strip()
    if baseline:
        write_report(report, filename=baseline)
    assert path.exists()
    assert report["total"] == len(prompts)
    # Founder gate: Tier A must be 100%
    failed = [q for q in report["questions"] if not q["pass"]]
    assert report["pass_rate"] == 1.0, (
        "Tier A smoke must pass 100%. Failures: "
        + "; ".join(f"{q['id']}: {q['failures']}" for q in failed)
    )
