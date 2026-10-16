"""Evidence-weighted macro scenario probabilities + confidence."""

from __future__ import annotations

from typing import Any

from macroeconomic_forecast_intelligence.schema import MacroForecastBundle, MacroScenario


def assign_probabilities(
    scenarios: list[MacroScenario],
    bundle: MacroForecastBundle,
) -> dict[str, int]:
    """Institutional priors tilted by analogues, inflation tip, and contradictions → sum 100."""
    weights = {"Bull": 22.0, "Base": 56.0, "Bear": 22.0}

    # Analogue tips
    for ana in bundle.analogues[:5]:
        label = str(ana.get("matched_label") or ana.get("matched_period") or "").lower()
        score = float(ana.get("similarity_score") or 0)
        boost = min(6.0, score / 25.0)
        if any(k in label for k in ("easing", "disinflation", "2025", "2018")):
            weights["Bull"] += boost * 0.6
            weights["Base"] += boost * 0.4
        if any(k in label for k in ("inflation", "tightening", "2022", "taper", "2013")):
            weights["Bear"] += boost * 0.7
            weights["Base"] += boost * 0.2
        if any(k in label for k in ("covid", "gfc", "crisis", "2008", "2020")):
            weights["Bear"] += boost * 0.5

    # Current tip inflation / repo
    cur = bundle.current_macro or {}
    cpi = _num(cur.get("cpi") or cur.get("CPI"))
    repo = _num(cur.get("repo_rate") or cur.get("Repo Rate"))
    if cpi is not None:
        if cpi <= 4.0:
            weights["Bull"] += 4.0
            weights["Bear"] -= 2.0
        elif cpi >= 6.0:
            weights["Bear"] += 5.0
            weights["Bull"] -= 2.0
    if repo is not None and repo >= 6.25:
        weights["Base"] += 2.0  # hold / cautious bias

    # Completeness reduces tail confidence → base absorbs
    if bundle.completeness_pct < 60:
        weights["Base"] += 4.0
        weights["Bull"] -= 2.0
        weights["Bear"] -= 2.0

    # Floor
    for k in weights:
        weights[k] = max(5.0, weights[k])

    total = sum(weights.values())
    raw = {k: 100.0 * v / total for k, v in weights.items()}
    bull = int(round(raw["Bull"]))
    bear = int(round(raw["Bear"]))
    base = 100 - bull - bear
    if base < 5:
        # rebalance
        deficit = 5 - base
        base = 5
        if bull >= bear:
            bull = max(5, bull - deficit)
        else:
            bear = max(5, bear - deficit)
        base = 100 - bull - bear

    dist = {"Bull": bull, "Base": base, "Bear": bear}
    for sc in scenarios:
        sc.probability_pct = dist[sc.scenario]
    return dist


def score_confidence(
    scenarios: list[MacroScenario],
    bundle: MacroForecastBundle,
) -> dict[str, Any]:
    """Independent confidence — not the same as probability."""
    evidence_n = sum(len(s.supporting_evidence) for s in scenarios)
    analogue_n = len(bundle.analogues)
    rel_n = len(bundle.relationships)
    completeness = bundle.completeness_pct

    evidence_q = min(95, 50 + evidence_n * 3 + (10 if bundle.current_macro else 0))
    hist_cov = min(95, 40 + analogue_n * 8 + (15 if bundle.historical_tip else 0))
    analogue_str = 0
    if bundle.analogues:
        top = max(float(a.get("similarity_score") or 0) for a in bundle.analogues)
        analogue_str = int(min(95, top))
    freshness = 85 if "CMKP" in bundle.sources else 55
    research_q = 80 if bundle.research else 60
    consistency = 92 if {s.scenario for s in scenarios} == {"Bull", "Base", "Bear"} else 70
    trigger_unc = 35 if len(bundle.monitoring) >= 3 else 55

    overall = int(
        round(
            0.22 * evidence_q
            + 0.18 * hist_cov
            + 0.18 * analogue_str
            + 0.12 * freshness
            + 0.12 * completeness
            + 0.10 * research_q
            + 0.08 * consistency
        )
    )
    overall = max(40, min(95, overall))

    for sc in scenarios:
        # Scenario-specific confidence: Base typically highest certainty of assessment
        adj = 0
        if sc.scenario == "Base":
            adj = 4
        elif sc.scenario == "Bull":
            adj = -2 if (bundle.analogues and "tightening" in str(bundle.analogues[0]).lower()) else 0
        elif sc.scenario == "Bear":
            adj = 2 if analogue_str >= 80 and "inflation" in str(bundle.analogues).lower() else -1
        sc.confidence_pct = max(40, min(95, overall + adj))
        sc.confidence_label = (
            "High" if sc.confidence_pct >= 80 else ("Medium" if sc.confidence_pct >= 60 else "Low")
        )

    return {
        "overall_pct": overall,
        "evidence_quality_pct": evidence_q,
        "historical_coverage_pct": hist_cov,
        "historical_analogue_strength_pct": analogue_str,
        "knowledge_freshness_pct": freshness,
        "knowledge_completeness_pct": completeness,
        "research_quality_pct": research_q,
        "scenario_consistency_pct": consistency,
        "trigger_uncertainty_pct": trigger_unc,
        "relationships_n": rel_n,
        "label": "High" if overall >= 80 else ("Medium" if overall >= 60 else "Low"),
        "note": "Probability = scenario likelihood; confidence = assessment certainty.",
    }


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
