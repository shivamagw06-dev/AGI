"""Tier B — AGI Ask Product Regression (CIO-25 + isolation + determinism).

Run:
  cd intelligence-engine && pytest tests/test_ask_product_regression.py -q

Quick sample:
  ASK_TEST_REGRESSION_LIMIT=5 pytest tests/test_ask_product_regression.py -q

Live gateway:
  ASK_TEST_MODE=live pytest tests/test_ask_product_regression.py -q
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List

import pytest

from ask_product_test.harness import (
    AskProductHarness,
    cio_cases_from_frozen,
    print_health_summary,
    write_report,
)
from ask_product_test.prompts import (
    CONTEXT_ISOLATION_SEQUENCE,
    DETERMINISM_PROMPT_IDS,
    UNKNOWN_COMPANY_PROMPT,
)


@pytest.fixture(scope="module")
def harness() -> AskProductHarness:
    return AskProductHarness(latency_budget_ms=int(os.environ.get("ASK_TEST_LATENCY_MS", "90000")))


def _limit_cases(cases: List[dict]) -> List[dict]:
    raw = os.environ.get("ASK_TEST_REGRESSION_LIMIT", "").strip()
    if not raw:
        return cases
    try:
        n = max(1, int(raw))
    except ValueError:
        return cases
    return cases[:n]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def test_tier_b_product_regression(harness: AskProductHarness):
    """Founder regression gate — CIO frozen + unknown + isolation + determinism."""
    h = AskProductHarness(
        mode=harness.mode,
        base_url=harness.base_url,
        latency_budget_ms=harness.latency_budget_ms,
    )

    cio_cases = _limit_cases(cio_cases_from_frozen())
    cio_report = h.run_cases(cio_cases, suite="Tier B — CIO Frozen")

    # Unknown company — never invent
    unknown_transport = h.ask(
        UNKNOWN_COMPANY_PROMPT["prompt"], case=UNKNOWN_COMPANY_PROMPT
    )
    unknown_row = h.evaluate(UNKNOWN_COMPANY_PROMPT, unknown_transport)

    # Context isolation sequence
    isolation_report = h.run_cases(
        CONTEXT_ISOLATION_SEQUENCE,
        suite="Tier B — Context Isolation",
        isolate_sequence=True,
    )

    # Determinism on selected CIO prompts
    by_id = {c["id"]: c for c in cio_cases_from_frozen()}
    det_rows = []
    for pid in DETERMINISM_PROMPT_IDS:
        case = by_id.get(pid)
        if not case:
            continue
        t1 = h.ask(case["prompt"], ticker=case.get("ticker"), case=case)
        t2 = h.ask(case["prompt"], ticker=case.get("ticker"), case=case)
        r1 = h.evaluate(case, t1)
        r2 = h.evaluate(case, t2)
        e1 = set(r1.get("entities") or [])
        e2 = set(r2.get("entities") or [])
        same_intent = (r1.get("intent") or "") == (r2.get("intent") or "")
        same_policy = (r1.get("policy") or "") == (r2.get("policy") or "")
        entity_ok = (not e1 and not e2) or bool(e1 & e2) or (not e1) or (not e2)
        ok = same_intent and same_policy and entity_ok
        det_rows.append(
            {
                "id": f"DET-{pid}",
                "prompt": case["prompt"],
                "pass": ok,
                "failures": []
                if ok
                else [
                    f"intent {r1.get('intent')} vs {r2.get('intent')}",
                    f"policy {r1.get('policy')} vs {r2.get('policy')}",
                    f"entities {sorted(e1)} vs {sorted(e2)}",
                ],
                "latency_ms": (r1.get("latency_ms") or 0) + (r2.get("latency_ms") or 0),
                "http_status": 200,
                "completed": True,
                "degraded": False,
                "intent": r1.get("intent"),
                "entities": sorted(e1 | e2),
                "entity": (sorted(e1 & e2) or [None])[0],
                "evidence_count": r1.get("evidence_count"),
                "evidence_sources": r1.get("evidence_sources"),
                "grounded_claims": r1.get("grounded_claims"),
                "confidence": r1.get("confidence"),
                "policy": r1.get("policy"),
                "policy_triggered": False,
                "freshness_timestamp": r1.get("freshness_timestamp"),
                "retryable": False,
                "insufficient_evidence": False,
                "context_leakage": False,
                "freshness_failure": False,
                "hallucination_risk": 0,
                "transport": r1.get("transport"),
                "error": None,
            }
        )

    questions = (
        list(cio_report.get("questions") or [])
        + [unknown_row]
        + list(isolation_report.get("questions") or [])
        + det_rows
    )
    passed = sum(1 for q in questions if q.get("pass"))
    total = len(questions)
    latencies = [q.get("latency_ms") or 0 for q in questions]
    report = {
        "suite": "Tier B — Product Regression",
        "timestamp": _ts(),
        "mode": h.mode,
        "pass_rate": (passed / total) if total else 0.0,
        "passed": passed,
        "total": total,
        "average_latency_ms": int(sum(latencies) / len(latencies)) if latencies else 0,
        "questions": questions,
        "sections": {
            "cio_frozen": {
                "passed": cio_report.get("passed"),
                "total": cio_report.get("total"),
                "pass_rate": cio_report.get("pass_rate"),
            },
            "unknown_company": {"pass": unknown_row.get("pass")},
            "context_isolation": {
                "passed": isolation_report.get("passed"),
                "total": isolation_report.get("total"),
                "pass_rate": isolation_report.get("pass_rate"),
            },
            "determinism": {
                "passed": sum(1 for r in det_rows if r["pass"]),
                "total": len(det_rows),
            },
        },
    }
    print_health_summary(report)
    filename = (os.environ.get("ASK_TEST_REPORT_NAME") or "ask_test_report.json").strip()
    path = write_report(report, filename=filename or "ask_test_report.json")
    baseline = (os.environ.get("ASK_TEST_BASELINE_NAME") or "").strip()
    if baseline:
        write_report(report, filename=baseline)
    assert path.exists()

    assert unknown_row["pass"], unknown_row.get("failures")
    assert (unknown_row.get("insufficient_evidence") or unknown_row.get("degraded") or unknown_row.get("evidence_count") == 0)
    assert isolation_report["pass_rate"] >= 0.95, isolation_report
    assert all(r["pass"] for r in det_rows), det_rows
    # Founder gate: ≥ 95% overall
    assert report["pass_rate"] >= 0.95, (
        f"Tier B pass_rate {report['pass_rate']:.0%} < 95%. "
        + "; ".join(f"{q.get('id')}: {q.get('failures')}" for q in questions if not q.get("pass"))
    )
