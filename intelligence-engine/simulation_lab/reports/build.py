"""SSL report builder — institutional simulation output format."""

from __future__ import annotations

from typing import Any


def build_report(pack: dict[str, Any]) -> dict[str, Any]:
    scenario = pack.get("scenario") or {}
    dist = pack.get("probabilities") or {}
    decision = pack.get("decision") or {}
    stress = pack.get("stress") or {}
    strategies = pack.get("strategies") or {}
    sensitivity = pack.get("sensitivity") or {}
    opportunity = pack.get("opportunity_cost") or {}
    replay = pack.get("replay") or {}
    confidence = pack.get("confidence") or {}
    evidence = pack.get("evidence") or {}
    portfolio = pack.get("portfolio") or {}

    executive = (
        f"Simulation '{scenario.get('label')}' for {scenario.get('ticker')} on "
        f"{scenario.get('portfolio_id')}: expected return {dist.get('expected_return')}, "
        f"vol {dist.get('expected_volatility')}, left-tail p05 {dist.get('tail_risk_p05')}. "
        f"Stress completed={stress.get('completed')}; opportunity cost analysed="
        f"{opportunity.get('analysed')}. Probabilistic — not deterministic."
    )
    return {
        "executive_summary": executive,
        "simulation_objective": scenario.get("objective"),
        "assumptions": scenario.get("assumptions"),
        "portfolio_changes": {
            "weight_delta_bps": portfolio.get("weight_delta_bps"),
            "factor_exposure_delta": portfolio.get("factor_exposure_delta"),
            "quality_score_delta": portfolio.get("quality_score_delta"),
        },
        "scenario_outcomes": dist.get("distribution"),
        "stress_results": stress.get("tests"),
        "opportunity_cost": opportunity,
        "alternative_strategies": strategies.get("strategies"),
        "sensitivity_analysis": sensitivity,
        "probability_distribution": {
            "distribution": dist.get("distribution"),
            "bands": dist.get("bands"),
            "n": dist.get("n"),
            "seed": dist.get("seed"),
        },
        "risk_summary": {
            "max_drawdown_proxy": dist.get("max_drawdown_proxy"),
            "tail_risk_p05": dist.get("tail_risk_p05"),
            "liquidity": portfolio.get("liquidity"),
        },
        "monitoring_plan": decision.get("recommended_monitoring"),
        "confidence": confidence.get("confidence"),
        "evidence": evidence,
        "historical_replay": {
            "active": replay.get("active"),
            "replay_id": replay.get("replay_id"),
            "behaviour": replay.get("portfolio_behaviour"),
        },
        "cio_brief": (
            f"Decision package ready for {scenario.get('ticker')}: "
            f"conf {confidence.get('confidence')}; "
            f"monitor assumption drift and FIL/FDI material changes."
        ),
        "committee": {
            "trade_offs": strategies.get("trade_offs"),
            "alternatives": strategies.get("strategies"),
            "opportunity_cost": opportunity,
        },
        "portfolio_office": {
            "quality_delta": portfolio.get("quality_score_delta"),
            "factor_exposure_delta": portfolio.get("factor_exposure_delta"),
            "expected_behaviour": {
                "return": dist.get("expected_return"),
                "volatility": dist.get("expected_volatility"),
            },
        },
        "writer_blocks": {
            "tables": ["scenario_outcomes", "stress_results", "strategy_comparison", "probability_bands"],
            "charts": ["distribution_histogram", "sensitivity_tornado", "replay_path_analogue"],
        },
        "never_recommendation": True,
        "not_deterministic": True,
    }
