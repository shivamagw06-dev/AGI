#!/usr/bin/env python3
"""Run Golden Business 20 permanent regression suite.

Default: ASK_TEST_MODE=inprocess. Exit 0 iff all 20 pass.
Writes artifacts/golden_business_20.json
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ask_product_test.golden_business_20 import GOLDEN_BUSINESS_20, evaluate_golden_business_case
from ask_product_test.harness import AskProductHarness, _artifacts_dir, write_artifact


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    os.environ.setdefault("ASK_TEST_MODE", "inprocess")
    latency = int(os.environ.get("ASK_TEST_LATENCY_MS") or "180000")
    cooldown = float(os.environ.get("ASK_TEST_CASE_COOLDOWN_SEC", "0") or "0")
    h = AskProductHarness(latency_budget_ms=latency)
    out_dir = _artifacts_dir()
    print(f"[golden_business_20] mode={h.mode} cases={len(GOLDEN_BUSINESS_20)}", flush=True)
    results: List[Dict[str, Any]] = []
    for i, case in enumerate(GOLDEN_BUSINESS_20, 1):
        if i > 1 and cooldown > 0 and h.mode == "live":
            time.sleep(cooldown)
        print(f"[{i}/20] {case['id']} — {case['prompt'][:72]}", flush=True)
        transport = h.ask(case["prompt"], case=case)
        payload = transport.get("payload") if isinstance(transport.get("payload"), dict) else {}
        row = evaluate_golden_business_case(case, payload if isinstance(payload, dict) else {})
        row["latency_ms"] = transport.get("latency_ms")
        results.append(row)
        print(f"  pass={row['pass']} failed={row['failed_assertions']} providers={row['providers']}", flush=True)

    passed = sum(1 for r in results if r["pass"])
    by_cat: Dict[str, Dict[str, int]] = {}
    for r in results:
        by_cat.setdefault(r["category"], {"count": 0, "passed": 0})
        by_cat[r["category"]]["count"] += 1
        if r["pass"]:
            by_cat[r["category"]]["passed"] += 1

    report = {
        "suite": "Golden Business 20",
        "version": "1.0",
        "timestamp": _ts(),
        "mode": h.mode,
        "total": len(results),
        "passed": passed,
        "pass_rate_pct": round(100.0 * passed / max(1, len(results)), 2),
        "gate": "20/20",
        "by_category": {
            k: {**v, "pass_rate_pct": round(100.0 * v["passed"] / v["count"], 2)}
            for k, v in by_cat.items()
        },
        "release_decision": "PASS" if passed == len(results) else "FAIL",
        "questions": results,
    }
    write_artifact("golden_business_20.json", report)
    print(
        f"\n[golden_business_20] {passed}/{len(results)} decision={report['release_decision']}",
        flush=True,
    )
    return 0 if report["release_decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
