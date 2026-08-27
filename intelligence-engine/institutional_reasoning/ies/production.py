"""IES runner — execute suites and emit benchmark report."""

from __future__ import annotations

from typing import Any

from institutional_reasoning.ies.banks import all_banks, all_cases
from institutional_reasoning.ies.grader import grade_case
from institutional_reasoning.ies.metrics import aggregate, render_dashboard
from institutional_reasoning.ies.schema import IES_VERSION, MODULE_CODE, PROGRAMME, SUITES


def inventory() -> dict[str, Any]:
    banks = all_banks()
    counts = {s: len(banks[s]) for s in SUITES}
    return {
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": IES_VERSION,
        "suites": list(SUITES),
        "counts": counts,
        "total": sum(counts.values()),
    }


def run_ies(
    *,
    suites: list[str] | None = None,
    limit_per_suite: int | None = None,
    case_ids: list[str] | None = None,
) -> dict[str, Any]:
    selected = list(suites) if suites else list(SUITES)
    cases = []
    banks = all_banks()
    for s in selected:
        rows = banks.get(s) or []
        if limit_per_suite is not None:
            rows = rows[:limit_per_suite]
        cases.extend(rows)
    if case_ids:
        want = set(case_ids)
        cases = [c for c in cases if c.case_id in want]

    results = [grade_case(c) for c in cases]
    metrics = aggregate(results)
    failures = [r for r in results if not r.get("passed")]
    return {
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": IES_VERSION,
        "inventory": inventory(),
        "n": len(results),
        "passed": sum(1 for r in results if r.get("passed")),
        "failed": len(failures),
        "metrics": metrics,
        "dashboard_text": render_dashboard(metrics, version=IES_VERSION),
        "failures": failures[:50],
        "results": results,
    }


def dashboard(*, limit_per_suite: int | None = None, suites: list[str] | None = None) -> dict[str, Any]:
    report = run_ies(limit_per_suite=limit_per_suite, suites=suites)
    m = report["metrics"]
    return {
        "module": MODULE_CODE,
        "version": IES_VERSION,
        "overall_score": m.get("overall_score"),
        "suite_scores": m.get("suite_scores"),
        "framework_execution": (m.get("framework") or {}).get("execution_rate_pct"),
        "evidence_coverage": round(((m.get("evidence") or {}).get("avg_coverage") or 0) * 100, 1),
        "editorial_violations": (m.get("governance") or {}).get("editorial_violations"),
        "unsupported_conclusions": (m.get("governance") or {}).get("unsupported_conclusions"),
        "false_positives": (m.get("errors") or {}).get("false_positives_pct"),
        "false_negatives": (m.get("errors") or {}).get("false_negatives_pct"),
        "average_evidence_quality": (m.get("evidence") or {}).get("avg_quality"),
        "average_latency_sec": (m.get("performance") or {}).get("avg_latency_sec"),
        "phase2_gate": m.get("phase2_gate"),
        "dashboard_text": report["dashboard_text"],
        "n": report["n"],
        "failed": report["failed"],
    }


def quality_gates(*, full: bool = False, limit_per_suite: int | None = 20) -> dict[str, Any]:
    """CI gate. full=True runs all 700 cases; default samples 20/suite for speed."""
    limit = None if full else limit_per_suite
    report = run_ies(limit_per_suite=limit)
    gate = (report.get("metrics") or {}).get("phase2_gate") or {}
    inv = inventory()
    return {
        "gate": "INSTITUTIONAL_EVALUATION_SUITE",
        "version": IES_VERSION,
        "full": full,
        "inventory_ok": inv["total"] >= 700 and all(inv["counts"].get(s, 0) >= 100 for s in SUITES),
        "passed": bool(gate.get("passed")) and inv["total"] >= 700,
        "phase2_gate": gate,
        "overall_score": (report.get("metrics") or {}).get("overall_score"),
        "n": report.get("n"),
        "failed_checks": gate.get("failed") or [],
        "sample_failures": (report.get("failures") or [])[:10],
    }
