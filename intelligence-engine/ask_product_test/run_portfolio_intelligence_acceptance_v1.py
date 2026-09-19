#!/usr/bin/env python3
"""Run Portfolio Intelligence Acceptance Test v1.0 (engine in-process).

Does NOT call Ask / KUL. Exit 0 iff pass rate = 100%.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ask_product_test.portfolio_intelligence_acceptance_v1 import (  # noqa: E402
    PI_ACCEPTANCE_300,
    evaluate_pi_case,
)
from portfolio_intelligence.foundation.production import analyse, health  # noqa: E402


def main() -> int:
    h = health()
    print(
        f"[pi_acceptance_v1] version={h.get('version')} "
        f"portfolios={h.get('portfolio_count')} ask_wired={h.get('ask_wired')}",
        flush=True,
    )
    # ASK_WIRED may be True after Phase 3.3.5 KUL integration.
    assert len(PI_ACCEPTANCE_300) == 300

    rows = []
    for i, case in enumerate(PI_ACCEPTANCE_300, 1):
        print(f"[{i}/300] {case['id']} — {case['prompt'][:72]}", flush=True)
        try:
            payload = analyse(
                case["prompt"],
                portfolio_id=case.get("portfolio_id"),
            )
        except Exception as exc:
            payload = {
                "ok": False,
                "summary": "",
                "portfolio_summary": "",
                "modules_used": [],
                "fabricated": False,
                "recommendation": "BUY",
                "error": str(exc),
            }
        row = evaluate_pi_case(case, payload)
        rows.append(row)
        print(
            f"  pass={row['pass']} hits={row['topic_hits']} "
            f"failed={row['failed_assertions']}",
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
        "suite": "Portfolio Intelligence Acceptance Test v1.0",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "version": h.get("version"),
        "ask_wired": bool(h.get("ask_wired")),
        "recommendation_policy": h.get("recommendation_policy"),
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
    out = Path("/workspace/artifacts")
    out.mkdir(parents=True, exist_ok=True)
    (out / "portfolio_intelligence_acceptance_v1.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"\n[pi_acceptance_v1] {passed}/{len(rows)} ({rate}%) "
        f"decision={report['release_decision']}",
        flush=True,
    )
    for k, v in report["by_category"].items():
        print(f"  {k}: {v['passed']}/{v['count']} ({v['pass_rate_pct']}%)", flush=True)
    fails = [r for r in rows if not r["pass"]]
    if fails:
        print("\nFailures:", flush=True)
        for r in fails[:50]:
            print(
                f"  {r['id']} [{r['category']}] failed={r['failed_assertions']} "
                f":: {r['prompt'][:60]}",
                flush=True,
            )
            print(f"    summary={r['summary'][:160]}", flush=True)
    return 0 if report["release_decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
