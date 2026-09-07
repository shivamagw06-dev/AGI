"""FG-01 production façades — health / run scenarios / Mission Control."""

from __future__ import annotations

from typing import Any, Optional

from institutional_forecasting.assumptions import ScenarioAssumption, banking_preset_assumptions
from institutional_forecasting.diagnostics import validate_scenario
from institutional_forecasting.flags import flags_dict, is_enabled
from institutional_forecasting.probability import (
    normalize_probabilities,
    standard_distribution,
)
from institutional_forecasting.scenario_engine import run_scenario
from institutional_forecasting.schema import (
    DEFAULT_HORIZON,
    FG_PRODUCT,
    FG_ROLE,
    FG_SPEC,
    FG_VERSION,
    FG_WORKSTREAM_ID,
    SCENARIO_ENGINE_VERSION,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


_SCENARIOS: dict[str, list[dict[str, Any]]] = {}


def reset_for_tests() -> None:
    _SCENARIOS.clear()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": FG_WORKSTREAM_ID,
        "product": FG_PRODUCT,
        "version": FG_VERSION,
        "role": FG_ROLE,
        "llm": False,
        "ml_price_prediction": False,
        "monte_carlo": False,
        "deterministic_propagation": True,
        "scenario_engine_version": SCENARIO_ENGINE_VERSION,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": FG_SPEC,
        "brand": "AGI",
        "tickers_cached": sorted(_SCENARIOS.keys()),
        "as_of": now_iso(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    scenario_count = sum(len(v) for v in _SCENARIOS.values())
    coverage = len(_SCENARIOS)
    # Lightweight aggregates from cache
    prop_times: list[float] = []
    confidences: list[float] = []
    for rows in _SCENARIOS.values():
        for s in rows:
            diag = s.get("diagnostics") or {}
            prop_times.append(float(diag.get("propagation_time_ms") or 0.0))
            if s.get("resulting_confidence") is not None:
                confidences.append(float(s["resulting_confidence"]))
    return {
        "status": h.get("status"),
        "workstream_id": FG_WORKSTREAM_ID,
        "product": FG_PRODUCT,
        "version": FG_VERSION,
        "llm": False,
        "forecast_health": "ok" if h.get("enabled") else "disabled",
        "scenario_coverage": coverage,
        "scenario_count": scenario_count,
        "propagation_time_ms_avg": round(sum(prop_times) / len(prop_times), 4) if prop_times else None,
        "scenario_accuracy": None,  # requires ex-post outcomes — out of scope
        "forecast_confidence_avg": round(sum(confidences) / len(confidences), 2) if confidences else None,
    }


def _load_graph_and_decision(ticker: str):
    from institutional_decision import history as decision_history
    from institutional_decision.production import decide_company
    from institutional_graph.graph import build_company_graph
    from institutional_graph.impact import compute_impacts
    from institutional_graph.inference import infer
    from institutional_graph.production import _GRAPHS
    from institutional_reporting.fixtures import get_fixture
    from institutional_reporting.reason_composer import compose_reasons

    key = str(ticker or "").strip().upper()
    fixture = get_fixture(key)
    if fixture is None:
        return None, None, None, [f"no fixture for ticker {key}"]

    latest = decision_history.latest(key)
    if latest is None or not getattr(latest, "calibrated", False):
        decide_company({"ticker": key, "include_calibration": True, "include_drift": False})
        latest = decision_history.latest(key)

    if key in _GRAPHS:
        graph = _GRAPHS[key]
    else:
        reasons = compose_reasons(fixture)
        graph = build_company_graph(fixture, reasons=reasons.reasons, decision=latest)
        infer(graph)
        compute_impacts(graph, fixture)
        _GRAPHS[key] = graph
    return fixture, graph, latest, []


def run_company_scenarios(
    ticker: str,
    *,
    scenarios: Optional[list[str]] = None,
    custom_assumptions: Optional[list[dict[str, Any]]] = None,
    horizon: str = DEFAULT_HORIZON,
    include_graph: bool = False,
    include_propagation: bool = True,
    include_sensitivity: bool = True,
    probability_distribution: Optional[dict[str, float]] = None,
) -> dict[str, Any]:
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "workstream_id": FG_WORKSTREAM_ID,
            "rejected": True,
            "validation_errors": ["FG-01 disabled"],
        }

    fixture, graph, decision, errors = _load_graph_and_decision(ticker)
    if errors:
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": FG_WORKSTREAM_ID,
            "validation_errors": errors,
        }

    names = [str(s).strip().lower() for s in (scenarios or ["base", "bull", "bear", "stress"])]
    names = [n for n in names if n]
    if not names:
        names = ["base", "bull", "bear"]

    dist = (
        normalize_probabilities(probability_distribution)
        if probability_distribution
        else standard_distribution(include_stress="stress" in names, include_optimistic="optimistic" in names)
    )

    results = []
    validation_errors: list[str] = []
    for name in names:
        if name == "custom" and custom_assumptions:
            assump = tuple(ScenarioAssumption.from_dict(a) for a in custom_assumptions)
        else:
            assump = banking_preset_assumptions(name)
        scenario = run_scenario(
            graph,
            assump,
            decision=decision,
            scenario_name=name,
            horizon=horizon,
            probability_distribution=dist,
            include_sensitivity=include_sensitivity and name == names[0],
        )
        # Attach sensitivity once on first scenario; copy reference for others if needed
        errs = validate_scenario(scenario)
        if errs:
            validation_errors.extend([f"{name}: {e}" for e in errs])
        payload = scenario.to_dict()
        if not include_propagation:
            payload.pop("propagated_impacts", None)
            payload.pop("changed_nodes", None)
        if not include_graph:
            payload.pop("forecast_graph", None)
        # Only keep full sensitivity on first row to avoid bloat; others get scorecard
        if name != names[0] and payload.get("sensitivity"):
            payload["sensitivity"] = {
                "scorecard": (payload.get("sensitivity") or {}).get("scorecard") or {},
                "version": (payload.get("sensitivity") or {}).get("version"),
            }
        results.append(payload)

    # If sensitivity only on first, ensure all have scorecard for UI
    if results and include_sensitivity:
        scorecard = (results[0].get("sensitivity") or {}).get("scorecard") or {}
        for row in results[1:]:
            row.setdefault("sensitivity", {"scorecard": scorecard})

    diag = {
        "workstream_id": FG_WORKSTREAM_ID,
        "version": FG_VERSION,
        "ticker": str(ticker).upper(),
        "scenario_count": len(results),
        "propagation_time_ms_avg": round(
            sum(float((r.get("diagnostics") or {}).get("propagation_time_ms") or 0) for r in results)
            / max(1, len(results)),
            4,
        ),
        "decision_changes": sum(1 for r in results if r.get("decision_changed")),
        "confidence_changes": [r.get("confidence_delta") for r in results],
        "probability_distribution": {r["scenario_name"]: r["probability"] for r in results},
        "affected_nodes_avg": round(
            sum(int((r.get("diagnostics") or {}).get("affected_nodes") or 0) for r in results)
            / max(1, len(results)),
            4,
        ),
        "quality_gate_pass": not validation_errors,
        "llm": False,
    }

    comparison = [
        {
            "scenario": r["scenario_name"],
            "decision": r["resulting_decision"],
            "confidence": r["resulting_confidence"],
            "probability": r["probability"],
            "decision_changed": r["decision_changed"],
        }
        for r in results
    ]

    key = str(ticker).strip().upper()
    _SCENARIOS[key] = results

    out = {
        "ok": not validation_errors,
        "rejected": bool(validation_errors),
        "workstream_id": FG_WORKSTREAM_ID,
        "ticker": key,
        "company_name": getattr(fixture, "company_name", ""),
        "horizon": horizon,
        "base_decision": {
            "recommendation": decision.recommendation if decision else None,
            "confidence": decision.confidence if decision else None,
            "conviction": decision.conviction if decision else None,
            "score": decision.score if decision else None,
            "decision_id": decision.decision_id if decision else None,
            "knowledge_graph_id": getattr(decision, "knowledge_graph_id", "") if decision else "",
        },
        "scenarios": results,
        "comparison": comparison,
        "probability_distribution": diag["probability_distribution"],
        "diagnostics": diag,
        "validation_errors": validation_errors,
        "lineage": [
            "Evidence",
            "Knowledge Graph",
            "Scenario",
            "Propagation",
            "Inference",
            "Decision",
            "Calibration",
            "Report",
        ],
        "llm": False,
    }
    if include_sensitivity and results:
        out["sensitivity"] = results[0].get("sensitivity") or {}
    return out


