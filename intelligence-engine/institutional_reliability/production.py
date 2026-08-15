"""Authoritative acceptance board for the four-stage reliability roadmap."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any


def _gate_counts(evidence: dict[str, dict[str, dict[str, Any]]], gate: str) -> dict[str, int]:
    return dict(sorted(Counter(
        str(strategy.get(gate, {}).get("status") or "MISSING").upper()
        for strategy in evidence.values()
    ).items()))


def roadmap_status() -> dict[str, Any]:
    """Evaluate every phase from its owning engine; missing evidence fails closed."""
    from forecast_intelligence_engine import calibration_board
    from portfolio_intelligence.production import quality_gates, strategy_execution_gate
    from strategy_lab.paper import board as paper_board
    from strategy_lab.production import REGISTRY
    from strategy_lab.registry_store import load_latest_evidence
    from strategy_lab.validation_registry import evaluate

    evidence = load_latest_evidence(force=True)
    decisions = {
        key: evaluate(key, requested_lifecycle="PRODUCTION", evidence=evidence.get(key, {}))
        for key in REGISTRY
    }
    required_data_gates = ("data_freshness", "data_completeness", "point_in_time", "corporate_actions")
    normalised_evidence = {key: decision["evidence"] for key, decision in decisions.items()}
    data_gate_counts = {gate: _gate_counts(normalised_evidence, gate) for gate in required_data_gates}
    phase_1_pass = bool(REGISTRY) and all(
        all(decision["evidence"][gate]["status"] == "PASSED" for gate in required_data_gates)
        for decision in decisions.values()
    )

    lifecycle_counts = dict(sorted(Counter(
        decision.get("supported_lifecycle", "EXPERIMENTAL") for decision in decisions.values()
    ).items()))
    validated = {"RESEARCH_VALIDATED", "INVESTMENT_VALIDATED", "PRODUCTION_CANDIDATE", "PRODUCTION"}
    phase_2_pass = bool(decisions) and all(
        decision.get("supported_lifecycle") in validated for decision in decisions.values()
    )
    paper = paper_board()

    calibration = calibration_board()
    phase_3_pass = calibration.get("status") == "RESEARCH_CALIBRATED"

    portfolio_checks = quality_gates()
    strategy_gates = {key: strategy_execution_gate(key) for key in REGISTRY}
    execution_allowed = [key for key, gate in strategy_gates.items() if gate.get("execution_eligible")]
    phase_4_pass = bool(portfolio_checks.get("passed")) and bool(execution_allowed)

    phases = {
        "phase_1_data_integrity": {
            "status": "ACCEPTED" if phase_1_pass else "IN_PROGRESS",
            "accepted": phase_1_pass,
            "strategy_count": len(REGISTRY),
            "gate_counts": data_gate_counts,
            "remaining": [gate for gate, counts in data_gate_counts.items()
                          if counts.get("PASSED", 0) != len(REGISTRY)],
        },
        "phase_2_validation": {
            "status": "ACCEPTED" if phase_2_pass else "IN_PROGRESS",
            "accepted": phase_2_pass,
            "supported_lifecycle_counts": lifecycle_counts,
            "research_validated_or_better": sum(
                count for lifecycle, count in lifecycle_counts.items() if lifecycle in validated
            ),
            "strategy_count": len(REGISTRY),
            "forward_paper_validation": paper,
        },
        "phase_3_forecast_intelligence": {
            "status": "ACCEPTED" if phase_3_pass else "ACCUMULATING_OUTCOMES",
            "accepted": phase_3_pass,
            "calibration": calibration,
        },
        "phase_4_portfolio_intelligence": {
            "status": "ACCEPTED" if phase_4_pass else "GOVERNED_BLOCKED",
            "accepted": phase_4_pass,
            "portfolio_quality_gates": portfolio_checks,
            "execution_eligible_strategies": execution_allowed,
            "strategy_gates": strategy_gates,
        },
    }
    all_accepted = all(phase["accepted"] for phase in phases.values())
    return {
        "ok": True,
        "authority": "AGI_INSTITUTIONAL_RELIABILITY_BOARD",
        "version": "1.0.0",
        "status": "ACCEPTED" if all_accepted else "IN_PROGRESS",
        "execution_eligible": all_accepted and bool(execution_allowed),
        "phases": phases,
        "accepted_phases": sum(bool(phase["accepted"]) for phase in phases.values()),
        "total_phases": len(phases),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "rule": "No model, scanner, forecast, or portfolio component may self-certify or bypass a failed phase.",
    }
