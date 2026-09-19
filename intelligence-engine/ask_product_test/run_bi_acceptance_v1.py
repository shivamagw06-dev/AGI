#!/usr/bin/env python3
"""Run Business Intelligence Acceptance Test v1.0 (foundation in-process).

Does NOT call Ask. Exit 0 iff pass rate ≥ 95%.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ask_product_test.bi_acceptance_v1 import BI_ACCEPTANCE_100, evaluate_bi_case
from ask_product_test.harness import write_artifact
from business_intelligence.foundation.production import analyse, health


def main() -> int:
    h = health()
    print(f"[bi_acceptance_v1] foundation version={h.get('version')} ask_wired={h.get('ask_wired')}", flush=True)
    rows = []
    for i, case in enumerate(BI_ACCEPTANCE_100, 1):
        print(f"[{i}/100] {case['id']} — {case['prompt'][:70]}", flush=True)
        try:
            payload = analyse(case["prompt"])
        except Exception as exc:
            payload = {"ok": False, "summary": "", "modules_used": [], "fabricated": False, "error": str(exc)}
        row = evaluate_bi_case(case, payload)
        rows.append(row)
        print(f"  pass={row['pass']} modules={row['modules']} failed={row['failed_assertions']}", flush=True)

    passed = sum(1 for r in rows if r["pass"])
    by_cat: dict = {}
    for r in rows:
        by_cat.setdefault(r["category"], {"count": 0, "passed": 0})
        by_cat[r["category"]]["count"] += 1
        if r["pass"]:
            by_cat[r["category"]]["passed"] += 1

    rate = round(100.0 * passed / len(rows), 2) if rows else 0.0
    report = {
        "suite": "Business Intelligence Acceptance Test v1.0",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ask_wired": bool(h.get("ask_wired")),
        "ask_wired_via": h.get("ask_wired_via"),
        "total": len(rows),
        "passed": passed,
        "pass_rate_pct": rate,
        "gate_pct": 95.0,
        "by_category": {
            k: {**v, "pass_rate_pct": round(100.0 * v["passed"] / v["count"], 2)} for k, v in by_cat.items()
        },
        "release_decision": "PASS" if rate >= 95.0 else "FAIL",
        "questions": rows,
    }
    write_artifact("bi_acceptance_v1.json", report)
    print(
        f"\n[bi_acceptance_v1] {passed}/{len(rows)} ({rate}%) decision={report['release_decision']}",
        flush=True,
    )
    for k, v in report["by_category"].items():
        print(f"  {k}: {v['passed']}/{v['count']} ({v['pass_rate_pct']}%)", flush=True)
    return 0 if report["release_decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
