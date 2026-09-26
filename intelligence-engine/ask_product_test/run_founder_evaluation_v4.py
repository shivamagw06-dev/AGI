#!/usr/bin/env python3
"""Run Founder Evaluation V4 (investment-focused) via KUL in-process.

Exit 0 iff pass rate ≥ 95%.
Writes /workspace/artifacts/founder_evaluation_v4.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ASK_TEST_MODE", "inprocess")
os.environ.setdefault("IKT_STORE_ROOT", str(ROOT / "data" / "institutional_knowledge_tables"))

from ask_product_test.founder_evaluation_v4 import (  # noqa: E402
    FOUNDER_EVAL_V4_100,
    evaluate_founder_v4_case,
)
from knowledge_unification.production import plan_and_gather  # noqa: E402
from knowledge_unification.registry import KnowledgeRegistry  # noqa: E402
import knowledge_unification.registry as kul_registry  # noqa: E402


def main() -> int:
    kul_registry._REGISTRY = KnowledgeRegistry()
    assert len(FOUNDER_EVAL_V4_100) == 100
    rows = []
    for i, case in enumerate(FOUNDER_EVAL_V4_100, 1):
        print(f"[{i}/100] {case['id']} — {case['prompt'][:72]}", flush=True)
        t0 = time.perf_counter()
        try:
            payload = plan_and_gather(case["prompt"])
            payload = {
                **payload,
                "answer": {
                    "summary": payload.get("summary") or "",
                    "executive_summary": payload.get("summary") or "",
                    "why": payload.get("why") or [],
                },
                "executive_summary": payload.get("summary") or "",
                "ask_orchestration": {"short_circuit": "knowledge_unification"},
            }
        except Exception as exc:
            payload = {
                "summary": "",
                "answer": {"summary": ""},
                "fabricated": False,
                "error": str(exc),
            }
        latency = int((time.perf_counter() - t0) * 1000)
        row = evaluate_founder_v4_case(case, payload, latency_ms=latency)
        rows.append(row)
        print(
            f"  pass={row['pass']} score={row.get('final_score')} "
            f"providers={row.get('providers')} hard={list((row.get('hard_fail_flags') or {}).keys())}",
            flush=True,
        )

    passed = sum(1 for r in rows if r["pass"])
    rate = round(100.0 * passed / len(rows), 2) if rows else 0.0
    gate = 95.0
    report = {
        "suite": "Founder Evaluation V4",
        "phase": "3.2.5",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total": len(rows),
        "passed": passed,
        "pass_rate_pct": rate,
        "gate_pct": gate,
        "release_decision": "PASS" if rate >= gate else "FAIL",
        "questions": rows,
    }
    out = Path("/workspace/artifacts")
    out.mkdir(parents=True, exist_ok=True)
    (out / "founder_evaluation_v4.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\n[founder_v4] {passed}/{len(rows)} ({rate}%) decision={report['release_decision']}", flush=True)
    fails = [r for r in rows if not r["pass"]]
    for r in fails[:20]:
        print(
            f"  FAIL {r['id']} score={r.get('final_score')} hard={list((r.get('hard_fail_flags') or {}).keys())} "
            f":: {r.get('prompt', '')[:60]}",
            flush=True,
        )
    return 0 if report["release_decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
