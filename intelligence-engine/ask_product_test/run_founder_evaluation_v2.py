#!/usr/bin/env python3
"""AGI Founder Evaluation V2 — 50-question production validation gate.

Default mode: ASK_TEST_MODE=inprocess (product path via UiService).
Gate: ≥95% pass rate, zero hard-fail flags, zero framework leakage.

Writes:
  artifacts/founder_evaluation_v2.json
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ask_product_test.founder_evaluation_v2 import FOUNDER_EVAL_V2_50, evaluate_founder_v2_case
from ask_product_test.harness import AskProductHarness, _artifacts_dir, write_artifact


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> int:
    os.environ.setdefault("ASK_TEST_MODE", "inprocess")
    latency = int(os.environ.get("ASK_TEST_LATENCY_MS") or "180000")
    cooldown = float(os.environ.get("ASK_TEST_CASE_COOLDOWN_SEC", "0") or "0")
    h = AskProductHarness(latency_budget_ms=latency)
    out_dir = _artifacts_dir()
    print(
        f"[founder_eval_v2] mode={h.mode} cases={len(FOUNDER_EVAL_V2_50)} cooldown={cooldown}s",
        flush=True,
    )

    results: List[Dict[str, Any]] = []
    for i, case in enumerate(FOUNDER_EVAL_V2_50, 1):
        if i > 1 and cooldown > 0 and h.mode == "live":
            time.sleep(cooldown)
        print(f"\n[{i}/50] {case['id']} ({case['section']}) — {case['prompt'][:90]}", flush=True)
        transport = h.ask(case["prompt"], case=case)
        payload = transport.get("payload") if isinstance(transport.get("payload"), dict) else {}
        row = evaluate_founder_v2_case(
            case,
            payload if isinstance(payload, dict) else {},
            latency_ms=transport.get("latency_ms"),
            http_status=transport.get("http_status"),
            raw_html=bool(transport.get("raw_is_html")),
        )
        results.append(row)
        print(
            f"  pass={row['pass']} score={row['final_score']}/30 "
            f"hard={list(row.get('hard_fail_flags') or {})} "
            f"providers={row.get('providers')} sc={row.get('short_circuit')}",
            flush=True,
        )
        print(f"  answer: {(row.get('answer') or '')[:220]}", flush=True)
        partial = {
            "suite": "AGI Founder Evaluation V2",
            "timestamp": _ts(),
            "partial": True,
            "completed_so_far": len(results),
            "questions": results,
        }
        write_artifact("founder_evaluation_v2.json", partial)

    passed = sum(1 for r in results if r.get("pass"))
    rate = round(100.0 * passed / max(1, len(results)), 2)
    hard_union: Dict[str, bool] = {}
    for r in results:
        for k in r.get("hard_fail_flags") or {}:
            hard_union[k] = True
    framework_leaks = sum(
        1
        for r in results
        if not (r.get("product_assertions") or {}).get("no_framework_leakage", True)
    )
    avg_score = round(sum(r.get("final_score") or 0 for r in results) / max(1, len(results)), 2)

    gate = 95.0
    release_pass = rate >= gate and not hard_union and framework_leaks == 0

    report = {
        "suite": "AGI Founder Evaluation V2 (Business Reasoning Emphasis)",
        "version": "2.0",
        "timestamp": _ts(),
        "mode": h.mode,
        "base_url": h.base_url,
        "total_questions": len(results),
        "passed": passed,
        "pass_rate_pct": rate,
        "gate_pct": gate,
        "average_score": avg_score,
        "max_score": 30,
        "hard_fail_flags": hard_union,
        "framework_leakage_count": framework_leaks,
        "release_criteria": {
            "pass_rate_min_pct": gate,
            "no_hard_fail_flags": True,
            "no_framework_leakage": True,
            "no_generic_retrieval_only": True,
            "direct_answer_first": True,
        },
        "release_decision": "PASS" if release_pass else "FAIL",
        "questions": results,
    }
    write_artifact("founder_evaluation_v2.json", report)
    print(
        f"\n[founder_eval_v2] {passed}/{len(results)} ({rate}%) avg={avg_score}/30 "
        f"decision={report['release_decision']} hard={list(hard_union)}",
        flush=True,
    )
    return 0 if release_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
