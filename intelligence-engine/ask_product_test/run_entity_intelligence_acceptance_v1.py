#!/usr/bin/env python3
"""Run Entity Intelligence Acceptance v1. Gate: 100%, wrong binds = 0."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ask_product_test.entity_intelligence_acceptance_v1 import (  # noqa: E402
    EI_ACCEPTANCE,
    evaluate_ei_case,
)
from entity_intelligence.production import analyse, health  # noqa: E402


def main() -> int:
    h = health()
    print(f"[ei_acceptance_v1] version={h.get('version')} n={len(EI_ACCEPTANCE)}", flush=True)
    rows = []
    for i, case in enumerate(EI_ACCEPTANCE, 1):
        print(f"[{i}/{len(EI_ACCEPTANCE)}] {case['id']} — {case['prompt'][:72]}", flush=True)
        contract = analyse(case["prompt"])
        row = evaluate_ei_case(case, contract)
        rows.append(row)
        print(f"  pass={row['pass']} state={row['state']} ticker={row['ticker']} failed={row['failed_assertions']}", flush=True)

    passed = sum(1 for r in rows if r["pass"])
    rate = round(100.0 * passed / len(rows), 2) if rows else 0.0
    wrong = sum(1 for r in rows if not r["assertions"].get("no_wrong_entity", True))
    by_cat: dict = {}
    for r in rows:
        by_cat.setdefault(r["category"], {"count": 0, "passed": 0})
        by_cat[r["category"]]["count"] += 1
        if r["pass"]:
            by_cat[r["category"]]["passed"] += 1

    decision = "PASS" if rate >= 100.0 and wrong == 0 else "FAIL"
    report = {
        "suite": "Entity Intelligence Acceptance v1",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "version": h.get("version"),
        "total": len(rows),
        "passed": passed,
        "pass_rate_pct": rate,
        "wrong_entity_bindings": wrong,
        "gate_pct": 100.0,
        "by_category": {
            k: {**v, "pass_rate_pct": round(100.0 * v["passed"] / v["count"], 2)}
            for k, v in by_cat.items()
        },
        "release_decision": decision,
        "questions": rows,
    }
    for out in (Path("/workspace/artifacts"), Path("/opt/cursor/artifacts")):
        try:
            out.mkdir(parents=True, exist_ok=True)
            (out / "entity_intelligence_acceptance_v1.json").write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )
        except OSError:
            pass
    print(f"\n[ei_acceptance_v1] {passed}/{len(rows)} ({rate}%) wrong={wrong} {decision}", flush=True)
    for k, v in report["by_category"].items():
        print(f"  {k}: {v['passed']}/{v['count']} ({v['pass_rate_pct']}%)", flush=True)
    for r in rows:
        if not r["pass"]:
            print(f"  FAIL {r['id']} {r['failed_assertions']} :: {r['prompt'][:70]}", flush=True)
            print(f"    summary={r['summary'][:160]}", flush=True)
    return 0 if decision == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
