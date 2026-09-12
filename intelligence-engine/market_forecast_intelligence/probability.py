"""Evidence-weighted market scenario probabilities + confidence."""

from __future__ import annotations

from typing import Any

from market_forecast_intelligence.schema import MarketForecastBundle, MarketScenario
from market_forecast_intelligence.templates import horizon_tilt


def assign_probabilities(
    scenarios: list[MarketScenario],
    bundle: MarketForecastBundle,
) -> dict[str, int]:
    """Institutional priors tilted by analogues, CMKTP tip, macro/sector inheritance → sum 100."""
    weights = {"Bull": 22.0, "Base": 56.0, "Bear": 22.0}

    for ana in bundle.analogues[:5]:
        label = str(ana.get("matched_label") or ana.get("matched_period") or "").lower()
        outcome = str(ana.get("historical_outcome") or ana.get("equity_outcome") or "").lower()
        score = float(ana.get("similarity_score") or 0)
        boost = min(6.0, score / 25.0)
        blob = f"{label} {outcome}"
        if any(
            k in blob
            for k in ("recovery", "bull", "liquidity", "2021", "2003", "expansion", "cushion")
        ):
            weights["Bull"] += boost * 0.6
            weights["Base"] += boost * 0.4
        if any(
            k in blob
            for k in ("shock", "stress", "crash", "correction", "2022", "2013", "taper", "inflation")
        ):
            weights["Bear"] += boost * 0.7
            weights["Base"] += boost * 0.2
        if any(k in blob for k in ("covid", "gfc", "crisis", "2008", "2020", "capitulation")):
            weights["Bear"] += boost * 0.5

    cur = bundle.current_market or {}
    regime = str(
        cur.get("market_regime")
        or cur.get("regime")
        or (bundle.current_regime or {}).get("regime_label")
        or ""
    ).lower()
    if any(k in regime for k in ("bull", "recovery", "expansion")):
        weights["Bull"] += 4.0
        weights["Bear"] -= 2.0
    elif any(k in regime for k in ("bear", "capitulation", "correction", "distribution")):
        weights["Bear"] += 5.0
        weights["Bull"] -= 2.0
    elif "sideways" in regime:
        weights["Base"] += 3.0

    macro = bundle.macro_forecast_tip or {}
    mdist = macro.get("probability_distribution") or {}
    if mdist:
        if int(mdist.get("Bull") or 0) >= 28:
            weights["Bull"] += 3.0
        if int(mdist.get("Bear") or 0) >= 28:
            weights["Bear"] += 3.0
        if int(mdist.get("Base") or 0) >= 55:
            weights["Base"] += 2.0

    sector = bundle.sector_forecast_tip or {}
    sdist = sector.get("probability_distribution") or {}
    if sdist:
        if int(sdist.get("Bull") or 0) >= 28:
            weights["Bull"] += 2.0
        if int(sdist.get("Bear") or 0) >= 28:
            weights["Bear"] += 2.0

    horizon = bundle.horizon or "6 Months"
    for k in ("Bull", "Base", "Bear"):
        weights[k] += horizon_tilt(horizon, k)  # type: ignore[arg-type]

    if bundle.completeness_pct < 60:
        weights["Base"] += 4.0
        weights["Bull"] -= 2.0
        weights["Bear"] -= 2.0

    for k in weights:
        weights[k] = max(5.0, weights[k])

    total = sum(weights.values())
    raw = {k: 100.0 * v / total for k, v in weights.items()}
    bull = int(round(raw["Bull"]))
    bear = int(round(raw["Bear"]))
    base = 100 - bull - bear
    if base < 5:
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
    scenarios: list[MarketScenario],
    bundle: MarketForecastBundle,
) -> dict[str, Any]:
    """Independent confidence — not the same as probability."""
    evidence_n = sum(len(s.supporting_evidence) for s in scenarios)
    analogue_n = len(bundle.analogues)
    rel_n = len(bundle.relationships)
    completeness = bundle.completeness_pct

    evidence_q = min(95, 50 + evidence_n * 3 + (10 if bundle.current_market else 0))
    hist_cov = min(95, 40 + analogue_n * 8 + (15 if bundle.historical_tip else 0))
    analogue_str = 0
    if bundle.analogues:
        top = max(float(a.get("similarity_score") or 0) for a in bundle.analogues)
        analogue_str = int(min(95, top))
    freshness = 85 if "CMKTP" in bundle.sources else 55
    research_q = 80 if bundle.research else 60
    consistency = 92 if {s.scenario for s in scenarios} == {"Bull", "Base", "Bear"} else 70
    macro_inherit = 88 if bundle.macro_forecast_tip else 60
    sector_inherit = 85 if bundle.sector_forecast_tip else 60
    trigger_unc = 35 if len(bundle.monitoring) >= 2 else 55

    overall = int(
        round(
            0.18 * evidence_q
            + 0.14 * hist_cov
            + 0.14 * analogue_str
            + 0.12 * freshness
            + 0.12 * completeness
            + 0.10 * research_q
            + 0.08 * consistency
            + 0.06 * macro_inherit
            + 0.06 * sector_inherit
        )
    )
    overall = max(40, min(95, overall))

    for sc in scenarios:
        adj = 0
        if sc.scenario == "Base":
            adj = 4
        elif sc.scenario == "Bull":
            adj = -2 if (bundle.analogues and "shock" in str(bundle.analogues[0]).lower()) else 0
        elif sc.scenario == "Bear":
            adj = 2 if analogue_str >= 80 and "stress" in str(bundle.analogues).lower() else -1
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
        "macro_inheritance_pct": macro_inherit,
        "sector_inheritance_pct": sector_inherit,
        "trigger_uncertainty_pct": trigger_unc,
        "relationships_n": rel_n,
        "label": "High" if overall >= 80 else ("Medium" if overall >= 60 else "Low"),
        "note": "Probability = scenario likelihood; confidence = assessment certainty.",
    }
