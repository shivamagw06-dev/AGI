"""Valuation Analyst IAI V1 — expectations, intrinsic value, margin of safety."""

from __future__ import annotations

from typing import Any

from institutional_analysts.valuation.brain.archetypes import match_archetype
from institutional_analysts.valuation.brain.benchmarks import benchmark
from institutional_analysts.valuation.brain.case_library import match_cases
from institutional_analysts.valuation.brain.frameworks import apply_all
from institutional_analysts.valuation.brain.historical_outcomes import build_historical
from institutional_analysts.valuation.brain.knowledge import knowledge_pack
from institutional_analysts.valuation.brain.memory import compare, extract_prior, get_timeline, record_opinion
from institutional_analysts.valuation.brain.quality_checks import run_checklist
from institutional_analysts.valuation.brain.reasoning import synthesize
from institutional_analysts.valuation.brain.templates import build_structured_opinion
from institutional_analysts.valuation.brain.validation import run_validation
from institutional_analysts.valuation.brain.valuation_dna import build_dna, get_dna, put_dna

IAI_VALUATION_VERSION = "iai-valuation-v1.0.0"


def _confidence(raw: dict[str, float], *, bias: float = 0.0) -> dict[str, float]:
    evidence = float(raw.get("evidence") or 0.54)
    knowledge = float(raw.get("knowledge") or 0.54)
    freshness = float(raw.get("freshness") or 0.52)
    valuation_coverage = float(raw.get("valuation_coverage") or raw.get("coverage") or knowledge)
    historical_coverage = float(raw.get("historical_coverage") or valuation_coverage)
    reasoning = float(raw.get("reasoning") or min(0.95, max(0.2, (evidence + knowledge) / 2 + bias)))
    overall = float(
        raw.get("overall")
        or round(
            evidence * 0.25
            + valuation_coverage * 0.2
            + historical_coverage * 0.15
            + reasoning * 0.25
            + freshness * 0.15,
            4,
        )
    )
    return {
        "evidence": evidence,
        "valuation_coverage": valuation_coverage,
        "historical_coverage": historical_coverage,
        "reasoning": reasoning,
        "freshness": freshness,
        "knowledge": knowledge,
        "coverage": valuation_coverage,
        "overall": max(0.05, min(0.99, overall)),
    }


