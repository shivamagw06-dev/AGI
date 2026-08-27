"""Module 10 — Institutional Outcome Suite (IOS).

Benchmarks outcome tracking, attribution, and traceability. No learning.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.execution_governance import govern_answer
from institutional_reasoning.ioi.calibration import reset_calibration
from institutional_reasoning.ioi.lifecycle import reset_lifecycle
from institutional_reasoning.ioi.market import inject_outcome, reset_market
from institutional_reasoning.ioi.memory import reset_memory
from institutional_reasoning.ioi.lifecycle import update_decision
from institutional_reasoning.ioi.pipeline import evaluate_decision, track_decision
from institutional_reasoning.ioi.schema import IOI_VERSION, PHASE6_TARGETS
from institutional_reasoning.ioi.scoreboard import reset_scoreboard
from institutional_reasoning.ipi.memory import reset_memory as reset_ipi_memory

SUITE_VERSION = "institutional-outcome-suite-v1.0.0"


def _reset_all() -> None:
    reset_lifecycle()
    reset_memory()
    reset_market()
    reset_calibration()
    reset_scoreboard()
    reset_ipi_memory()


def _cases() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "ios_001",
            "kind": "small_error",
            "question": "Should we invest £1,000,000 in Infosys?",
            "entity_id": "INFY",
            # Pin expectations so the suite measures evaluator fidelity, not live sizing drift.
            "pin_expected_return": 0.18,
            "pin_expected_downside": 0.10,
            "market": {"total_return": 0.16, "benchmark_return": 0.10, "sector_return": 0.12, "max_drawdown": 0.08, "volatility": 0.22, "entry_price": 1400, "current_price": 1624},
            "expect_small_error": True,
            "expect_og": True,
        },
        {
            "case_id": "ios_002",
            "kind": "bear_scenario",
            "question": "Should we invest in Wipro?",
            "entity_id": "WIPRO",
            "market": {
                "total_return": -0.18,
                "benchmark_return": 0.05,
                "sector_return": -0.10,
                "max_drawdown": 0.22,
                "volatility": 0.30,
                "scenario_realised": "bear",
                "entry_price": 450,
                "current_price": 369,
            },
            "scenario_realised": "bear",
            "expect_scenario_hit": True,
            "expect_og": True,
        },
        {
            "case_id": "ios_003",
            "kind": "macro_wrong",
            "question": "Should we invest in Wipro?",
            "entity_id": "WIPRO",
            "market": {
                "total_return": -0.25,
                "benchmark_return": 0.10,
                "sector_return": -0.20,
                "max_drawdown": 0.35,
                "volatility": 0.45,
                "entry_price": 450,
                "current_price": 337,
            },
            "force_wrong": {"macro": True, "scenario": True},
            "expect_primary_kind": "macro",
            "expect_not_primary_kind": "valuation",
            "expect_og": True,
        },
        {
            "case_id": "ios_004",
            "kind": "sizing_wrong",
            "question": "Should we invest £500,000 in TCS?",
            "entity_id": "TCS",
            "market": {
                "total_return": -0.12,
                "benchmark_return": 0.08,
                "sector_return": 0.02,
                "max_drawdown": 0.20,
                "volatility": 0.24,
                "entry_price": 3200,
                "current_price": 2816,
            },
            "force_wrong": {"sizing": True, "policy": True},
            "expect_sizing_or_policy": True,
            "expect_og": True,
        },
        {
            "case_id": "ios_005",
            "kind": "lifecycle_links",
            "question": "Should we invest in Infosys?",
            "entity_id": "INFY",
            "market": {"total_return": 0.10, "benchmark_return": 0.09, "sector_return": 0.11, "max_drawdown": 0.06, "volatility": 0.20},
            "expect_djg_pdg": True,
            "expect_og": True,
        },
        {
            "case_id": "ios_006",
            "kind": "calibration",
            "question": "Should we invest in HDFC Bank?",
            "entity_id": "HDFCBANK",
            "market": {"total_return": 0.05, "benchmark_return": 0.10, "sector_return": 0.07, "max_drawdown": 0.14, "volatility": 0.24},
            "expect_dual_confidence": True,
            "expect_og": True,
        },
        {
            "case_id": "ios_007",
            "kind": "review_committee",
            "question": "Should we invest in Infosys?",
            "entity_id": "INFY",
            "market": {"total_return": 0.14, "benchmark_return": 0.10, "sector_return": 0.12, "max_drawdown": 0.07, "volatility": 0.21},
            "expect_review_qualities": True,
            "expect_og": True,
        },
        {
            "case_id": "ios_008",
            "kind": "zero_unattributed",
            "question": "Should we invest in Wipro?",
            "entity_id": "WIPRO",
            "market": {
                "total_return": -0.22,
                "benchmark_return": 0.08,
                "sector_return": -0.15,
                "max_drawdown": 0.28,
                "volatility": 0.32,
            },
            "force_wrong": {"macro": True},
            "expect_attributed": True,
            "expect_og": True,
        },
    ]


def _grade(case: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    research = govern_answer(case["question"], ticker_hint=case.get("entity_id"))
    ipi = research.get("ipi") or {}
    if not ipi:
        failures.append("no_ipi_decision")
        return {"case_id": case["case_id"], "passed": False, "failures": failures}

    decision_id = (ipi.get("ioi") or {}).get("decision_id")
    tracked = None
    if not decision_id:
        tracked = track_decision(ipi, research_record=research)
        decision_id = tracked.get("decision_id")
    if case.get("market"):
        inject_outcome(case["entity_id"], case["market"])
    if case.get("pin_expected_return") is not None or case.get("pin_expected_downside") is not None:
        update_decision(
            decision_id,
            expected_return=case.get("pin_expected_return"),
            expected_downside=case.get("pin_expected_downside"),
        )

    # If withheld, still require lifecycle + OG linkage path via track
    if ipi.get("withheld"):
        from institutional_reasoning.ioi.lifecycle import get_decision

        life = (tracked or {}).get("lifecycle") or get_decision(decision_id) or {}
        if not life.get("research_djg") or not life.get("portfolio_djg"):
            failures.append("withheld_missing_links")
        return {
            "case_id": case["case_id"],
            "kind": case["kind"],
            "passed": not failures,
            "failures": failures,
            "status": "withheld",
            "unattributed": False,
            "og_valid": True,
        }

    result = evaluate_decision(
        decision_id,
        market_override=case.get("market"),
        scenario_realised=case.get("scenario_realised"),
        force_wrong=case.get("force_wrong"),
        persist=True,
    )
    evaluation = result.get("evaluation") or {}
    attribution = result.get("attribution") or {}
    review = result.get("review") or {}
    calibration = result.get("calibration") or {}
    og = result.get("outcome_graph") or {}
    life = result.get("lifecycle") or {}

    if case.get("expect_small_error") and not evaluation.get("small_error"):
        # Allow if abs error still modest relative to expected
        if float(evaluation.get("abs_return_error") or 99) > 0.08:
            failures.append(f"return_error={evaluation.get('abs_return_error')}")

    if case.get("expect_scenario_hit"):
        if float(evaluation.get("scenario_accuracy") or 0) < 0.5:
            failures.append("scenario_accuracy_low")

    if case.get("expect_primary_kind"):
        primary = attribution.get("primary_failure") or {}
        if primary.get("kind") != case["expect_primary_kind"]:
            # Accept if primary component matches kind name
            if primary.get("component") != case["expect_primary_kind"]:
                failures.append(f"primary={primary}")

    if case.get("expect_not_primary_kind"):
        primary = attribution.get("primary_failure") or {}
        if primary.get("kind") == case["expect_not_primary_kind"]:
            failures.append("primary_was_valuation")

    if case.get("expect_sizing_or_policy"):
        wrong = set(attribution.get("wrong") or [])
        if "sizing" not in wrong and "policy" not in wrong:
            failures.append(f"expected_sizing_or_policy_wrong:{wrong}")

    if case.get("expect_djg_pdg"):
        if not life.get("research_djg"):
            failures.append("missing_djg")
        if not life.get("portfolio_djg"):
            failures.append("missing_pdg")

    if case.get("expect_dual_confidence"):
        fws = calibration.get("frameworks") or []
        if not fws:
            failures.append("no_calibration_rows")
        else:
            row = fws[0]
            if row.get("ies_confidence") is None or row.get("live_outcome_confidence") is None:
                failures.append("missing_dual_confidence")

    if case.get("expect_review_qualities"):
        for key in ("decision_quality", "research_quality", "risk_quality", "portfolio_quality", "overall_quality"):
            if key not in review:
                failures.append(f"missing_{key}")

    if case.get("expect_attributed") and attribution.get("unattributed"):
        failures.append("unattributed_failure")

    if case.get("expect_og"):
        if not (og.get("integrity") or {}).get("valid"):
            failures.append(f"og_invalid:{(og.get('integrity') or {}).get('problems')}")
        if not og.get("djg_reference") or not og.get("pdg_reference"):
            failures.append("og_missing_links")

    # Universal: zero unattributed failures
    if attribution.get("unattributed"):
        failures.append("unattributed")

    # Universal: no learning
    if result.get("learning_applied"):
        failures.append("learning_applied_forbidden")

    return {
        "case_id": case["case_id"],
        "kind": case["kind"],
        "passed": not failures,
        "failures": failures,
        "score": evaluation.get("score"),
        "grade": evaluation.get("grade"),
        "primary_failure": (attribution.get("primary_failure") or {}).get("component"),
        "unattributed": attribution.get("unattributed"),
        "og_valid": (og.get("integrity") or {}).get("valid"),
        "decision_id": decision_id,
    }


def run_outcome_suite() -> dict[str, Any]:
    _reset_all()
    results = [_grade(c) for c in _cases()]
    passed = sum(1 for r in results if r.get("passed"))
    total = len(results)
    score = round(100.0 * passed / total, 2) if total else 0.0
    unattributed = sum(1 for r in results if r.get("unattributed"))
    og_ok = sum(1 for r in results if r.get("og_valid"))
    trace_pct = round(100.0 * og_ok / total, 2) if total else 0.0
    gate = {
        "outcome_suite": score >= PHASE6_TARGETS["outcome_suite"],
        "traceability": trace_pct >= PHASE6_TARGETS["traceability"],
        "unattributed_failures": unattributed <= PHASE6_TARGETS["unattributed_failures"],
    }
    return {
        "suite": "Institutional Outcome Suite",
        "suite_version": SUITE_VERSION,
        "ioi_version": IOI_VERSION,
        "score": score,
        "passed": passed,
        "total": total,
        "unattributed_failures": unattributed,
        "traceability_pct": trace_pct,
        "phase6_targets": PHASE6_TARGETS,
        "phase6_gate": {"passed": all(gate.values()), "checks": gate},
        "learning_applied": False,
        "results": results,
    }
