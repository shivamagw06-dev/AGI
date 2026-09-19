"""FIE report builder — executive forecast + scenario tables for desks / CIO / writer."""

from __future__ import annotations

from typing import Any


def build_report(pack: dict[str, Any]) -> dict[str, Any]:
    scenarios = pack.get("scenarios") or []
    probs = pack.get("probabilities") or {}
    catalysts = pack.get("catalysts") or {}
    triggers = pack.get("triggers") or {}
    sensitivity = pack.get("sensitivity") or {}
    expectations = pack.get("expectations") or {}
    uncertainty = pack.get("uncertainty") or {}
    analogues = pack.get("historical_analogues") or []
    confidence = pack.get("confidence") or {}
    ticker = pack.get("ticker")
    most = probs.get("most_likely")
    most_p = probs.get("most_likely_probability")

    exec_lines = [
        f"Forward outlook for {ticker}: most likely path is {most} (~{most_p}).",
        "This is a scenario distribution — not a price prediction.",
        (expectations.get("narrative_gap") or {}).get("agib")
        or "AGIB evaluates plausible futures relative to market expectations.",
    ]
    scenario_table = [
        {
            "scenario": s.get("name"),
            "probability": s.get("probability"),
            "triggers": [t.get("monitor") for t in (s.get("triggers") or [])],
            "business": s.get("expected_business_impact"),
        }
        for s in scenarios
    ]
    return {
        "executive_forecast": " ".join(x for x in exec_lines if x),
        "bull_scenario": next((s for s in scenarios if s.get("name") == "bull"), None),
        "base_scenario": next((s for s in scenarios if s.get("name") == "base"), None),
        "bear_scenario": next((s for s in scenarios if s.get("name") == "bear"), None),
        "stress_scenario": next((s for s in scenarios if s.get("name") == "stress"), None),
        "recovery_scenario": next((s for s in scenarios if s.get("name") == "recovery"), None),
        "catalysts": catalysts.get("timeline") or catalysts.get("items"),
        "trigger_matrix": triggers.get("matrix"),
        "sensitivity_analysis": sensitivity.get("top_sensitivities"),
        "historical_analogues": analogues,
        "market_expectations": expectations.get("market_expects"),
        "agib_expectations": expectations.get("agib_expects"),
        "uncertainty_assessment": {
            "knowns": uncertainty.get("knowns"),
            "known_unknowns": uncertainty.get("known_unknowns"),
            "unknown_unknowns": uncertainty.get("unknown_unknowns"),
            "weak_evidence": uncertainty.get("weak_evidence"),
            "conflicting_evidence": uncertainty.get("conflicting_evidence"),
            "score": uncertainty.get("uncertainty_score"),
        },
        "portfolio_impact": pack.get("portfolio_impact"),
        "confidence": confidence,
        "evidence": pack.get("evidence"),
        "scenario_table": scenario_table,
        "committee": {
            "debate": "Scenario probabilities — not price targets",
            "distribution": probs.get("distribution"),
            "most_likely": most,
            "disagreements": (pack.get("consensus") or {}).get("disagreements"),
            "uncertainty_disclosed": True,
        },
        "cio_brief": (
            f"Institutional outlook: {most} path leading (~{most_p}). "
            f"Uncertainty {uncertainty.get('uncertainty_score')} explicitly disclosed. "
            "Prepare for multiple plausible futures; do not treat any path as certain."
        ),
        "writer_blocks": {
            "scenario_tables": scenario_table,
            "probability_charts": probs.get("distribution"),
            "catalyst_timelines": catalysts.get("timeline"),
            "sensitivity_matrices": sensitivity.get("heatmap"),
        },
        "text": " ".join(x for x in exec_lines if x),
        "no_price_prediction": True,
        "no_deterministic_forecast": True,
    }
