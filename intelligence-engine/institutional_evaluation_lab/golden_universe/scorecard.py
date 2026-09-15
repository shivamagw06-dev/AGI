"""Release scorecard — publishable summary after a golden evaluation run."""

from __future__ import annotations

from typing import Any

from institutional_evaluation_lab.golden_universe.schema import GOLDEN_EVAL_VERSION, SUITE_ID


def release_scorecard(run_summary: dict[str, Any]) -> dict[str, Any]:
    cov = run_summary.get("coverage") or {}
    sector = run_summary.get("sector") or {}
    qa = run_summary.get("qa") or {}
    drift = run_summary.get("drift") or {}
    unexpected = int(drift.get("unexpected_count") or 0)
    qa_fail = int(qa.get("failed") or 0)

    # Simple release health: green / amber / red
    gate_pass = float(cov.get("gate_pass_rate_pct") or 0)
    if unexpected > 5 or qa_fail > 10 or gate_pass < 50:
        health = "red"
    elif unexpected > 0 or qa_fail > 0 or gate_pass < 75:
        health = "amber"
    else:
        health = "green"

    return {
        "suite": SUITE_ID,
        "version": GOLDEN_EVAL_VERSION,
        "run_id": run_summary.get("run_id"),
        "release_id": run_summary.get("release_id"),
        "commit": run_summary.get("commit"),
        "health": health,
        "companies": cov.get("companies") or run_summary.get("n"),
        "average_readiness_pct": cov.get("average_readiness_pct"),
        "average_runtime_s": cov.get("average_runtime_s"),
        "gate_pass_rate_pct": cov.get("gate_pass_rate_pct"),
        "gate_fail_rate_pct": cov.get("gate_fail_rate_pct"),
        "evidence_coverage": cov.get("evidence_coverage"),
        "qa_pass_pct": qa.get("pass_pct"),
        "qa_violations": qa.get("by_rule") or {},
        "drift_changed": drift.get("changed"),
        "drift_unexpected": unexpected,
        "sector_count": sector.get("sector_count"),
        "top_weak_sectors": [
            s
            for s in (sector.get("sectors") or [])
            if (s.get("gate_pass_pct") or 100) < 80
        ][:8],
        "flags": {
            "investigate_unexpected_drift": unexpected > 0,
            "investigate_qa_failures": qa_fail > 0,
            "ingestion_gap": (cov.get("evidence_coverage") or {}).get("Insufficient", 0) > 0,
        },
        "note": "Release scorecard for statistical evaluation of AGIB changes over the golden universe.",
    }
