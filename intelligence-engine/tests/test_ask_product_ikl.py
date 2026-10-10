"""Tier IKL — founder validation that persistent institutional memory is used.

Product-contract checks always apply.
IKL memory-layer asserts are soft on live (pre-deploy baseline) unless:

  ASK_TEST_IKL_STRICT=1

Run (contract / CI):
  cd intelligence-engine && pytest tests/test_ask_product_ikl.py -q

Run live (post-#437 deploy, strict):
  ASK_TEST_MODE=live \\
  ASK_TEST_BASE=https://finance-news-backend-19i5.onrender.com \\
  ASK_TEST_IKL_STRICT=1 \\
    pytest tests/test_ask_product_ikl.py -q
"""

from __future__ import annotations

import os

import pytest

from ask_product_test.harness import AskProductHarness, write_report
from ask_product_test.prompts import IKL_PROMPTS


@pytest.fixture(scope="module")
def harness() -> AskProductHarness:
    return AskProductHarness(latency_budget_ms=int(os.environ.get("ASK_TEST_LATENCY_MS", "90000")))


def test_ikl_founder_suite(harness: AskProductHarness):
    prompts = list(IKL_PROMPTS)
    report = harness.run_cases(prompts, suite="Tier IKL — Institutional Memory")
    path = write_report(report, filename="ask_test_report_ikl.json")
    # Also keep a dated alias for pre/post comparison folders
    tag = (os.environ.get("ASK_TEST_REPORT_TAG") or "").strip()
    if tag:
        write_report(report, filename=f"ask_test_report_ikl_{tag}.json")
    assert path.exists()
    assert report["total"] == len(prompts)

    # Always: no policy violations, no hallucination risk on the gap prompt
    policy_violations = [
        q for q in report["questions"] if q.get("policy") == "violation"
    ]
    assert not policy_violations, policy_violations

    gap = next(q for q in report["questions"] if q["id"] == "IKL-05")
    assert gap.get("hallucination_risk", 0) == 0
    assert gap.get("insufficient_evidence") or gap.get("degraded") or gap.get("pass")

    strict = str(os.environ.get("ASK_TEST_IKL_STRICT", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    # Contract mode always exercises fixtures with IKL pack → expect 100%
    if harness.mode == "contract" or strict:
        failed = [q for q in report["questions"] if not q["pass"]]
        assert report["pass_rate"] == 1.0, (
            "IKL suite must pass 100% in contract/strict mode. Failures: "
            + "; ".join(f"{q['id']}: {q['failures']}" for q in failed)
        )
    else:
        # Live soft mode: product contract must still hold (pass_rate from evaluate)
        # Soft IKL layer misses are recorded in ikl_meta, not hard failures.
        failed = [q for q in report["questions"] if not q["pass"]]
        assert report["pass_rate"] >= 0.8, (
            "IKL live soft mode: product contract pass_rate < 80%. Failures: "
            + "; ".join(f"{q['id']}: {q['failures']}" for q in failed)
        )

    metrics = report.get("comparison_metrics") or {}
    assert "company_memory_hits" in metrics
    assert "fallback_rate" in metrics
