#!/usr/bin/env python3
"""Run Knowledge Unification Acceptance Test v1.0 (in-process)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ask_product_test.harness import write_artifact
from ask_product_test.kul_acceptance_v1 import KUL_ACCEPTANCE_60, evaluate_kul_case
from knowledge_unification.production import plan_and_gather


def main() -> int:
    rows = []
    for i, case in enumerate(KUL_ACCEPTANCE_60, 1):
        print(f"[{i}/60] {case['id']} — {case['prompt'][:70]}", flush=True)
        try:
            payload = plan_and_gather(case["prompt"])
        except Exception as exc:
            payload = {"ok": False, "summary": "", "coverage": {}, "diagnostics": {}, "error": str(exc)}
        row = evaluate_kul_case(case, payload)
        rows.append(row)
        print(f"  pass={row['pass']} sources={row['sources']} failed={row['failed_assertions']}", flush=True)

    passed = sum(1 for r in rows if r["pass"])
    by_cat: dict = {}
    for r in rows:
        by_cat.setdefault(r["category"], {"count": 0, "passed": 0})
        by_cat[r["category"]]["count"] += 1
        if r["pass"]:
            by_cat[r["category"]]["passed"] += 1

    report = {
        "suite": "Knowledge Unification Acceptance Test v1.0",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total": len(rows),
        "passed": passed,
        "pass_rate_pct": round(100.0 * passed / len(rows), 2) if rows else 0.0,
        "by_category": {
            k: {**v, "pass_rate_pct": round(100.0 * v["passed"] / v["count"], 2)} for k, v in by_cat.items()
        },
        "release_decision": "PASS" if passed == len(rows) else "FAIL",
        "questions": rows,
    }
    write_artifact("kul_acceptance_v1.json", report)
    print(
        f"\n[kul_acceptance_v1] {passed}/{len(rows)} ({report['pass_rate_pct']}%) "
        f"decision={report['release_decision']}",
        flush=True,
    )
    for k, v in report["by_category"].items():
        print(f"  {k}: {v['passed']}/{v['count']} ({v['pass_rate_pct']}%)", flush=True)
    return 0 if report["release_decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
