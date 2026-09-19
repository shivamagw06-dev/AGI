#!/usr/bin/env python3
"""Run Investment Integration Acceptance Suite v1.0 (KUL in-process).

Exit 0 iff pass rate ≥ 90% (freeze targets 100%).
Writes /workspace/artifacts/inv_integration_acceptance_v1.json
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("IKT_STORE_ROOT", str(ROOT / "data" / "institutional_knowledge_tables"))

from ask_product_test.inv_integration_acceptance_v1 import (  # noqa: E402
    INV_INTEGRATION_CASES,
    evaluate_inv_integration_case,
)
from investment_intelligence.production import health as inv_health  # noqa: E402
from knowledge_unification.production import plan_and_gather  # noqa: E402
from knowledge_unification.registry import KnowledgeRegistry  # noqa: E402
import knowledge_unification.registry as kul_registry  # noqa: E402


def main() -> int:
    kul_registry._REGISTRY = KnowledgeRegistry()

    h = inv_health()
    print(
        f"[inv_integration_v1] INV ask_wired={h.get('ask_wired')} via={h.get('ask_wired_via')} "
        f"profiles={h.get('profile_count')}",
        flush=True,
    )
    assert h.get("ask_wired") is True, "ASK_WIRED must be True for Phase 3.2.5"
    assert len(INV_INTEGRATION_CASES) == 75

    rows = []
    for i, case in enumerate(INV_INTEGRATION_CASES, 1):
        print(f"[{i}/75] {case['id']} — {case['prompt'][:72]}", flush=True)
        try:
            payload = plan_and_gather(case["prompt"])
        except Exception as exc:
            payload = {
                "ok": False,
                "summary": "",
                "why": [],
                "coverage": {"knowledge_sources_used": []},
                "diagnostics": {},
                "fabricated": False,
                "error": str(exc),
            }
        row = evaluate_inv_integration_case(case, payload)
        rows.append(row)
        print(
            f"  pass={row['pass']} sources={row['sources']} failed={row['failed_assertions']}",
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
    gate = 90.0
    report = {
        "suite": "Investment Integration Acceptance Suite v1.0",
        "phase": "3.2.5",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ask_wired": True,
        "ask_wired_via": h.get("ask_wired_via"),
        "recommendation_policy": h.get("recommendation_policy"),
        "total": len(rows),
        "passed": passed,
        "pass_rate_pct": rate,
        "gate_pct": gate,
        "by_category": {
            k: {**v, "pass_rate_pct": round(100.0 * v["passed"] / v["count"], 2)}
            for k, v in by_cat.items()
        },
        "release_decision": "PASS" if rate >= gate else "FAIL",
        "note": (
            "Engine acceptance (300/300) already green. This suite validates KUL/Ask "
            "integration. Founder Evaluation V4 + Golden/Coverage/Reco remain "
            "before Phase 3.2 freeze."
        ),
        "questions": rows,
    }
    out = Path("/workspace/artifacts")
    out.mkdir(parents=True, exist_ok=True)
    (out / "inv_integration_acceptance_v1.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"\n[inv_integration_v1] {passed}/{len(rows)} ({rate}%) decision={report['release_decision']}",
        flush=True,
    )
    for k, v in report["by_category"].items():
        print(f"  {k}: {v['passed']}/{v['count']} ({v['pass_rate_pct']}%)", flush=True)
    fails = [r for r in rows if not r["pass"]]
    if fails:
        print("\nFailures:", flush=True)
        for r in fails[:30]:
            print(
                f"  {r['id']} failed={r['failed_assertions']} sources={r['sources']} "
                f":: {r['prompt'][:56]}",
                flush=True,
            )
            print(f"    summary={r['summary'][:160]}", flush=True)
    return 0 if report["release_decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
