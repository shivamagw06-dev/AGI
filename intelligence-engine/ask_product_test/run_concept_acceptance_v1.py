#!/usr/bin/env python3
"""Concept Acceptance Test v1.0 — runner.

Run:
    ASK_TEST_MODE=live ASK_TEST_BASE=https://finance-news-backend-19i5.onrender.com \\
        python3 -m ask_product_test.run_concept_acceptance_v1

Writes artifacts/concept_acceptance_v1.json. Exit code 0 iff every question
passes all six assertions.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ask_product_test import checks
from ask_product_test.concept_acceptance_v1 import CONCEPT_ACCEPTANCE_QUESTIONS, evaluate_concept_question
from ask_product_test.harness import AskProductHarness, _artifacts_dir, write_artifact


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _evaluate_one(case: Dict[str, Any], payload: Dict[str, Any], *, latency_ms: int, http_status: int) -> Dict[str, Any]:
    text = checks.extract_answer_text(payload) if isinstance(payload, dict) else ""
    raw_orch = payload.get("ask_orchestration") if isinstance(payload, dict) else {}
    raw_orch = raw_orch if isinstance(raw_orch, dict) else {}
    funnel = raw_orch.get("funnel") if isinstance(raw_orch.get("funnel"), dict) else {}
    entity = raw_orch.get("entity") if isinstance(raw_orch.get("entity"), dict) else {}
    # entity.detected is the actually-BOUND ticker/company (None for a pure
    # concept question); entity.name can legitimately hold a non-company
    # label (e.g. "ROIC" tagged entity_type="Financial Metric") without any
    # entity lookup/resolution having occurred against a company universe.
    return evaluate_concept_question(
        case,
        text=text,
        financial_engine=raw_orch.get("financial_engine"),
        financial_router_triggered=raw_orch.get("financial_router_triggered"),
        short_circuit=raw_orch.get("short_circuit"),
        retrieved=funnel.get("retrieved"),
        entity_detected=entity.get("detected") or raw_orch.get("bound_ticker") or raw_orch.get("ticker_source"),
        http_status=http_status,
        latency_ms=latency_ms,
        financial_engine_key=raw_orch.get("financial_engine_key"),
    )


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> int:
    latency = int(os.environ.get("ASK_TEST_LATENCY_MS") or "120000")
    cooldown = float(os.environ.get("ASK_TEST_CASE_COOLDOWN_SEC", "4") or "4")
    h = AskProductHarness(latency_budget_ms=latency)
    out_dir = _artifacts_dir()

    print(
        f"[concept_acceptance_v1] mode={h.mode} base={h.base_url} cases={len(CONCEPT_ACCEPTANCE_QUESTIONS)}",
        flush=True,
    )

    rows: List[Dict[str, Any]] = []
    for i, case in enumerate(CONCEPT_ACCEPTANCE_QUESTIONS, 1):
        if i > 1 and cooldown > 0 and h.mode == "live":
            time.sleep(cooldown)
        print(f"\n[{i}/{len(CONCEPT_ACCEPTANCE_QUESTIONS)}] {case['id']} — {case['prompt']}", flush=True)
        transport = h.ask(case["prompt"])
        payload = transport.get("payload") if isinstance(transport.get("payload"), dict) else {}
        row = _evaluate_one(
            case, payload, latency_ms=transport.get("latency_ms") or 0, http_status=transport.get("http_status") or 0
        )
        rows.append(row)
        print(
            f"  pass={row['pass']} engine={row['financial_engine']} short_circuit={row['short_circuit']} "
            f"failed={row['failed_assertions']} ms={row['latency_ms']}",
            flush=True,
        )
        print(f"  answer: {(row.get('answer') or '')[:200]}", flush=True)

    passed = sum(1 for r in rows if r["pass"])
    total = len(rows)
    assertion_pass_rates: Dict[str, float] = {}
    for assertion_name in ("routed_to_financial_concepts", "no_retrieval", "no_entity_lookup",
                            "correct_concept_card", "direct_answer_first", "no_hallucination"):
        hits = sum(1 for r in rows if r["assertions"].get(assertion_name))
        assertion_pass_rates[assertion_name] = round(100.0 * hits / total, 2) if total else 0.0

    report = {
        "suite": "Concept Acceptance Test v1.0",
        "timestamp": _ts(),
        "mode": h.mode,
        "base_url": h.base_url,
        "total_questions": total,
        "passed": passed,
        "pass_rate_pct": round(100.0 * passed / total, 2) if total else 0.0,
        "assertion_pass_rates_pct": assertion_pass_rates,
        "release_decision": "PASS" if passed == total else "FAIL",
        "questions": rows,
    }
    write_artifact("concept_acceptance_v1.json", report)
    _write_json(out_dir / "concept_acceptance_v1.json", report)

    print(
        f"\n[concept_acceptance_v1] {passed}/{total} passed ({report['pass_rate_pct']}%) "
        f"decision={report['release_decision']}",
        flush=True,
    )
    for name, rate in assertion_pass_rates.items():
        print(f"  {name}: {rate}%", flush=True)
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
