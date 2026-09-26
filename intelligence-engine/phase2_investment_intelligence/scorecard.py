"""Phase 2 Intelligence Scorecard — measures intelligence quality (not governance)."""

from __future__ import annotations

from typing import Any

from phase2_investment_intelligence.contract import ENGINE_CONTRACTS

# Targets from the Phase 2 programme (intelligence measurement).
SCORECARD_TARGETS = {
    "coverage_pct_min": 95.0,
    "confidence_reported": True,
    "explainability_present": True,
    "iat_regressions_max": 0,
    "unknown_drift_max": 0,
    # Freshness / runtime budgets come from ENGINE_CONTRACTS per workstream
}

DEFINITION_OF_DONE = (
    "architecture_implemented_standard_contract",
    "unit_and_integration_tests_passing",
    "evaluation_lab_integrated",
    "no_governance_regressions",
    "unknown_drift_zero",
    "iat_still_passes",
    "demonstrable_improvement_on_one_intelligence_metric",
)


def scorecard_template(engine_code: str) -> dict[str, Any]:
    """Empty scorecard row for a workstream — filled by Evaluation Lab after runs."""
    meta = ENGINE_CONTRACTS[engine_code]
    return {
        "workstream_id": meta["id"],
        "engine": engine_code,
        "engine_name": meta["engine_name"],
        "metrics": {
            "coverage_pct": None,
            "freshness_within_sla_pct": None,
            "freshness_sla_days": meta["freshness_sla_days"],
            "confidence_reported_pct": None,
            "explainability_present_pct": None,
            "iat_regressions": None,
            "unknown_drift": None,
            "average_runtime_s": None,
            "runtime_budget_s": meta["runtime_budget_s"],
        },
        "targets": {
            **SCORECARD_TARGETS,
            "freshness_sla_days": meta["freshness_sla_days"],
            "runtime_budget_s": meta["runtime_budget_s"],
        },
        "definition_of_done": list(DEFINITION_OF_DONE),
        "dod_status": {k: "pending" for k in DEFINITION_OF_DONE},
        "complete": False,
    }


def programme_scorecard_board() -> dict[str, Any]:
    rows = [scorecard_template(code) for code in ENGINE_CONTRACTS]
    return {
        "kind": "phase2_intelligence_scorecard",
        "note": (
            "Phase 1 measured governance. Phase 2 measures intelligence "
            "while re-checking IAT PASS and UNKNOWN drift = 0."
        ),
        "targets": dict(SCORECARD_TARGETS),
        "definition_of_done": list(DEFINITION_OF_DONE),
        "workstreams": rows,
        "n": len(rows),
    }


def evaluate_scorecard_row(row: dict[str, Any]) -> dict[str, Any]:
    """Mark metric pass/fail against targets (values must already be filled)."""
    m = row.get("metrics") or {}
    t = row.get("targets") or SCORECARD_TARGETS
    checks = {
        "coverage": (m.get("coverage_pct") or 0) >= float(t.get("coverage_pct_min") or 95),
        "freshness": (m.get("freshness_within_sla_pct") or 0) >= float(t.get("coverage_pct_min") or 95),
        "confidence_reported": (m.get("confidence_reported_pct") or 0) >= 100.0
        if t.get("confidence_reported")
        else True,
        "explainability": (m.get("explainability_present_pct") or 0) >= 95.0
        if t.get("explainability_present")
        else True,
        "iat_regressions": int(m.get("iat_regressions") or 0) <= int(t.get("iat_regressions_max") or 0),
        "unknown_drift": int(m.get("unknown_drift") or 0) <= int(t.get("unknown_drift_max") or 0),
        "runtime": (
            m.get("average_runtime_s") is None
            or float(m["average_runtime_s"]) <= float(t.get("runtime_budget_s") or 99)
        ),
    }
    return {
        **row,
        "checks": checks,
        "metrics_pass": all(checks.values()),
    }