def think(
    *,
    company: str,
    evidence: dict[str, Any],
    previous: dict[str, Any] | None = None,
    confidence: dict[str, float] | None = None,
    ticker: str | None = None,
) -> dict[str, Any]:
    conf_in = confidence if isinstance(confidence, dict) else {}
    t = (ticker or evidence.get("ticker") or "").upper() or None

    frameworks = apply_all(evidence)
    cases = match_cases(evidence, frameworks)
    prior_dna = get_dna(t)
    dna = build_dna(company=company, ticker=t, evidence=evidence, frameworks=frameworks, prior=prior_dna)
    if t:
        put_dna(t, dna)
    archetype = match_archetype(dna, frameworks)
    historical = build_historical(company=company, frameworks=frameworks, cases=cases)
    benches = benchmark(evidence, frameworks)

    learning = {
        "cases": cases,
        "valuation_dna": dna,
        "archetype": archetype,
        "historical": historical,
    }
    reasoned = synthesize(
        company=company,
        evidence=evidence,
        frameworks=frameworks,
        learning=learning,
        benchmarks=benches,
    )
    conf = _confidence(conf_in, bias=float((archetype.get("primary") or {}).get("confidence_bias") or 0))
    checklist = run_checklist(evidence, frameworks)
    executive = checklist.get("explanation") if checklist.get("incomplete") else str(reasoned.get("executive_opinion") or "")
    validation = run_validation(evidence=evidence, frameworks=frameworks, executive=executive)

    prior = extract_prior(previous)
    comparison = compare(str(reasoned.get("stance") or "Neutral"), prior, list(dna.get("dna_changes") or []))

    structured = build_structured_opinion(
        {
            "executive_opinion": executive,
            "intrinsic_value_view": frameworks.get("intrinsic_value"),
            "market_expectations": frameworks.get("market_expectations"),
            "valuation_quality": reasoned.get("valuation_quality"),
            "multiple_analysis": frameworks.get("multiple_analysis"),
            "dcf_discussion": frameworks.get("dcf_discussion"),
            "relative_valuation": frameworks.get("relative_valuation"),
            "historical_valuation": frameworks.get("historical_valuation"),
            "margin_of_safety": frameworks.get("margin_of_safety"),
            "valuation_dna": dna,
            "historical_trend": {
                "narrative": historical.get("historical_narrative"),
                "current_vs_history": historical.get("current_vs_history"),
                "expectation_trend": historical.get("expectation_trend"),
            },
            "peer_comparison": frameworks.get("peer_comparison"),
            "assumptions": reasoned.get("assumptions"),
            "uncertainties": reasoned.get("uncertainties"),
            "missing_evidence": reasoned.get("missing_evidence") or checklist.get("failed_items"),
            "confidence": conf,
            "quality_checks": checklist,
        }
    )

    stance_out = "Neutral" if checklist.get("incomplete") else str(reasoned.get("stance") or "Neutral")
    record_opinion(
        t,
        {
            "stance": stance_out,
            "reason": executive,
            "pe": evidence.get("pe"),
            "margin_of_safety": evidence.get("margin_of_safety"),
            "profile": dna.get("profile"),
            "trajectory": comparison.get("trajectory"),
            "accuracy": None,
            "lessons": reasoned.get("lessons_learned"),
        },
    )

    return {
        "iai_version": IAI_VALUATION_VERSION,
        "knowledge": knowledge_pack(t),
        "learning_chain": [
            "knowledge",
            "frameworks",
            "case_studies",
            "historical_outcomes",
            "lessons_learned",
            "reasoning",
            "opinion",
        ],
        "frameworks_applied": list(frameworks.get("applied") or []),
        "framework_detail": frameworks,
        "case_studies": cases,
        "archetype": archetype,
        "historical_outcomes": historical,
        "lessons_learned": reasoned.get("lessons_learned"),
        "valuation_dna": dna,
        "benchmarks": benches,
        "structured_valuation_opinion": structured,
        "executive_opinion": structured["executive_opinion"],
        "intrinsic_value_view": structured["intrinsic_value_view"],
        "market_expectations": structured["market_expectations"],
        "valuation_quality": structured["valuation_quality"],
        "multiple_analysis": structured["multiple_analysis"],
        "dcf_discussion": structured["dcf_discussion"],
        "relative_valuation": structured["relative_valuation"],
        "historical_valuation": structured["historical_valuation"],
        "margin_of_safety": structured["margin_of_safety"],
        "historical_trend": structured["historical_trend"],
        "peer_comparison": structured["peer_comparison"],
        "assumptions": structured["assumptions"],
        "uncertainties": structured["uncertainties"],
        "missing_evidence": structured["missing_evidence"],
        "confidence": conf,
        "quality_checks": checklist,
        "validation": validation,
        "summary": executive,
        "institutional_valuation_opinion": executive,
        "stance": stance_out,
        "strengths": list(reasoned.get("strengths") or []),
        "weaknesses": list(reasoned.get("weaknesses") or []),
        "reasoning": list(reasoned.get("reasoning_steps") or []),
        "unanswered_questions": list(reasoned.get("missing_evidence") or [])
        or [
            "How much growth is already discounted in today's multiple?",
            "What margin of safety remains if earnings undershoot?",
        ],
        "memory": {
            "trajectory": comparison.get("trajectory"),
            "what_changed": comparison.get("what_changed"),
            "opinion_timeline": get_timeline(t, limit=8),
            "lessons_learned": reasoned.get("lessons_learned"),
        },
        "what_changed": list(comparison.get("what_changed") or []),
        "trajectory": comparison.get("trajectory") or "Stable",
        "ready_for_committee": bool(checklist.get("ready_for_committee", True)),
        "primary_question_answer": reasoned.get("primary_question_answer"),
        # section helpers for analyst.py
        "scenario_valuation": frameworks.get("scenario_valuation"),
    }


__all__ = ["think", "IAI_VALUATION_VERSION"]