def get_company_scenarios(
    ticker: str,
    *,
    include_graph: bool = False,
    include_propagation: bool = True,
    rebuild: bool = False,
) -> dict[str, Any]:
    key = str(ticker or "").strip().upper()
    if not rebuild and key in _SCENARIOS:
        rows = _SCENARIOS[key]
        # Filter fields
        scenarios = []
        for r in rows:
            row = dict(r)
            if not include_propagation:
                row.pop("propagated_impacts", None)
                row.pop("changed_nodes", None)
            if not include_graph:
                row.pop("forecast_graph", None)
            scenarios.append(row)
        return {
            "ok": True,
            "workstream_id": FG_WORKSTREAM_ID,
            "ticker": key,
            "scenarios": scenarios,
            "comparison": [
                {
                    "scenario": r["scenario_name"],
                    "decision": r["resulting_decision"],
                    "confidence": r["resulting_confidence"],
                    "probability": r["probability"],
                    "decision_changed": r["decision_changed"],
                }
                for r in scenarios
            ],
            "cached": True,
            "llm": False,
        }
    return run_company_scenarios(
        key,
        include_graph=include_graph,
        include_propagation=include_propagation,
    )


def scenario_company(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    ticker = str(body.get("ticker") or "").strip()
    scenarios = body.get("scenarios")
    if isinstance(scenarios, str):
        scenarios = [s.strip() for s in scenarios.split(",") if s.strip()]
    include_graph = body.get("include_graph", False)
    include_propagation = body.get("include_propagation", True)
    include_sensitivity = body.get("include_sensitivity", True)
    if isinstance(include_graph, str):
        include_graph = include_graph.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(include_propagation, str):
        include_propagation = include_propagation.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(include_sensitivity, str):
        include_sensitivity = include_sensitivity.strip().lower() in {"1", "true", "yes", "on"}

    return run_company_scenarios(
        ticker,
        scenarios=scenarios,
        custom_assumptions=body.get("assumptions"),
        horizon=str(body.get("horizon") or DEFAULT_HORIZON),
        include_graph=bool(include_graph),
        include_propagation=bool(include_propagation),
        include_sensitivity=bool(include_sensitivity),
        probability_distribution=body.get("probability_distribution"),
    )
