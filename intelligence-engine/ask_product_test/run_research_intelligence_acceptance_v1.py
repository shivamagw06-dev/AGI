#!/usr/bin/env python3
"""Run Research Intelligence Acceptance Test v1.0 (engine in-process).

Permanent Research Intelligence engine gate (in-process; not Ask).
After Phase 3.4.5, ASK_WIRED may be True via KUL provider only.

Pass when:
  - pass rate ≥ 95%
  - hallucinations = 0
  - recommendation leakage = 0
  - research memory leakage = 0
  - planner / module accuracy = 100%
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ask_product_test.research_intelligence_acceptance_v1 import (  # noqa: E402
    RI_ACCEPTANCE_400,
    evaluate_ri_case,
)
from research_intelligence.production import analyse, health  # noqa: E402

GATE_PCT = 95.0
WEIGHTS = {
    "research_accuracy": 0.30,
    "document_understanding": 0.20,
    "cross_document_reasoning": 0.15,
    "research_memory": 0.10,
    "evidence_quality": 0.10,
    "executive_communication": 0.10,
    "uncertainty": 0.05,
}


def main() -> int:
    h = health()
    print(
        f"[ri_acceptance_v1] version={h.get('version')} "
        f"entities={h.get('entity_count')} ask_wired={h.get('ask_wired')}",
        flush=True,
    )
    assert len(RI_ACCEPTANCE_400) == 400

    rows = []
    for i, case in enumerate(RI_ACCEPTANCE_400, 1):
        print(f"[{i}/400] {case['id']} — {case['prompt'][:72]}", flush=True)
        try:
            payload = analyse(case["prompt"], entity=case.get("entity"))
        except Exception as exc:
            payload = {
                "ok": False,
                "summary": "",
                "executive_summary": "",
                "modules_used": [],
                "fabricated": True,
                "recommendation": "BUY",
                "error": str(exc),
            }
        row = evaluate_ri_case(case, payload)
        rows.append(row)
        print(
            f"  pass={row['pass']} hits={row['topic_hits']} "
            f"weighted={row['weighted_score']} failed={row['failed_assertions']}",
            flush=True,
        )

    passed = sum(1 for r in rows if r["pass"])
    rate = round(100.0 * passed / len(rows), 2) if rows else 0.0

    by_section: dict = {}
    for r in rows:
        by_section.setdefault(r["section"], {"count": 0, "passed": 0})
        by_section[r["section"]]["count"] += 1
        if r["pass"]:
            by_section[r["section"]]["passed"] += 1

    # Aggregate weighted component scores
    comp_sums = defaultdict(float)
    for r in rows:
        for k, v in (r.get("component_scores") or {}).items():
            comp_sums[k] += float(v)
    n = max(len(rows), 1)
    component_avg = {k: round(100.0 * (comp_sums[k] / n), 2) for k in WEIGHTS}
    overall_weighted = round(sum(WEIGHTS[k] * component_avg[k] for k in WEIGHTS), 2)

    hallucinations = sum(1 for r in rows if r.get("hallucination"))
    reco_leaks = sum(1 for r in rows if not r.get("no_recommendation_leakage"))
    memory_leaks = sum(1 for r in rows if not r.get("no_memory_leakage"))
    planner_ok = sum(1 for r in rows if r.get("planner_module_ok"))
    planner_pct = round(100.0 * planner_ok / n, 2)

    hard_gates = {
        "pass_rate_ge_95": rate >= GATE_PCT,
        "hallucinations_zero": hallucinations == 0,
        "recommendation_leakage_zero": reco_leaks == 0,
        "research_memory_leakage_zero": memory_leaks == 0,
        "planner_accuracy_100": planner_pct >= 100.0,
    }
    decision = "PASS" if all(hard_gates.values()) else "FAIL"

    report = {
        "suite": "Research Intelligence Acceptance Test v1.0",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "version": h.get("version"),
        "ask_wired": bool(h.get("ask_wired")),
        "recommendation_policy": h.get("recommendation_policy"),
        "knowledge_authority": h.get("knowledge_authority"),
        "total": len(rows),
        "passed": passed,
        "pass_rate_pct": rate,
        "gate_pct": GATE_PCT,
        "overall_weighted_score_pct": overall_weighted,
        "scoring_weights": WEIGHTS,
        "component_scores_pct": component_avg,
        "hallucinations": hallucinations,
        "recommendation_leakage": reco_leaks,
        "research_memory_leakage": memory_leaks,
        "planner_accuracy_pct": planner_pct,
        "hard_gates": hard_gates,
        "by_section": {
            k: {**v, "pass_rate_pct": round(100.0 * v["passed"] / v["count"], 2)}
            for k, v in by_section.items()
        },
        "release_decision": decision,
        "questions": rows,
    }

    out_dirs = [Path("/workspace/artifacts"), Path("/opt/cursor/artifacts")]
    for out in out_dirs:
        try:
            out.mkdir(parents=True, exist_ok=True)
            (out / "research_intelligence_acceptance_v1.json").write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )
        except OSError:
            pass

    print(
        f"\n[ri_acceptance_v1] {passed}/{len(rows)} ({rate}%) "
        f"weighted={overall_weighted}% decision={decision}",
        flush=True,
    )
    print(
        f"  hallucinations={hallucinations} reco_leaks={reco_leaks} "
        f"memory_leaks={memory_leaks} planner={planner_pct}%",
        flush=True,
    )
    for k, v in report["by_section"].items():
        print(f"  {k}: {v['passed']}/{v['count']} ({v['pass_rate_pct']}%)", flush=True)
    for name, ok in hard_gates.items():
        print(f"  gate {name}: {'OK' if ok else 'FAIL'}", flush=True)

    fails = [r for r in rows if not r["pass"]]
    if fails:
        print("\nFailures:", flush=True)
        for r in fails[:60]:
            print(
                f"  {r['id']} [{r['section']}] failed={r['failed_assertions']} "
                f":: {r['prompt'][:60]}",
                flush=True,
            )
            print(f"    summary={r['summary'][:160]}", flush=True)
    return 0 if decision == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
