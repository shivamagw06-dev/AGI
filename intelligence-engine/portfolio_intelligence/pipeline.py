"""PIO analyse pipeline — portfolio context + candidate suitability (never orders)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from portfolio_intelligence.allocation.score import allocation_analysis
from portfolio_intelligence.concentration.score import concentration_score
from portfolio_intelligence.confidence.model import portfolio_confidence
from portfolio_intelligence.correlation.score import correlation_analysis
from portfolio_intelligence.diversification.score import diversification_score
from portfolio_intelligence.evidence.attach import evidence_pack
from portfolio_intelligence.factor_exposure.score import factor_exposure
from portfolio_intelligence.holdings.position_impact import position_impact
from portfolio_intelligence.holdings.position_sizing import position_sizing
from portfolio_intelligence.liquidity.score import liquidity_score
from portfolio_intelligence.optimisation.score import optimisation_score
from portfolio_intelligence.overlap.score import overlap_analysis
from portfolio_intelligence.portfolio.packs import default_portfolio_id, portfolio_for
from portfolio_intelligence.quality.pqe import portfolio_quality, quality_delta
from portfolio_intelligence.reports.build import build_report, portfolio_health_block, suitability_matrix
from portfolio_intelligence.risk_budget.score import empirical_risk_budget, risk_budget
from portfolio_intelligence.scenario.engine import run_scenarios
from portfolio_intelligence.schema import PIO_VERSION
from portfolio_intelligence.watchlist.rank import rank_watchlist

# Sector priors for candidates not in book
_CANDIDATE_META = {
    "HDFCBANK": {"sector": "banks", "market_cap": "large", "style": "quality", "factors": {"quality": 0.8, "value": 0.4, "growth": 0.5, "momentum": 0.3, "low_vol": 0.6, "dividend": 0.4, "leverage": 0.5, "profitability": 0.7}},
    "KOTAKBANK": {"sector": "banks", "market_cap": "large", "style": "quality", "factors": {"quality": 0.78, "value": 0.42, "growth": 0.5, "momentum": 0.35, "low_vol": 0.58, "dividend": 0.3, "leverage": 0.5, "profitability": 0.7}},
    "HINDUNILVR": {"sector": "fmcg", "market_cap": "large", "style": "quality", "factors": {"quality": 0.9, "value": 0.2, "growth": 0.45, "momentum": 0.3, "low_vol": 0.8, "dividend": 0.5, "leverage": 0.15, "profitability": 0.88}},
    "SBIN": {"sector": "banks", "market_cap": "large", "style": "value", "factors": {"quality": 0.5, "value": 0.65, "growth": 0.45, "momentum": 0.4, "low_vol": 0.35, "dividend": 0.4, "leverage": 0.7, "profitability": 0.55}},
    "NESTLEIND": {"sector": "fmcg", "market_cap": "large", "style": "quality", "factors": {"quality": 0.88, "value": 0.2, "growth": 0.55, "momentum": 0.35, "low_vol": 0.75, "dividend": 0.45, "leverage": 0.2, "profitability": 0.88}},
    "TCS": {"sector": "it_services", "market_cap": "large", "style": "quality", "factors": {"quality": 0.9, "value": 0.35, "growth": 0.45, "momentum": 0.35, "low_vol": 0.7, "dividend": 0.55, "leverage": 0.15, "profitability": 0.9}},
}


def _snapshot(
    holdings: list[dict[str, Any]], profile: dict[str, Any], cash_weight: float,
    *, daily_returns: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    divers = diversification_score(holdings, cash_weight=cash_weight)
    conc = concentration_score(
        holdings,
        single_name_limit=float(profile.get("single_name_limit") or 0.12),
        sector_limits=profile.get("sector_limits") or {},
    )
    factors = factor_exposure(holdings)
    corr = correlation_analysis(holdings)
    risk = risk_budget(
        holdings,
        max_drawdown=float(profile.get("max_drawdown") or 0.25),
        avg_corr=float(corr.get("avg_pairwise_correlation") or 0.4),
    )
    empirical = empirical_risk_budget(daily_returns or [], max_drawdown=float(profile.get("max_drawdown") or 0.25))
    if empirical:
        empirical["contributions"] = risk.get("contributions") or []
        risk = empirical
    liq = liquidity_score(holdings)
    alloc = allocation_analysis(
        holdings,
        cash_weight=cash_weight,
        benchmark=None,  # filled by caller when available
        sector_limits=profile.get("sector_limits") or {},
    )
    pqe = portfolio_quality(holdings)
    return {
        "diversification": divers,
        "concentration": conc,
        "factors": factors,
        "correlation": corr,
        "risk": risk,
        "liquidity": liq,
        "allocation": alloc,
        "portfolio_quality": pqe,
    }


def _candidate_holding(ticker: str, weight: float) -> dict[str, Any]:
    t = ticker.upper()
    meta = _CANDIDATE_META.get(t) or {
        "sector": "other",
        "market_cap": "large",
        "style": "blend",
        "factors": {"quality": 0.55, "value": 0.5, "growth": 0.5, "momentum": 0.4, "low_vol": 0.4, "dividend": 0.3, "leverage": 0.4, "profitability": 0.55},
    }
    return {
        "ticker": t,
        "weight": weight,
        "sector": meta["sector"],
        "industry": meta.get("industry") or meta["sector"],
        "country": "IN",
        "market_cap": meta["market_cap"],
        "style": meta["style"],
        "thesis": "Candidate under portfolio suitability review",
        "conviction": "medium",
        "factors": meta["factors"],
    }


def analyse_portfolio(
    portfolio_id: str | None = None,
    *,
    candidate: str | None = None,
    candidate_weight: float | None = None,
) -> dict[str, Any]:
    pid = portfolio_id or default_portfolio_id()
    book = portfolio_for(pid)
    if not book:
        return {"portfolio_id": pid, "found": False, "pio_version": PIO_VERSION}

    profile = book["profile"]
    data_lineage = book.get("data_lineage") or {"source": "unknown"}
    holdings = list(book.get("holdings") or [])
    cash = float(book.get("cash_weight") or 0)
    bench = book.get("benchmark_sector_weights") or {}
    daily_returns = book.get("daily_returns") or []

    current = _snapshot(holdings, profile, cash, daily_returns=daily_returns)
    current["allocation"] = allocation_analysis(
        holdings,
        cash_weight=cash,
        benchmark=bench,
        sector_limits=profile.get("sector_limits") or {},
    )
    scenarios = run_scenarios(holdings, cash_weight=cash)

    soft_sources = ["portfolio_packs", "mii_soft", "aci_soft"]

    cand = (candidate or "").upper() or None
    impact = None
    suitability = None
    sizing = None
    pro_forma_snap = None
    candidate_governance = None
    overlap = overlap_analysis(holdings, candidate_ticker=cand, candidate_sector=None)

    if cand:
        meta = _CANDIDATE_META.get(cand) or {"sector": "other"}
        overlap = overlap_analysis(holdings, candidate_ticker=cand, candidate_sector=meta.get("sector"))
        # Propose weight from sizing heuristic seed
        seed_w = float(candidate_weight) if candidate_weight is not None else 0.05
        if overlap.get("already_held"):
            # evaluate small add-on
            pf_holdings = deepcopy(holdings)
            for h in pf_holdings:
                if str(h.get("ticker")).upper() == cand:
                    h["weight"] = float(h.get("weight") or 0) + seed_w
            pf_cash = max(0.0, cash - seed_w)
        else:
            pf_holdings = deepcopy(holdings) + [_candidate_holding(cand, seed_w)]
            pf_cash = max(0.0, cash - seed_w)

        pro_forma_snap = _snapshot(pf_holdings, profile, pf_cash)
        pro_forma_snap["allocation"] = allocation_analysis(
            pf_holdings,
            cash_weight=pf_cash,
            benchmark=bench,
            sector_limits=profile.get("sector_limits") or {},
        )
        impact = position_impact(current=current, pro_forma=pro_forma_snap, overlap=overlap)
        pqe_d = quality_delta(current["portfolio_quality"], pro_forma_snap["portfolio_quality"])
        current_risk_method = (current.get("risk") or {}).get("method")
        pro_forma_risk_method = (pro_forma_snap.get("risk") or {}).get("method")
        risk_methods_compatible = bool(current_risk_method and current_risk_method == pro_forma_risk_method)
        candidate_governance = {
            "risk_models_compatible": risk_methods_compatible,
            "current_risk_method": current_risk_method,
            "pro_forma_risk_method": pro_forma_risk_method,
            "execution_eligible": False,
            "reason": None if risk_methods_compatible else "CANDIDATE_COVARIANCE_HISTORY_REQUIRED",
            "rule": "Candidate sizing requires a pro-forma empirical risk model comparable with the current portfolio.",
        }
        if risk_methods_compatible:
            sizing = position_sizing(
                profile=profile,
                overlap=overlap,
                diversification_delta=float(impact.get("diversification_delta") or 0),
                risk_delta=float(impact.get("risk_vol_delta") or 0),
                quality_delta=float(impact.get("quality_delta") or 0),
            )
        else:
            impact.update({
                "portfolio_risk_rises": None,
                "risk_vol_delta": None,
                "net_portfolio_effect": "undetermined",
                "risk_model_compatible": False,
                "reason": "CANDIDATE_COVARIANCE_HISTORY_REQUIRED",
            })
            sizing = {
                "status": "BLOCKED",
                "minimum_weight": None,
                "suggested_initial_weight": None,
                "maximum_weight": None,
                "maximum_exposure": float(profile.get("single_name_limit") or 0.12),
                "never_buy_sell_instructions": True,
                "reason": "CANDIDATE_COVARIANCE_HISTORY_REQUIRED",
                "note": "No sizing band until candidate covariance history supports a comparable pro-forma risk model.",
            }
        # Re-run impact at suggested weight when available
        sug = sizing.get("suggested_initial_weight")
        if risk_methods_compatible and sug and not overlap.get("already_held") and candidate_weight is None:
            pf_holdings = deepcopy(holdings) + [_candidate_holding(cand, float(sug))]
            pf_cash = max(0.0, cash - float(sug))
            pro_forma_snap = _snapshot(pf_holdings, profile, pf_cash)
            pro_forma_snap["allocation"] = allocation_analysis(
                pf_holdings,
                cash_weight=pf_cash,
                benchmark=bench,
                sector_limits=profile.get("sector_limits") or {},
            )
            impact = position_impact(current=current, pro_forma=pro_forma_snap, overlap=overlap)
            pqe_d = quality_delta(current["portfolio_quality"], pro_forma_snap["portfolio_quality"])
        suitability = (
            suitability_matrix(impact, sizing=sizing, pqe_delta=pqe_d)
            if risk_methods_compatible
            else {
                "status": "BLOCKED",
                "portfolio_fit": "undetermined",
                "risk_contribution": "not_calculated",
                "capital_efficiency": "not_calculated",
                "never_buy_hold_sell": True,
                "reason": "CANDIDATE_COVARIANCE_HISTORY_REQUIRED",
                "summary": "Candidate suitability is blocked until comparable empirical pro-forma risk is available.",
            }
        )

    health = portfolio_health_block(
        diversification=current["diversification"],
        concentration=current["concentration"],
        risk=current["risk"],
        liquidity=current["liquidity"],
        factors=current["factors"],
        allocation=current["allocation"],
        pqe=current["portfolio_quality"],
        n_holdings=len(holdings),
    )
    opt = optimisation_score(
        diversification=float(current["diversification"]["diversification"]),
        concentration=float(current["concentration"]["concentration"]),
        factor_balance=float(current["factors"]["factor_balance"]),
        risk_score=float(current["risk"]["risk_score"]),
        portfolio_quality=float(current["portfolio_quality"]["portfolio_quality"]),
        liquidity=float(current["liquidity"]["liquidity"]),
    )
    watch = rank_watchlist(
        list(book.get("watchlist") or []),
        holdings=holdings,
        concentration=current["concentration"],
        impact=impact,
        candidate=cand,
    )

    holding_cov = min(100.0, 40.0 + 6.0 * len(holdings))
    evidence_q = min(100.0, 50.0 + 5.0 * len(soft_sources))
    conf = portfolio_confidence(
        holding_coverage=holding_cov,
        evidence_quality=evidence_q,
        portfolio_data=85.0,
        risk_coverage=float(current["risk"]["risk_score"]),
        scenario_coverage=float(scenarios.get("scenario_coverage") or 80),
    )
    evidence = evidence_pack(
        portfolio_id=profile["portfolio_id"],
        holdings=holdings,
        soft_sources=soft_sources,
        confidence=conf,
    )
    report = build_report(
        profile=profile,
        health=health,
        impact=impact,
        suitability=suitability,
        allocation=current["allocation"],
        factors=current["factors"],
        correlation=current["correlation"],
        liquidity=current["liquidity"],
        risk=current["risk"],
        scenarios=scenarios,
        sizing=sizing,
        watchlist=watch,
        pqe=current["portfolio_quality"],
        confidence=conf,
        evidence=evidence,
        candidate=cand,
    )

    return {
        "portfolio_id": profile["portfolio_id"],
        "found": True,
        "pio_version": PIO_VERSION,
        "primary_question": "Does this investment improve portfolio quality?",
        "profile": profile,
        "data_lineage": data_lineage,
        "holdings": holdings,
        "cash_weight": cash,
        "health": health,
        "allocation": current["allocation"],
        "diversification": current["diversification"],
        "concentration": current["concentration"],
        "factors": current["factors"],
        "correlation": current["correlation"],
        "liquidity": current["liquidity"],
        "risk": current["risk"],
        "scenarios": scenarios,
        "optimisation": opt,
        "portfolio_quality": current["portfolio_quality"],
        "candidate": cand,
        "overlap": overlap,
        "impact": impact,
        "suitability": suitability,
        "position_sizing": sizing,
        "candidate_governance": candidate_governance,
        "pro_forma": pro_forma_snap,
        "watchlist": watch,
        "confidence": conf,
        "evidence": evidence,
        "report": report,
        "never_recommendation": True,
        "does_not_replace_company_analysis": True,
    }
