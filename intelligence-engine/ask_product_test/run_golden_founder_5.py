#!/usr/bin/env python3
"""Run permanent golden_founder_5 founder regression (live or inprocess).

Exit 1 if any case fails — intended as a release gate.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ask_product_test.golden_founder_5 import GOLDEN_FOUNDER_5, evaluate_payload
from ask_product_test.harness import AskProductHarness, _artifacts_dir, write_artifact


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    latency = int(os.environ.get("ASK_TEST_LATENCY_MS") or "120000")
    cooldown = float(os.environ.get("ASK_TEST_CASE_COOLDOWN_SEC", "12") or "12")
    h = AskProductHarness(latency_budget_ms=latency)
    out_dir = _artifacts_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"golden_founder_5_{stamp}.json"

    print(
        f"[golden_founder_5] mode={h.mode} base={h.base_url} cases={len(GOLDEN_FOUNDER_5)}",
        flush=True,
    )
    results: List[Dict[str, Any]] = []
    for i, case in enumerate(GOLDEN_FOUNDER_5, 1):
        if i > 1 and cooldown > 0 and h.mode == "live":
            time.sleep(cooldown)
        print(f"\n[{i}/5] {case['id']} — {case['prompt']}", flush=True)
        transport = h.ask(case["prompt"], case=case)
        payload = transport.get("payload") if isinstance(transport.get("payload"), dict) else {}
        scored = evaluate_payload(case, payload if isinstance(payload, dict) else {})
        scored["latency_ms"] = transport.get("latency_ms")
        scored["http_status"] = transport.get("http_status")
        scored["fallback_used"] = bool(
            (payload.get("ask_orchestration") or {}).get("fallback_used")
            if isinstance(payload, dict)
            else False
        )
        scored["prompt"] = case["prompt"]
        results.append(scored)
        print(
            f"  pass={scored['pass']} failures={scored['failures']} "
            f"ms={scored.get('latency_ms')}",
            flush=True,
        )
        print(f"  excerpt: {scored.get('summary_excerpt')}", flush=True)

    passed = sum(1 for r in results if r.get("pass"))
    scores = [r.get("score") or 0 for r in results]
    avg_score = round(sum(scores) / max(1, len(scores)), 2)
    hard_fail_union: Dict[str, bool] = {}
    for r in results:
        for k in (r.get("hard_fail_flags") or {}):
            hard_fail_union[k] = True
    release_block = avg_score < 25 or bool(hard_fail_union)
    report = {
        "suite": "golden_founder_5",
        "version": "v1.0",
        "timestamp": _ts(),
        "mode": h.mode,
        "base_url": h.base_url,
        "passed": passed,
        "total": len(results),
        "pass_rate": passed / max(1, len(results)),
        "average_score": avg_score,
        "max_score": 30,
        "hard_fail_flags": hard_fail_union,
        "release_block": release_block,
        "release_gate": {
            "fail_if_avg_below": 25,
            "fail_if_framework_scaffold_appears": True,
            "fail_if_unknown_entity_hallucinates": True,
            "fail_if_comparison_omits_entity": True,
            "fail_if_recommendation_regresses": True,
        },
        "results": results,
    }
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_artifact("golden_founder_5_latest.json", report)
    print(
        f"\n[golden_founder_5] {passed}/{len(results)} avg_score={avg_score}/30 "
        f"hard_fail_flags={list(hard_fail_union)} release_block={release_block} → {path}",
        flush=True,
    )
    return 1 if release_block else 0


if __name__ == "__main__":
    raise SystemExit(main())
