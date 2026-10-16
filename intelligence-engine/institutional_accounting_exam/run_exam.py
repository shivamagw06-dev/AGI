#!/usr/bin/env python3
"""Run the AGI Institutional Accounting & Financial Analysis Exam
(Level 1) — the Phase 1/2 → Phase 3 release gate.

Usage:
    cd intelligence-engine
    python3 -m institutional_accounting_exam.run_exam
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from institutional_accounting_exam.all_items import ALL_EXAM_ITEMS
from institutional_accounting_exam.grader import grade_exam
from institutional_accounting_exam.schema import EXAM_VERSION, PASSING_SCORE, RELEASE_GATE


def _artifacts_dir() -> Path:
    opt = Path("/opt/cursor/artifacts")
    if opt.is_dir():
        return opt
    return Path("/workspace/artifacts")


def main() -> int:
    print(f"[exam] {EXAM_VERSION} — {len(ALL_EXAM_ITEMS)} items", flush=True)
    report = grade_exam(ALL_EXAM_ITEMS)

    print("\n=== PER-ITEM RESULTS ===", flush=True)
    for r in report.item_results:
        flags = []
        if r.accounting_score >= 0 and r.accounting_score < 1.0:
            flags.append(f"accounting={r.accounting_score:.2f}")
        if r.linkage_score >= 0 and r.linkage_score < 1.0:
            flags.append(f"linkage={r.linkage_score:.2f}")
        if r.interpretation_score >= 0 and r.interpretation_score < 0.6:
            flags.append(f"interpretation={r.interpretation_score:.2f}")
        if not r.causal_score:
            flags.append("no_causal_reasoning")
        if r.hallucinated:
            flags.append("HALLUCINATION")
        status = "OK" if not flags else "WEAK: " + ", ".join(flags)
        print(f"  [{r.item.section}] {r.item.id:5s} {status}", flush=True)

    print("\n=== DIMENSION SCORES ===", flush=True)
    for k, v in report.dimension_scores.items():
        print(f"  {k}: {v}", flush=True)

    print(f"\nOVERALL SCORE: {report.overall_score * 100:.1f}%  (passing = {PASSING_SCORE * 100:.0f}%)", flush=True)
    print("\n=== RELEASE GATE ===", flush=True)
    for k, v in report.release_gate.items():
        print(f"  {k}: {v}", flush=True)
    print(f"\nRELEASE DECISION: {'PASS — proceed to Phase 3' if report.passed else 'FAIL — remain in Phase 1/2 remediation'}", flush=True)

    out: dict[str, Any] = {
        "exam_version": EXAM_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total_items": len(ALL_EXAM_ITEMS),
        "dimension_scores": report.dimension_scores,
        "overall_score": report.overall_score,
        "passing_score": PASSING_SCORE,
        "release_gate": report.release_gate,
        "release_gate_spec": RELEASE_GATE,
        "passed": report.passed,
        "items": [
            {
                "id": r.item.id,
                "section": r.item.section,
                "prompt": r.item.prompt,
                "answer": r.answer.answer_text,
                "accounting_score": r.accounting_score,
                "linkage_score": r.linkage_score,
                "interpretation_score": r.interpretation_score,
                "causal_reasoning_present": bool(r.causal_score),
                "hallucination_detected": r.hallucinated,
                "admits_uncertainty_correctly": r.answer.admits_uncertainty_correctly,
            }
            for r in report.item_results
        ],
    }
    out_dir = _artifacts_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"institutional_accounting_exam_{stamp}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")
    try:
        ws = Path("/workspace/artifacts")
        ws.mkdir(parents=True, exist_ok=True)
        (ws / path.name).write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")
        (ws / "institutional_accounting_exam_latest.json").write_text(
            json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8"
        )
    except Exception:
        pass
    print(f"\n[exam] wrote {path}", flush=True)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
