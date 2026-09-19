"""Learning hooks — every outcome feeds ILM / forecast / committee / analyst / portfolio calibration."""

from __future__ import annotations

from typing import Any


def build_learning_hooks(
    *,
    ticker: str,
    gate: dict[str, Any],
    confidence: dict[str, Any],
    inputs: dict[str, Any],
) -> dict[str, Any]:
    summary = inputs.get("stack_summary") or {}
    return {
        "ticker": (ticker or "").upper(),
        "hooks": [
            {
                "target": "ILM",
                "action": "append_decision_outcome_when_resolved",
                "status": "armed",
            },
            {
                "target": "FIE",
                "action": "calibrate_scenario_probabilities_vs_realised",
                "baseline_most_likely": summary.get("forecast_most_likely"),
                "status": "armed",
            },
            {
                "target": "Investment Committee",
                "action": "calibrate_consensus_and_minority_accuracy",
                "status": "armed",
            },
            {
                "target": "Institutional Analysts",
                "action": "update_desk_accuracy_scores",
                "status": "armed",
            },
            {
                "target": "Portfolio Intelligence",
                "action": "update_portfolio_decision_accuracy",
                "baseline_net_effect": summary.get("portfolio_net_effect"),
                "status": "armed",
            },
            {
                "target": "IDE_V2",
                "action": "update_decision_quality_vs_gate_status",
                "gate_status": gate.get("status"),
                "confidence": confidence.get("confidence"),
                "status": "armed",
            },
        ],
        "rule": "Every outcome feeds ILM, forecast calibration, committee/analyst/portfolio accuracy, decision quality",
        "soft_only": True,
        "no_ilm_redesign": True,
    }
