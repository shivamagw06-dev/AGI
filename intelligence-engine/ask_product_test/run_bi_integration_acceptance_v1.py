#!/usr/bin/env python3
"""Run Business Integration Acceptance Suite v1.0 (KUL in-process).

Exit 0 iff pass rate ≥ 90%. Writes /workspace/artifacts/bi_integration_acceptance_v1.json
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("IKT_STORE_ROOT", str(ROOT / "data" / "institutional_knowledge_tables"))

from ask_product_test.bi_integration_acceptance_v1 import (  # noqa: E402
    BI_INTEGRATION_CASES,
    evaluate_bi_integration_case,
)
from ask_product_test.harness import write_artifact  # noqa: E402
from business_intelligence.foundation.production import health as bi_health  # noqa: E402
from knowledge_unification.production import plan_and_gather  # noqa: E402
from knowledge_unification.registry import KnowledgeRegistry  # noqa: E402
import knowledge_unification.registry as kul_registry  # noqa: E402


def main() -> int:
    # Ensure singleton registry includes the BI provider (fresh process / hot reload).
    kul_registry._REGISTRY = KnowledgeRegistry()

    h = bi_health()
    print(
        f"[bi_integration_v1] BI ask_wired={h.get('ask_wired')} via={h.get('ask_wired_via')}",
        flush=True,
    )
    rows = []
    for i, case in enumerate(BI_INTEGRATION_CASES, 1):
        print(f"[{i}/{len(BI_INTEGRATION_CASES)}] {case['id']} — {case['prompt'][:72]}", flush=True)
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
        row = evaluate_bi_integration_case(case, payload)
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
        "suite": "Business Integration Acceptance Suite v1.0",
        "phase": "3.0.5",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ask_wired": True,
        "ask_wired_via": h.get("ask_wired_via"),
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
            "Engine acceptance (100/100) already green. This suite validates KUL/Ask "
            "integration only. Founder Evaluation + Golden5/AFI/Coverage/Reco remain "
            "before Phase 3 freeze."
        ),
        "questions": rows,
    }
    write_artifact("bi_integration_acceptance_v1.json", report)
    print(
        f"\n[bi_integration_v1] {passed}/{len(rows)} ({rate}%) decision={report['release_decision']}",
        flush=True,
    )
    for k, v in report["by_category"].items():
        print(f"  {k}: {v['passed']}/{v['count']} ({v['pass_rate_pct']}%)", flush=True)
    return 0 if report["release_decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
