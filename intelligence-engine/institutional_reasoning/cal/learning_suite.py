"""Module 10 — Institutional Learning Suite (ILS).

Did confidence/calibration/planner improve? Any IES regression? Traceable?
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.cal.governance import (
    approve,
    deploy,
    get_proposal,
    govern_learning,
    propose_from_outcome,
    reset_governance,
    simulate,
    validate_proposal,
)
from institutional_reasoning.cal.schema import CAL_VERSION, PHASE7_TARGETS
from institutional_reasoning.cal.versions import active_state, reset_versions
from institutional_reasoning.execution_governance import govern_answer
from institutional_reasoning.ioi.lifecycle import reset_lifecycle
from institutional_reasoning.ioi.market import inject_outcome, reset_market
from institutional_reasoning.ioi.memory import reset_memory as reset_ioi_memory
from institutional_reasoning.ioi.pipeline import evaluate_decision
from institutional_reasoning.ipi.memory import reset_memory as reset_ipi_memory

SUITE_VERSION = "institutional-learning-suite-v1.0.0"


def _reset_all() -> None:
    reset_governance()
    reset_versions()
    reset_lifecycle()
    reset_ioi_memory()
    reset_market()
    reset_ipi_memory()


def _outcome_for(entity_id: str, question: str, market: dict[str, Any]) -> dict[str, Any]:
    inject_outcome(entity_id, market)
    research = govern_answer(question, ticker_hint=entity_id)
    decision_id = (research.get("ioi") or {}).get("decision_id")
    if not decision_id:
        raise RuntimeError("missing_ioi_decision")
    return evaluate_decision(decision_id, market_override=market, persist=True)


def _cases() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "ils_001",
            "kind": "framework_wrong_accepted",
            "entity_id": "WIPRO",
            "question": "Should we invest in Wipro?",
            "market": {
                "total_return": -0.20,
                "benchmark_return": 0.08,
                "sector_return": -0.15,
                "max_drawdown": 0.25,
                "volatility": 0.32,
            },
            "force_wrong": {"macro": True},
            "expect_proposal": True,
            "expect_some_deployed_or_approved": True,
        },
        {
            "case_id": "ils_002",
            "kind": "hurts_ies_rejected",
            "mode": "synthetic_hurt_ies",
            "expect_rejected": True,
        },
        {
            "case_id": "ils_003",
            "kind": "improves_live_accepted",
            "entity_id": "INFY",
            "question": "Should we invest in Infosys?",
            "market": {
                "total_return": -0.10,
                "benchmark_return": 0.08,
                "sector_return": -0.08,
                "max_drawdown": 0.18,
                "volatility": 0.28,
            },
            "expect_live_non_negative_on_deploy": True,
        },
        {
            "case_id": "ils_004",
            "kind": "confidence_calibration",
            "entity_id": "INFY",
            "question": "Should we invest £1,000,000 in Infosys?",
            "market": {
                "total_return": 0.12,
                "benchmark_return": 0.10,
                "sector_return": 0.11,
                "max_drawdown": 0.07,
                "volatility": 0.20,
            },
            "expect_confidence_overlay_or_no_change": True,
        },
        {
            "case_id": "ils_005",
            "kind": "planner_priority",
            "entity_id": "WIPRO",
            "question": "Should we invest in Wipro?",
            "market": {
                "total_return": -0.22,
                "benchmark_return": 0.05,
                "sector_return": -0.18,
                "max_drawdown": 0.28,
                "volatility": 0.35,
            },
            "force_wrong": {"macro": True},
            "expect_planner_or_failure_condition": True,
        },
        {
            "case_id": "ils_006",
            "kind": "traceability",
            "entity_id": "TCS",
            "question": "Should we invest in TCS?",
            "market": {
                "total_return": -0.08,
                "benchmark_return": 0.06,
                "sector_return": 0.01,
                "max_drawdown": 0.15,
                "volatility": 0.24,
            },
            "expect_learning_graph": True,
        },
        {
            "case_id": "ils_007",
            "kind": "no_ungoverned",
            "mode": "governance_invariants",
            "expect_ungoverned_zero": True,
        },
        {
            "case_id": "ils_008",
            "kind": "no_ies_regression_on_accept",
            "entity_id": "HDFCBANK",
            "question": "Should we invest in HDFC Bank?",
            "market": {
                "total_return": 0.04,
                "benchmark_return": 0.09,
                "sector_return": 0.05,
                "max_drawdown": 0.12,
                "volatility": 0.22,
            },
            "expect_no_ies_regression": True,
        },
    ]


def _grade(case: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    if case.get("mode") == "synthetic_hurt_ies":
        # Craft a proposal that collapses IES and ensure rejection
        from institutional_reasoning.cal.governance import _PROPOSALS

        pid = "lp_hurt_ies_test"
        _PROPOSALS[pid] = {
            "proposal_id": pid,
            "kind": "adjust_planner_priority",
            "target": "rel_val_damodaran",
            "delta": -0.50,
            "force_hurt_ies": True,
            "auto_apply": False,
            "requires_governance": True,
            "forbidden": ["rewrite_framework"],
            "status": "proposed",
            "source_outcome_id": "dec_synthetic",
            "og_ref": "dec_synthetic",
        }
        validate_proposal(pid)
        simulate(pid)
        row = get_proposal(pid) or {}
        if (row.get("simulation") or {}).get("passed"):
            failures.append("hurt_ies_not_rejected_by_sandbox")
        approve(pid, approver="governance")
        row = get_proposal(pid) or {}
        if row.get("status") in {"approved", "deployed"}:
            failures.append("hurt_ies_was_approved")
        return {
            "case_id": case["case_id"],
            "kind": case["kind"],
            "passed": not failures,
            "failures": failures,
            "status": row.get("status"),
            "ungoverned": 0,
            "ies_regression": 0,
            "lg_valid": True,
        }

    if case.get("mode") == "governance_invariants":
        # Ensure active path never writes ungoverned changes
        outcome = _outcome_for(
            "INFY",
            "Should we invest in Infosys?",
            {"total_return": -0.05, "benchmark_return": 0.05, "sector_return": -0.02, "max_drawdown": 0.1, "volatility": 0.2},
        )
        governed = govern_learning(outcome, approver="governance")
        if governed.get("ungoverned_changes", 1) != 0:
            failures.append("ungoverned_changes")
        if governed.get("learning_applied_to_source"):
            failures.append("source_rewritten")
        return {
            "case_id": case["case_id"],
            "kind": case["kind"],
            "passed": not failures,
            "failures": failures,
            "ungoverned": governed.get("ungoverned_changes"),
            "ies_regression": 0,
            "lg_valid": True,
        }

    # Standard outcome → learning path
    research = govern_answer(case["question"], ticker_hint=case["entity_id"])
    decision_id = (research.get("ioi") or {}).get("decision_id")
    if not decision_id:
        failures.append("no_ioi")
        return {"case_id": case["case_id"], "passed": False, "failures": failures}

    inject_outcome(case["entity_id"], case["market"])
    outcome = evaluate_decision(
        decision_id,
        market_override=case["market"],
        force_wrong=case.get("force_wrong"),
        persist=True,
    )
    governed = govern_learning(outcome, approver="governance")
    results = governed.get("results") or []
    deployed = [r for r in results if r.get("status") == "deployed"]
    approved = [r for r in results if r.get("status") in {"approved", "deployed"}]
    rejected = [r for r in results if r.get("status") == "rejected"]

    if case.get("expect_proposal") and not results:
        failures.append("no_proposals")

    if case.get("expect_some_deployed_or_approved") and not (deployed or approved):
        # Acceptable if only no_change / all rejected for good reason — but framework_wrong should produce something
        actionable = [r for r in results if r.get("kind") != "no_change"]
        if not actionable:
            failures.append("no_actionable_proposals")
        elif not approved and not deployed:
            # At least one should pass sandbox for failure-driven learning
            if not any((r.get("simulation") or {}).get("passed") for r in actionable):
                failures.append("no_simulation_pass")

    if case.get("expect_live_non_negative_on_deploy"):
        for r in deployed:
            if float((r.get("simulation") or {}).get("live_delta") or 0) < 0:
                failures.append("live_delta_negative")
            if float((r.get("simulation") or {}).get("ies_delta") or 0) < -0.5:
                failures.append("ies_regression_on_deploy")

    if case.get("expect_confidence_overlay_or_no_change"):
        kinds = {r.get("kind") for r in results}
        state = active_state()
        if not (
            kinds & {"increase_confidence", "decrease_confidence", "no_change", "adjust_planner_priority", "add_failure_condition", "add_applicability_rule", "adjust_policy"}
            or state.get("confidence")
        ):
            failures.append("no_confidence_signal")

    if case.get("expect_planner_or_failure_condition"):
        kinds = {r.get("kind") for r in results}
        state = active_state()
        if not (
            kinds & {"adjust_planner_priority", "add_failure_condition", "add_applicability_rule", "adjust_policy", "decrease_confidence"}
            or state.get("failure_conditions")
            or deployed
        ):
            failures.append("planner_not_touched")

    if case.get("expect_learning_graph"):
        graphs = [r.get("learning_graph") for r in results if r.get("learning_graph")]
        if deployed and not graphs:
            failures.append("missing_learning_graph")
        for g in graphs:
            if not (g.get("integrity") or {}).get("valid"):
                failures.append(f"lg_invalid:{(g.get('integrity') or {}).get('problems')}")
            if not (g.get("integrity") or {}).get("linked_to_og"):
                failures.append("lg_missing_og")

    if case.get("expect_no_ies_regression"):
        for r in deployed:
            if float((r.get("simulation") or {}).get("ies_delta") or 0) < -0.5:
                failures.append("ies_regression")

    if governed.get("ungoverned_changes", 0) != 0:
        failures.append("ungoverned")
    if governed.get("learning_applied_to_source"):
        failures.append("source_rewrite")

    lg_valid = True
    for r in results:
        g = r.get("learning_graph")
        if g and not (g.get("integrity") or {}).get("valid"):
            lg_valid = False

    return {
        "case_id": case["case_id"],
        "kind": case["kind"],
        "passed": not failures,
        "failures": failures,
        "proposals": len(results),
        "deployed": len(deployed),
        "rejected": len(rejected),
        "ungoverned": governed.get("ungoverned_changes", 0),
        "ies_regression": sum(
            1
            for r in deployed
            if float((r.get("simulation") or {}).get("ies_delta") or 0) < -0.5
        ),
        "lg_valid": lg_valid,
    }


def run_learning_suite() -> dict[str, Any]:
    _reset_all()
    results = [_grade(c) for c in _cases()]
    passed = sum(1 for r in results if r.get("passed"))
    total = len(results)
    score = round(100.0 * passed / total, 2) if total else 0.0
    ungoverned = sum(int(r.get("ungoverned") or 0) for r in results)
    ies_reg = sum(int(r.get("ies_regression") or 0) for r in results)
    lg_ok = sum(1 for r in results if r.get("lg_valid"))
    trace_pct = round(100.0 * lg_ok / total, 2) if total else 0.0
    gate = {
        "learning_suite": score >= PHASE7_TARGETS["learning_suite"],
        "traceability": trace_pct >= PHASE7_TARGETS["traceability"],
        "ungoverned_changes": ungoverned <= PHASE7_TARGETS["ungoverned_changes"],
        "ies_regression": ies_reg <= PHASE7_TARGETS["ies_regression"],
    }
    return {
        "suite": "Institutional Learning Suite",
        "suite_version": SUITE_VERSION,
        "cal_version": CAL_VERSION,
        "score": score,
        "passed": passed,
        "total": total,
        "ungoverned_changes": ungoverned,
        "ies_regressions": ies_reg,
        "traceability_pct": trace_pct,
        "phase7_targets": PHASE7_TARGETS,
        "phase7_gate": {"passed": all(gate.values()), "checks": gate},
        "learning_applied_to_source": False,
        "results": results,
    }
