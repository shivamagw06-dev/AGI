"""Independent confidence calculation — not the same as probability."""

from __future__ import annotations

from typing import Any

from institutional_probability_confidence import traces
from institutional_probability_confidence.evidence_scoring import (
    contradiction_level,
    missing_level,
    score_analogue_strength,
    score_evidence_quality,
    score_freshness,
    score_historical_coverage,
    score_research_quality,
)
from institutional_probability_confidence.schema import ConfidenceBreakdown


def calculate_confidence(
    scenario_report: dict[str, Any],
    *,
    evidence_quality: dict[str, Any] | None = None,
    missing_evidence: list[str] | None = None,
    triggers: list[dict[str, Any]] | None = None,
) -> ConfidenceBreakdown:
    """Confidence reflects evidence quality / coverage / freshness — not scenario likelihood."""
    span = traces.begin(
        "confidence_calculation",
        meta={"entity": scenario_report.get("entity")},
    )
    eq = evidence_quality or score_evidence_quality(scenario_report)
    hist = score_historical_coverage(scenario_report)
    ana_pct, _ana_n = score_analogue_strength(scenario_report)
    fresh = score_freshness(scenario_report)
    completeness = ((scenario_report.get("completeness") or {}).get("bundle") or {})
    comp_score = int(round(float(completeness.get("score") or 0.55) * 100))
    if comp_score < 40:
        comp_score = max(comp_score, hist - 10)

    contra_n = len(scenario_report.get("contradictions") or [])
    contra_lvl = contradiction_level(contra_n)
    # Contradiction reduces confidence but does not erase it
    contra_score = 92 if contra_lvl == "Low" else 78 if contra_lvl == "Moderate" else 60

    missing = missing_evidence or []
    miss_lvl = missing_level(len(missing))
    miss_score = 90 if miss_lvl == "Low" else 72 if miss_lvl == "Moderate" else 55

    triggers = triggers or []
    watching = sum(1 for t in triggers if str(t.get("status") or "").lower() in {"watching", "scheduled"})
    trigger_uncertainty = max(40, 95 - watching * 8)

    research = score_research_quality(scenario_report)

    # Scenario consistency: all three present with narratives
    scenarios = scenario_report.get("scenarios") or []
    types = {s.get("type") for s in scenarios}
    consistency = 95 if types >= {"Bull", "Base", "Bear"} and all(s.get("narrative") for s in scenarios) else 70

    # Weighted overall — independent of probability mass on any scenario
    overall = (
        0.22 * float(eq.get("score_pct") or 70)
        + 0.14 * hist
        + 0.12 * ana_pct
        + 0.14 * fresh
        + 0.12 * comp_score
        + 0.08 * contra_score
        + 0.06 * miss_score
        + 0.05 * trigger_uncertainty
        + 0.04 * research
        + 0.03 * consistency
    )
    overall_pct = int(round(max(35, min(99, overall))))

    breakdown = ConfidenceBreakdown(
        overall_pct=overall_pct,
        evidence_quality_pct=int(eq.get("score_pct") or 0),
        historical_coverage_pct=hist,
        historical_analogue_strength_pct=ana_pct,
        knowledge_freshness_pct=fresh,
        knowledge_completeness_pct=comp_score,
        contradiction_level=contra_lvl,
        missing_evidence_level=miss_lvl,
        trigger_uncertainty_pct=int(trigger_uncertainty),
        research_quality_pct=research,
        scenario_consistency_pct=consistency,
        components={
            "weights": {
                "evidence_quality": 0.22,
                "historical_coverage": 0.14,
                "analogue_strength": 0.12,
                "freshness": 0.14,
                "completeness": 0.12,
                "contradictions": 0.08,
                "missing_evidence": 0.06,
                "trigger_uncertainty": 0.05,
                "research": 0.04,
                "consistency": 0.03,
            },
            "rule": "Confidence is independent of which scenario is most probable",
        },
    )
    traces.end(span, output={"overall_pct": overall_pct, "evidence_quality": eq.get("score_pct")})
    return breakdown


def per_scenario_confidence(
    scenario: dict[str, Any],
    *,
    overall: ConfidenceBreakdown,
    scenario_name: str,
) -> int:
    """Slight per-scenario confidence modulation without coupling to probability."""
    base = overall.overall_pct
    ev_n = len(scenario.get("supporting_evidence") or [])
    adj = 0
    if ev_n >= 4:
        adj += 3
    elif ev_n <= 1:
        adj -= 5
    # Base case typically best supported by institutional priors
    if scenario_name == "Base":
        adj += 2
    if scenario_name == "Bull":
        adj -= 1
    if scenario_name == "Bear":
        adj -= 2
    return int(max(35, min(99, base + adj)))
