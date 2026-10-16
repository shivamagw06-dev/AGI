"""SSL analyse / run pipeline — reproducible institutional simulations."""

from __future__ import annotations

from typing import Any

from simulation_lab.confidence.engine import simulation_confidence
from simulation_lab.decision_lab.engine import build_decision_package, opportunity_cost_analysis
from simulation_lab.evidence.attach import attach_evidence
from simulation_lab.macro_lab.engine import resolve_macro_shock
from simulation_lab.optimisation.engine import optimisation_notes
from simulation_lab.portfolio_lab.engine import simulate_portfolio_change
from simulation_lab.probabilities.engine import run_monte_carlo
from simulation_lab.replay.engine import run_replay
from simulation_lab.reports.build import build_report
from simulation_lab.scenario_lab.company_sim import company_assumption_shift
from simulation_lab.scenario_lab.engine import list_all_scenarios, resolve_scenario
from simulation_lab.schema import SSL_VERSION, PRIMARY_QUESTION
from simulation_lab.sensitivity.engine import sensitivity_analysis
from simulation_lab.store.corpus import append_run, list_history
from simulation_lab.strategy_lab.engine import compare_strategies
from simulation_lab.stress_testing.engine import run_stress_tests


def _base_params(scenario: dict[str, Any], macro: dict[str, Any]) -> tuple[float, float, float]:
    assumptions = scenario.get("assumptions") or {}
    ticker = scenario.get("ticker") or "HDFCBANK"
    base_return = 0.085
    base_vol = 0.17
    if ticker == "NESTLEIND":
        base_return, base_vol = 0.08, 0.14
    elif ticker == "TCS":
        base_return, base_vol = 0.1, 0.2
    # Weight change nudges expected return slightly (soft)
    delta = float(assumptions.get("weight_delta_bps") or 0)
    base_return += (delta / 10000.0) * 0.15
    company = company_assumption_shift(assumptions)
    base_return += float(company.get("return_delta") or 0)
    base_vol = max(0.05, base_vol + float(company.get("vol_delta") or 0))
    shock = float(macro.get("shock") or 0.0)
    if assumptions.get("nim_sensitivity") is not None and macro.get("shock_id") == "rates_plus_100bps":
        shock += float(assumptions["nim_sensitivity"]) * 0.05
    return base_return, base_vol, shock


def run_simulation(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    scenario = resolve_scenario(payload)
    assumptions = scenario.get("assumptions") or {}
    evidence = attach_evidence(assumptions)
    macro = resolve_macro_shock(assumptions)
    run_key = f"{scenario.get('id')}|{scenario.get('ticker')}|{scenario.get('portfolio_id')}|{sorted(assumptions.items())}"
    base_return, base_vol, shock = _base_params(scenario, macro)
    n = int(payload.get("n") or assumptions.get("monte_carlo_n") or 2000)
    probabilities = run_monte_carlo(
        run_key=run_key,
        assumptions=assumptions,
        n=n,
        base_return=base_return,
        base_vol=base_vol,
        shock=shock,
    )
    portfolio = simulate_portfolio_change(
        ticker=scenario["ticker"],
        portfolio_id=scenario["portfolio_id"],
        assumptions=assumptions,
        distribution=probabilities,
    )
    strategies = compare_strategies(run_key=run_key, assumptions=assumptions, macro_shock=shock)
    # Ensure strategy compare always has at least quality vs value when family is strategy
    if scenario.get("family") == "strategy" and not assumptions.get("strategy_a"):
        strategies = compare_strategies(
            run_key=run_key,
            assumptions={**assumptions, "strategy_a": "high_quality", "strategy_b": "deep_value"},
            macro_shock=shock,
        )
    stress = run_stress_tests(distribution=probabilities, macro=macro, portfolio=portfolio)
    sensitivity = sensitivity_analysis(assumptions=assumptions, macro=macro, distribution=probabilities)
    opportunity_cost = opportunity_cost_analysis(
        distribution=probabilities, strategies=strategies, assumptions=assumptions
    )
    replay = run_replay(
        run_key=run_key,
        assumptions={**assumptions, "family": scenario.get("family")},
        portfolio_id=scenario["portfolio_id"],
    )
    confidence = simulation_confidence(
        assumptions=assumptions,
        evidence=evidence,
        stress_completed=bool(stress.get("completed")),
        distribution_ok=bool(probabilities.get("distribution")),
    )
    optimisation = optimisation_notes(portfolio=portfolio, strategies=strategies)
    decision = build_decision_package(
        scenario=scenario,
        portfolio=portfolio,
        macro=macro,
        stress=stress,
        strategies=strategies,
        opportunity_cost=opportunity_cost,
        distribution=probabilities,
        confidence=confidence,
    )
    pack: dict[str, Any] = {
        "found": True,
        "ssl_version": SSL_VERSION,
        "primary_question": PRIMARY_QUESTION,
        "scenario": scenario,
        "assumptions_explicit": True,
        "evidence": evidence,
        "macro": macro,
        "probabilities": probabilities,
        "portfolio": portfolio,
        "strategies": strategies,
        "stress": stress,
        "sensitivity": sensitivity,
        "opportunity_cost": opportunity_cost,
        "replay": replay,
        "confidence": confidence,
        "optimisation": optimisation,
        "decision": decision,
        "reproducible": True,
        "run_key_seed": probabilities.get("seed"),
        "not_an_engine_redesign": True,
        "never_recommendation": True,
        "no_unsupported_deterministic_outcomes": True,
        "active_experimentation": True,
    }
    pack["report"] = build_report(pack)
    history_row = append_run(
        {
            "scenario_id": scenario.get("id"),
            "ticker": scenario.get("ticker"),
            "portfolio_id": scenario.get("portfolio_id"),
            "seed": probabilities.get("seed"),
            "expected_return": probabilities.get("expected_return"),
            "confidence": confidence.get("confidence"),
            "executive_summary": pack["report"].get("executive_summary"),
        }
    )
    pack["history_record"] = history_row
    return pack


def run_portfolio_simulation(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    payload.setdefault("scenario_id", payload.get("scenario_id") or "rebalance_hdfc_plus")
    payload.setdefault("family", "portfolio_rebalance")
    out = run_simulation(payload)
    return {
        "ssl_version": SSL_VERSION,
        "portfolio_simulation": True,
        "portfolio": out.get("portfolio"),
        "probabilities": out.get("probabilities"),
        "decision": out.get("decision"),
        "report": out.get("report"),
        "reproducible": True,
        "history_record": out.get("history_record"),
        "full": out,
    }


def simulation_history(*, limit: int = 50) -> dict[str, Any]:
    return {
        "ssl_version": SSL_VERSION,
        "history": list_history(limit=limit),
        "append_only": True,
        "count": len(list_history(limit=limit)),
    }


def scenarios_pack() -> dict[str, Any]:
    return {"ssl_version": SSL_VERSION, **list_all_scenarios()}
