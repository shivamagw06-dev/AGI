#!/usr/bin/env python3
"""Run Industry Intelligence Acceptance Test v1.0 (engine in-process).

Does NOT call Ask / KUL. Exit 0 iff pass rate = 100%.
Gate before Module 14 (Ask integration).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ask_product_test.harness import write_artifact  # noqa: E402
from ask_product_test.industry_intelligence_acceptance_v1 import (
    II_ACCEPTANCE_200,
    evaluate_ii_case,
)
from industry_intelligence.production import analyse, health


def main() -> int:
    h = health()
    print(
        f"[ii_acceptance_v1] version={h.get('version')} "
        f"industries={h.get('industry_count')} ask_wired={h.get('ask_wired')}",
        flush=True,
    )
    # Engine acceptance is independent of Ask wiring; Phase 3.1.5 may flip ASK_WIRED.
    assert len(II_ACCEPTANCE_200) == 200

    rows = []
    for i, case in enumerate(II_ACCEPTANCE_200, 1):
        print(f"[{i}/200] {case['id']} — {case['prompt'][:72]}", flush=True)
        try:
            payload = analyse(case["prompt"], industry=case.get("industry"))
        except Exception as exc:
            payload = {
                "ok": False,
                "summary": "",
                "modules_used": [],
                "fabricated": False,
                "error": str(exc),
            }
        row = evaluate_ii_case(case, payload)
        rows.append(row)
        print(
            f"  pass={row['pass']} hits={row['topic_hits']} "
            f"modules={row['modules_used']} failed_fields={not row['field_ok']}",
            flush=True,
        )

    passed = sum(1 for r in rows if r["pass"])
    by_cat: dict = {}
    for r in rows:
        by_cat.setdefault(r["category"], {"count": 0, "passed": 0})
        by_cat[r["category"]]["count"] += 1
        if r["pass"]:
            by_cat[r["category"]]["passed"] += 1

    rate = round(100.0 * passed / len(rows), 2) if rows else 0.0
    report = {
        "suite": "Industry Intelligence Acceptance Test v1.0",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "version": h.get("version"),
        "ask_wired": bool(h.get("ask_wired")),
        "industry_count": h.get("industry_count"),
        "total": len(rows),
        "passed": passed,
        "pass_rate_pct": rate,
        "gate_pct": 100.0,
        "by_category": {
            k: {**v, "pass_rate_pct": round(100.0 * v["passed"] / v["count"], 2)}
            for k, v in by_cat.items()
        },
        "release_decision": "PASS" if rate >= 100.0 else "FAIL",
        "questions": rows,
    }
    write_artifact("industry_intelligence_acceptance_v1.json", report)
    print(
        f"\n[ii_acceptance_v1] {passed}/{len(rows)} ({rate}%) "
        f"decision={report['release_decision']}",
        flush=True,
    )
    for k, v in report["by_category"].items():
        print(f"  {k}: {v['passed']}/{v['count']} ({v['pass_rate_pct']}%)", flush=True)
    fails = [r for r in rows if not r["pass"]]
    if fails:
        print("\nFailures:", flush=True)
        for r in fails[:40]:
            print(
                f"  {r['id']} [{r['category']}] hits={r['topic_hits']} "
                f"field={r['field_ok']} industry={r['industry_ok']} "
                f"direct={r['direct_answer_first']} :: {r['prompt'][:60]}",
                flush=True,
            )
            print(f"    summary={r['summary'][:160]}", flush=True)
    return 0 if report["release_decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
