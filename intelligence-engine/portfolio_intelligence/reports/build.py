"""PIO report + suitability matrix — never Buy/Hold/Sell."""

from __future__ import annotations

from typing import Any


def suitability_matrix(impact: dict[str, Any], *, sizing: dict[str, Any], pqe_delta: dict[str, Any]) -> dict[str, Any]:
    net = impact.get("net_portfolio_effect")
    strategic = "strong" if pqe_delta.get("improves") else "mixed" if net == "mixed" else "weak"
    port_fit = "strong" if net == "improves" else "mixed" if net == "mixed" else "weak"
    div = "positive" if impact.get("diversification_improves") else "neutral_or_negative"
    risk = "increases" if impact.get("portfolio_risk_rises") else "stable_or_lower"
    mon = "elevated" if impact.get("sector_concentration_exceeds_limits") or impact.get("overlap", {}).get("overlap_flag") != "low" else "standard"

    return {
        "strategic_fit": strategic,
        "portfolio_fit": port_fit,
        "diversification_benefit": div,
        "risk_contribution": risk,
        "capital_efficiency": "band_defined" if sizing.get("suggested_initial_weight") is not None else "add_on_only",
        "monitoring_requirement": mon,
        "never_buy_hold_sell": True,
        "summary": (
            f"Portfolio fit {port_fit}; diversification {div}; risk {risk}; "
            f"PQE Δ {pqe_delta.get('delta')}. Suitability only — not a recommendation."
        ),
    }


def build_report(
    *,
    profile: dict[str, Any],
    health: dict[str, Any],
    impact: dict[str, Any] | None,
    suitability: dict[str, Any] | None,
    allocation: dict[str, Any],
    factors: dict[str, Any],
    correlation: dict[str, Any],
    liquidity: dict[str, Any],
    risk: dict[str, Any],
    scenarios: dict[str, Any],
    sizing: dict[str, Any] | None,
    watchlist: dict[str, Any],
    pqe: dict[str, Any],
    confidence: dict[str, Any],
    evidence: dict[str, Any],
    candidate: str | None,
) -> dict[str, Any]:
    name = profile.get("name") or profile.get("portfolio_id")
    exec_sum = (
        f"{name}: portfolio grade {health.get('grade')} · quality {pqe.get('portfolio_quality')}/100 · "
        f"confidence {confidence.get('confidence')}/100. "
        "Primary question: does a candidate improve this specific portfolio?"
    )
    if candidate and impact:
        exec_sum += (
            f" Candidate {candidate}: net effect {impact.get('net_portfolio_effect')}; "
            f"{(suitability or {}).get('summary')}"
        )

    cio_brief = (
        f"Portfolio context for capital allocation: grade {health.get('grade')}, "
        f"PQE {pqe.get('portfolio_quality')}, risk vol ~{risk.get('expected_volatility')}, "
        f"worst scenario {(scenarios.get('worst') or {}).get('scenario')} "
        f"({(scenarios.get('worst') or {}).get('portfolio_impact_pct')}%). "
        "No buy/sell instruction issued."
    )

    return {
        "executive_summary": exec_sum,
        "portfolio_health": health,
        "holding_analysis": {"n": health.get("n_holdings"), "cash": allocation.get("cash_weight")},
        "candidate_impact": impact,
        "diversification": health.get("diversification"),
        "concentration": health.get("concentration"),
        "sector_exposure": allocation,
        "factor_exposure": factors,
        "correlation": correlation,
        "liquidity": liquidity,
        "risk_budget": risk,
        "scenario_results": scenarios,
        "position_suitability": suitability,
        "position_sizing": sizing,
        "monitoring_plan": watchlist.get("monitoring_priority"),
        "portfolio_quality": pqe,
        "confidence": confidence,
        "evidence": evidence,
        "missing_evidence": evidence.get("missing") or [],
        "cio_brief": cio_brief,
        "committee": {
            "portfolio_impact": impact,
            "trade_offs": suitability,
            "risk_changes": {
                "vol": risk.get("expected_volatility"),
                "drawdown_usage": risk.get("drawdown_budget_usage"),
            },
            "diversification_effects": impact.get("diversification_delta") if impact else None,
            "capacity": sizing,
        },
        "text": exec_sum + " " + cio_brief,
        "never_recommendation": True,
    }


def portfolio_health_block(
    *,
    diversification: dict[str, Any],
    concentration: dict[str, Any],
    risk: dict[str, Any],
    liquidity: dict[str, Any],
    factors: dict[str, Any],
    allocation: dict[str, Any],
    pqe: dict[str, Any],
    n_holdings: int,
) -> dict[str, Any]:
    scores = {
        "diversification": diversification.get("diversification"),
        "quality": pqe.get("portfolio_quality"),
        "risk": risk.get("risk_score"),
        "liquidity": liquidity.get("liquidity"),
        "concentration": concentration.get("concentration"),
        "factor_balance": factors.get("factor_balance"),
        "sector_balance": 75.0 - 15.0 * len(allocation.get("sector_limit_breaches") or []),
    }
    overall = round(sum(float(v or 0) for v in scores.values()) / len(scores), 1)
    grade = "A" if overall >= 80 else "B" if overall >= 65 else "C" if overall >= 50 else "D"
    return {
        "scores": {k: round(float(v or 0), 1) for k, v in scores.items()},
        "overall": overall,
        "grade": grade,
        "n_holdings": n_holdings,
        "diversification": diversification,
        "concentration": concentration,
    }
