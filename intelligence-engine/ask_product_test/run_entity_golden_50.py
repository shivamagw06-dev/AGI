#!/usr/bin/env python3
"""Run Entity Golden 50. Gate: 100%."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ask_product_test.entity_golden_50 import ENTITY_GOLDEN_50, evaluate_golden_case  # noqa: E402
from entity_intelligence.production import analyse, health  # noqa: E402


def main() -> int:
    h = health()
    assert len(ENTITY_GOLDEN_50) == 50
    print(f"[entity_golden_50] version={h.get('version')}", flush=True)
    rows = []
    for i, case in enumerate(ENTITY_GOLDEN_50, 1):
        print(f"[{i}/50] {case['id']} — {case['prompt'][:72]}", flush=True)
        row = evaluate_golden_case(case, analyse(case["prompt"]))
        rows.append(row)
        print(f"  pass={row['pass']} state={row['state']} ticker={row['ticker']}", flush=True)
    passed = sum(1 for r in rows if r["pass"])
    rate = round(100.0 * passed / 50, 2)
    decision = "PASS" if rate >= 100.0 else "FAIL"
    report = {
        "suite": "Entity Golden 50",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total": 50,
        "passed": passed,
        "pass_rate_pct": rate,
        "release_decision": decision,
        "questions": rows,
    }
    for out in (Path("/workspace/artifacts"), Path("/opt/cursor/artifacts")):
        try:
            out.mkdir(parents=True, exist_ok=True)
            (out / "entity_golden_50.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
    print(f"\n[entity_golden_50] {passed}/50 ({rate}%) {decision}", flush=True)
    for r in rows:
        if not r["pass"]:
            print(f"  FAIL {r['id']} {r['failed_assertions']} :: {r['prompt']}", flush=True)
    return 0 if decision == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
