"""Decision lab — committee proposal → simulation package (no buy/sell mandate)."""

from __future__ import annotations

from typing import Any


def build_decision_package(
    *,
    scenario: dict[str, Any],
    portfolio: dict[str, Any],
    macro: dict[str, Any],
    stress: dict[str, Any],
    strategies: dict[str, Any],
    opportunity_cost: dict[str, Any],
    distribution: dict[str, Any],
    confidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "proposal": scenario.get("label") or scenario.get("objective"),
        "ticker": scenario.get("ticker"),
        "portfolio_id": scenario.get("portfolio_id"),
        "simulation_summary": {
            "expected_return": distribution.get("expected_return"),
            "expected_volatility": distribution.get("expected_volatility"),
            "tail_risk_p05": distribution.get("tail_risk_p05"),
            "stress_completed": stress.get("completed"),
            "macro_active": macro.get("active"),
        },
        "portfolio_impact": {
            "weight_delta_bps": portfolio.get("weight_delta_bps"),
            "quality_score_delta": portfolio.get("quality_score_delta"),
            "factor_exposure_delta": portfolio.get("factor_exposure_delta"),
            "liquidity": portfolio.get("liquidity"),
        },
        "macro_impact": {
            "shock_id": macro.get("shock_id"),
            "channels": macro.get("channels"),
        },
        "risk_impact": {
            "max_drawdown_proxy": portfolio.get("maximum_drawdown"),
            "stress_tests": [t.get("name") for t in (stress.get("tests") or [])],
        },
        "opportunity_cost": opportunity_cost,
        "alternative_strategies": strategies.get("strategies"),
        "trade_offs": strategies.get("trade_offs"),
        "recommended_monitoring": [
            "Track assumption drift vs recorded baseline",
            "Re-run simulation if FIL/FDI material change fires",
            "Compare realised path vs distribution bands (ILM learning loop)",
            "Watch macro channels listed in stress package",
        ],
        "confidence": confidence.get("confidence"),
        "rule": "Decision package informs committee — SSL never issues a trade instruction",
        "never_recommendation": True,
    }


def opportunity_cost_analysis(
    *,
    distribution: dict[str, Any],
    strategies: dict[str, Any],
    assumptions: dict[str, Any],
) -> dict[str, Any]:
    alts = strategies.get("strategies") or []
    primary = distribution.get("expected_return")
    forgone = None
    if len(alts) >= 2:
        forgone = round(float(alts[1]["expected_return"]) - float(alts[0]["expected_return"]), 4)
    return {
        "analysed": True,
        "primary_expected_return": primary,
        "forgone_sleeve_spread": forgone,
        "redeploy": assumptions.get("redeploy") or assumptions.get("funding"),
        "narrative": "Opportunity cost is the alternative sleeve distribution under the same evidence set",
        "rule": "Opportunity cost analysed for every decision simulation",
    }
