#!/usr/bin/env python3
"""Run Unknown Entity Acceptance (Ask inprocess/live)."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from ask_product_test.harness import AskProductHarness, write_artifact
from ask_product_test.unknown_entity_acceptance_v1 import (
    UNKNOWN_ENTITY_CASES,
    evaluate_unknown_case,
)


def main() -> int:
    os.environ.setdefault("ASK_TEST_MODE", "inprocess")
    h = AskProductHarness(latency_budget_ms=int(os.environ.get("ASK_TEST_LATENCY_MS") or "120000"))
    rows = []
    for i, case in enumerate(UNKNOWN_ENTITY_CASES, 1):
        print(f"[{i}/{len(UNKNOWN_ENTITY_CASES)}] {case['id']} — {case['prompt']}", flush=True)
        transport = h.ask(case["prompt"], case=case)
        payload = transport.get("payload") if isinstance(transport.get("payload"), dict) else {}
        row = evaluate_unknown_case(case, payload if isinstance(payload, dict) else {})
        rows.append(row)
        print(f"  pass={row['pass']} failed={row['failed_assertions']}", flush=True)
    passed = sum(1 for r in rows if r["pass"])
    report = {
        "suite": "Unknown Entity Acceptance v1",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": h.mode,
        "total": len(rows),
        "passed": passed,
        "pass_rate_pct": round(100.0 * passed / max(1, len(rows)), 2),
        "release_decision": "PASS" if passed == len(rows) else "FAIL",
        "questions": rows,
    }
    write_artifact("unknown_entity_acceptance_v1.json", report)
    print(f"\n[unknown_entity] {passed}/{len(rows)} decision={report['release_decision']}", flush=True)
    return 0 if report["release_decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
