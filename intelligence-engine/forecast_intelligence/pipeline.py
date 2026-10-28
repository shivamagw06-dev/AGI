"""FIE analyse pipeline — company scenario / catalyst / probability packs."""

from __future__ import annotations

from typing import Any

from forecast_intelligence.catalysts.engine import catalysts_for
from forecast_intelligence.confidence.model import forecast_confidence
from forecast_intelligence.consensus.engine import consensus_compare
from forecast_intelligence.evidence.attach import evidence_pack
from forecast_intelligence.expectations.engine import expectation_gap
from forecast_intelligence.probability.engine import score_probabilities
from forecast_intelligence.profiles.packs import list_profiles, profile_for
from forecast_intelligence.reports.build import build_report
from forecast_intelligence.scenarios.engine import build_scenarios
from forecast_intelligence.schema import FIE_VERSION, PRIMARY_QUESTION, SCENARIO_NAMES
from forecast_intelligence.sensitivity.engine import sensitivity_matrix
from forecast_intelligence.transmission.soft import soft_causal_transmission
from forecast_intelligence.triggers.engine import triggers_for
from forecast_intelligence.uncertainty.engine import uncertainty_assessment


def _portfolio_impact(profile: dict[str, Any], scenarios: list[dict[str, Any]], sensitivity: dict[str, Any]) -> dict[str, Any]:
    dist = {s["name"]: s.get("probability") for s in scenarios}
    stress_p = float(dist.get("stress") or 0)
    bear_p = float(dist.get("bear") or 0)
    return {
        "scenario_impact": dist,
        "expected_portfolio_behaviour": "Factor and stress exposures shift with scenario mass — suitability context only",
        "stress_exposure": round(stress_p + 0.5 * bear_p, 3),
        "factor_impact": (sensitivity or {}).get("heatmap"),
        "top_sensitivities": (sensitivity or {}).get("top_sensitivities"),
        "sector": profile.get("sector"),
        "never_recommendation": True,
        "rule": "Portfolio Office receives scenario impact / stress exposure — never buy/sell orders",
    }


def _soft_pio(ticker: str) -> dict[str, Any]:
    try:
        from portfolio_intelligence.production import soft_slice_for_analyst

        return (soft_slice_for_analyst(ticker, analyst="committee") or {}).get("portfolio_intelligence") or {}
    except Exception:
        return {}


def analyse_company(ticker: str) -> dict[str, Any]:
    profile = profile_for(ticker)
    if not profile:
        return {
            "found": False,
            "ticker": (ticker or "").upper(),
            "fie_version": FIE_VERSION,
            "primary_question": PRIMARY_QUESTION,
            "available": list_profiles(),
        }
    t = profile["ticker"]
    causal = soft_causal_transmission(t)
    cats = catalysts_for(profile)
    trig = triggers_for(profile)
    unc = uncertainty_assessment(profile, catalysts=cats)
    probs = score_probabilities(profile, catalysts=cats, uncertainty=unc, causal_soft=causal)
    evid = evidence_pack(profile, catalysts=cats, analogues=profile.get("analogues"), causal_soft=causal)
    scenarios = build_scenarios(
        profile,
        probabilities=probs,
        triggers=trig,
        catalysts=cats,
        evidence=evid,
    )
    sens = sensitivity_matrix(profile)
    expect = expectation_gap(profile, probs)
    pio_soft = _soft_pio(t)
    cons = consensus_compare(profile, probabilities=probs, portfolio_soft=pio_soft)
    conf = forecast_confidence(probabilities=probs, uncertainty=unc, evidence=evid, triggers=trig)
    port = _portfolio_impact(profile, scenarios, sens)
    pack = {
        "found": True,
        "ticker": t,
        "name": profile.get("name"),
        "sector": profile.get("sector"),
        "fie_version": FIE_VERSION,
        "primary_question": PRIMARY_QUESTION,
        "scenarios": scenarios,
        "probabilities": probs,
        "catalysts": cats,
        "triggers": trig,
        "sensitivity": sens,
        "expectations": expect,
        "consensus": cons,
        "uncertainty": unc,
        "historical_analogues": profile.get("analogues") or [],
        "confidence": conf,
        "evidence": evid,
        "portfolio_impact": port,
        "causal_soft": causal,
        "scenario_names": list(SCENARIO_NAMES),
        "not_a_price_prediction": True,
        "no_deterministic_forecast": True,
        "never_recommendation": True,
        "not_an_engine_redesign": True,
        "does_not_replace_company_analysis": True,
    }
    pack["report"] = build_report(pack)
    return pack


def analyse_query(*, ticker: str | None = None, question: str | None = None) -> dict[str, Any]:
    if ticker:
        out = analyse_company(ticker)
        out["question"] = question
        return out
    # Question-only: infer ticker hints
    q = (question or "").lower()
    guess = None
    for tok, t in (
        ("hdfc", "HDFCBANK"),
        ("kotak", "KOTAKBANK"),
        ("tcs", "TCS"),
        ("nestle", "NESTLEIND"),
        ("tata steel", "TATASTEEL"),
        ("steel", "TATASTEEL"),
    ):
        if tok in q:
            guess = t
            break
    if guess:
        out = analyse_company(guess)
        out["question"] = question
        out["inferred_ticker"] = guess
        return out
    return {
        "found": False,
        "fie_version": FIE_VERSION,
        "primary_question": PRIMARY_QUESTION,
        "question": question,
        "available": list_profiles(),
        "hint": "Provide ticker for scenario distribution — FIE does not predict prices",
        "not_a_price_prediction": True,
    }
