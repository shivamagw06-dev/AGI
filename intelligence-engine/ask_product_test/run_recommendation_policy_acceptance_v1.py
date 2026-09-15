#!/usr/bin/env python3
"""Run Recommendation Policy Acceptance (Ask inprocess/live)."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from ask_product_test.harness import AskProductHarness, write_artifact
from ask_product_test.recommendation_policy_acceptance_v1 import (
    RECO_POLICY_CASES,
    evaluate_reco_case,
)


def main() -> int:
    os.environ.setdefault("ASK_TEST_MODE", "inprocess")
    h = AskProductHarness(latency_budget_ms=int(os.environ.get("ASK_TEST_LATENCY_MS") or "120000"))
    rows = []
    for i, case in enumerate(RECO_POLICY_CASES, 1):
        print(f"[{i}/{len(RECO_POLICY_CASES)}] {case['id']} — {case['prompt']}", flush=True)
        transport = h.ask(case["prompt"], case=case)
        payload = transport.get("payload") if isinstance(transport.get("payload"), dict) else {}
        row = evaluate_reco_case(case, payload if isinstance(payload, dict) else {})
        rows.append(row)
        print(f"  pass={row['pass']} failed={row['failed_assertions']}", flush=True)
    passed = sum(1 for r in rows if r["pass"])
    report = {
        "suite": "Recommendation Policy Acceptance v1",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": h.mode,
        "total": len(rows),
        "passed": passed,
        "pass_rate_pct": round(100.0 * passed / max(1, len(rows)), 2),
        "release_decision": "PASS" if passed == len(rows) else "FAIL",
        "questions": rows,
    }
    write_artifact("recommendation_policy_acceptance_v1.json", report)
    print(f"\n[reco_policy] {passed}/{len(rows)} decision={report['release_decision']}", flush=True)
    return 0 if report["release_decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
