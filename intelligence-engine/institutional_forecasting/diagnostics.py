"""FG-01 diagnostics and quality gates."""

from __future__ import annotations

from typing import Any, Iterable, List, Sequence

from institutional_forecasting.probability import validate_probability
from institutional_forecasting.scenario import ForecastScenario
from institutional_forecasting.schema import FG_VERSION, FG_WORKSTREAM_ID


def quality_gates(scenario: ForecastScenario) -> tuple[dict[str, bool], list[str]]:
    errors: list[str] = []
    if not scenario.assumptions:
        errors.append("scenario without assumptions")
    if not scenario.propagated_impacts and not scenario.changed_nodes:
        errors.append("scenario without propagation")
    errors.extend(validate_probability(scenario.probability))
    if scenario.probability is None:
        errors.append("scenario without probability")
    if not scenario.resulting_decision:
        errors.append("scenario without decision")
    if not scenario.diagnostics:
        errors.append("scenario without diagnostics")

    gates = {
        "has_assumptions": bool(scenario.assumptions),
        "has_propagation": bool(scenario.propagated_impacts or scenario.changed_nodes),
        "has_probability": scenario.probability is not None
        and 0.0 <= float(scenario.probability) <= 1.0,
        "has_decision": bool(scenario.resulting_decision),
        "has_diagnostics": bool(scenario.diagnostics),
        "lineage_complete": bool(scenario.lineage) and len(scenario.lineage) >= 6,
    }
    for key, ok in gates.items():
        if not ok and not any(key.replace("has_", "scenario without ") in e for e in errors):
            # already covered above for most
            pass
    return gates, errors


def build_diagnostics(
    scenarios: Sequence[ForecastScenario],
    *,
    ticker: str = "",
) -> dict[str, Any]:
    rows = list(scenarios or [])
    decision_changes = sum(1 for s in rows if s.decision_changed)
    conf_changes = [s.confidence_delta for s in rows]
    probs = {s.scenario_name: s.probability for s in rows}
    prop_times = [float((s.diagnostics or {}).get("propagation_time_ms") or 0.0) for s in rows]
    affected = [int((s.diagnostics or {}).get("affected_nodes") or 0) for s in rows]
    gates_all = [quality_gates(s)[0] for s in rows]
    return {
        "workstream_id": FG_WORKSTREAM_ID,
        "version": FG_VERSION,
        "ticker": ticker,
        "scenario_count": len(rows),
        "propagation_time_ms_avg": round(sum(prop_times) / len(prop_times), 4) if prop_times else 0.0,
        "propagation_time_ms_max": round(max(prop_times), 4) if prop_times else 0.0,
        "affected_nodes_avg": round(sum(affected) / len(affected), 4) if affected else 0.0,
        "decision_changes": decision_changes,
        "confidence_changes": conf_changes,
        "probability_distribution": probs,
        "quality_gates": gates_all,
        "quality_gate_pass": all(all(g.values()) for g in gates_all) if gates_all else False,
        "llm": False,
    }


def validate_scenario(scenario: ForecastScenario) -> list[str]:
    _, errors = quality_gates(scenario)
    return errors
