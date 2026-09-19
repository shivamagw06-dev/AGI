"""Facade for the AGI Alpha Validation and Investment Operating System."""

from __future__ import annotations

import os
from typing import Any, Mapping

from strategy_lab import ledger
from strategy_lab.backtest_engine import run as run_backtest
from strategy_lab.contracts import RunManifest, capital_decision_for, content_hash, stage_assessment, utc_now
from strategy_lab.definitions import all_definitions, definition as get_definition
from strategy_lab.execution import IndiaCashCostSchedule
from strategy_lab.registry_store import load_latest_evidence
from strategy_lab.research import evaluate_factor


VERSION = "agi-alpha-validation-operating-system-v1.0.0"


def _evidence(strategy_id: str) -> dict[str, Any]:
    try:
        return load_latest_evidence(strategy_id)
    except Exception:
        return {}


def definition(strategy_id: str) -> dict[str, Any]:
    item = get_definition(strategy_id)
    evidence = _evidence(item.strategy_id)
    return {
        "ok": True,
        "definition": item.to_dict(),
        "evidence": evidence,
        "governance": stage_assessment(evidence),
        "capital": capital_decision_for(item, evidence),
    }


def catalog(*, run_limit: int = 10) -> dict[str, Any]:
    strategies = []
    stage_counts: dict[str, int] = {}
    for item in all_definitions():
        evidence = _evidence(item.strategy_id)
        governance = stage_assessment(evidence)
        stage = governance["stage"]
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        strategies.append({
            "strategy_id": item.strategy_id,
            "strategy_name": item.strategy_name,
            "version": item.version,
            "role": item.role,
            "definition_hash": item.definition_hash,
            "declared_status": item.status,
            "governance": governance,
            "capital_allocation_allowed": False,
        })
    try:
        runs = ledger.recent_runs(run_limit)
    except Exception:
        runs = []
    return {
        "ok": True,
        "version": VERSION,
        "claim": "research_operating_system_no_strategy_is_implicitly_validated",
        "strategy_count": len(strategies),
        "stage_counts": stage_counts,
        "strategies": strategies,
        "recent_runs": runs,
        "capital_rule": "Only a version declared PRODUCTION with every sequential evidence gate PASSED may receive capital.",
    }


def sync_registry(*, actor: str = "admin") -> dict[str, Any]:
    return ledger.seal_definitions(all_definitions(), actor=actor)


def capital_decision(strategy_id: str) -> dict[str, Any]:
    item = get_definition(strategy_id)
    return {"ok": True, **capital_decision_for(item, _evidence(item.strategy_id))}


def _manifest(item: Any, payload: Mapping[str, Any], schedule: IndiaCashCostSchedule) -> RunManifest:
    observations = payload.get("observations") or []
    features = payload.get("feature_rows") or observations
    universe = payload.get("universe") or sorted({row.get("symbol") or row.get("company_id") for row in observations})
    actions = payload.get("corporate_actions") or []
    parameters = payload.get("parameters") or item.parameters
    return RunManifest(
        strategy_id=item.strategy_id,
        strategy_version=item.version,
        definition_hash=item.definition_hash,
        code_commit=str(payload.get("code_commit") or os.getenv("RENDER_GIT_COMMIT") or "LOCAL_UNCOMMITTED"),
        dataset_hash=content_hash(observations),
        universe_hash=content_hash(universe),
        feature_hash=content_hash(features),
        corporate_action_hash=content_hash(actions),
        cost_model_hash=schedule.schedule_hash,
        parameters_hash=content_hash(parameters),
        start_date=str(payload.get("start_date") or min((str(row.get("signal_date") or row.get("as_of")) for row in observations), default="")),
        end_date=str(payload.get("end_date") or max((str(row.get("signal_date") or row.get("as_of")) for row in observations), default="")),
        information_cutoff=item.information_cutoff,
        created_at=utc_now(),
        parent_run_id=payload.get("parent_run_id"),
        notes=tuple(str(note) for note in payload.get("notes") or ()),
    )


def run_research(strategy_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    item = get_definition(strategy_id)
    observations = list(payload.get("observations") or [])
    if not observations:
        raise ValueError("observations_required")
    if len(observations) > 250_000:
        raise ValueError("bounded_research_limit_exceeded")
    schedule = IndiaCashCostSchedule.conservative_research_default()
    manifest = _manifest(item, payload, schedule)
    persist = bool(payload.get("persist", True))
    if persist:
        ledger.seal_definition(item, actor=str(payload.get("actor") or "admin"))
        ledger.start_run(manifest, actor=str(payload.get("actor") or "admin"))

    mode = str(payload.get("mode") or "factor").lower()
    if mode == "factor":
        feature_id = str(payload.get("feature_id") or item.feature_dependencies[0])
        result = evaluate_factor(observations, feature_id=feature_id)
    elif mode == "backtest":
        result = run_backtest(
            observations,
            capital=float(payload.get("capital") or 10_000_000.0),
            schedule=schedule,
            benchmark_returns=payload.get("benchmark_returns") or {},
            max_position_weight=float(item.risk_constraints.get("max_position_weight") or 0.05),
            max_sector_weight=float(item.risk_constraints.get("max_sector_weight") or 0.25),
            max_adv_participation=float(item.risk_constraints.get("max_adv_participation") or 0.05),
            long_short=bool(payload.get("long_short", False)),
        )
    else:
        raise ValueError("mode_must_be_factor_or_backtest")
    if persist:
        ledger.complete_run(manifest.run_id, result, actor=str(payload.get("actor") or "admin"))
    return {
        "ok": True,
        "strategy_id": item.strategy_id,
        "manifest": manifest.to_dict(),
        "result": result,
        "governance": stage_assessment(_evidence(item.strategy_id)),
        "capital_allocation_allowed": False,
        "promotion": "DO_NOT_DEPLOY",
    }
