#!/usr/bin/env python3
"""Run Research Memory Regression. Gate: 100%."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ask_product_test.research_memory_regression import (  # noqa: E402
    MEMORY_REGRESSION,
    evaluate_memory_case,
)
from research_intelligence.production import analyse, health  # noqa: E402


def main() -> int:
    h = health()
    print(f"[memory_regression] n={len(MEMORY_REGRESSION)} ask_wired={h.get('ask_wired')}", flush=True)
    rows = []
    for i, case in enumerate(MEMORY_REGRESSION, 1):
        print(f"[{i}/{len(MEMORY_REGRESSION)}] {case['id']} — {case['prompt'][:72]}", flush=True)
        payload = analyse(case["prompt"], entity=case["entity"])
        row = evaluate_memory_case(case, payload)
        rows.append(row)
        print(f"  pass={row['pass']} failed={row['failed_assertions']}", flush=True)

    passed = sum(1 for r in rows if r["pass"])
    rate = round(100.0 * passed / len(rows), 2)
    decision = "PASS" if rate >= 100.0 else "FAIL"
    report = {
        "suite": "Research Memory Regression",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total": len(rows),
        "passed": passed,
        "pass_rate_pct": rate,
        "gate_pct": 100.0,
        "release_decision": decision,
        "questions": rows,
    }
    for out in (Path("/workspace/artifacts"), Path("/opt/cursor/artifacts")):
        try:
            out.mkdir(parents=True, exist_ok=True)
            (out / "research_memory_regression.json").write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )
        except OSError:
            pass
    print(f"\n[memory_regression] {passed}/{len(rows)} ({rate}%) {decision}", flush=True)
    for r in rows:
        if not r["pass"]:
            print(f"  FAIL {r['id']} {r['failed_assertions']}", flush=True)
    return 0 if decision == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
