"""Financial Analyst IAI V1 brain — durable economic value creation from statements."""

from __future__ import annotations

from typing import Any

from institutional_analysts.financial.brain.archetypes import match_archetype
from institutional_analysts.financial.brain.benchmarks import benchmark
from institutional_analysts.financial.brain.case_library import match_cases
from institutional_analysts.financial.brain.financial_dna import build_dna, get_dna, put_dna
from institutional_analysts.financial.brain.frameworks import apply_all
from institutional_analysts.financial.brain.historical_outcomes import build_historical
from institutional_analysts.financial.brain.knowledge import knowledge_pack
from institutional_analysts.financial.brain.memory import (
    compare_trajectory,
    extract_prior,
    get_timeline,
    record_opinion,
)
from institutional_analysts.financial.brain.quality_checks import run_checklist
from institutional_analysts.financial.brain.reasoning import synthesize
from institutional_analysts.financial.brain.templates import build_structured_opinion
from institutional_analysts.financial.brain.validation import run_validation

IAI_FINANCIAL_VERSION = "iai-financial-v1.0.0"


def _confidence(
    raw: dict[str, float],
    *,
    archetype_bias: float = 0.0,
    accounting_ok: bool = True,
) -> dict[str, float]:
    evidence = float(raw.get("evidence") or 0.55)
    knowledge = float(raw.get("knowledge") or 0.55)
    freshness = float(raw.get("freshness") or 0.55)
    historical_coverage = float(raw.get("historical_coverage") or raw.get("coverage") or knowledge)
    accounting = float(raw.get("accounting") or (0.72 if accounting_ok else 0.42))
    reasoning = float(
        raw.get("reasoning")
        or min(0.95, max(0.2, (evidence + knowledge) / 2 + archetype_bias))
    )
    overall = float(
        raw.get("overall")
        or round(
            evidence * 0.25
            + accounting * 0.2
            + historical_coverage * 0.15
            + freshness * 0.15
            + reasoning * 0.25,
            4,
        )
    )
    return {
        "evidence": evidence,
        "accounting": accounting,
        "historical_coverage": historical_coverage,
        "freshness": freshness,
        "reasoning": reasoning,
        "knowledge": knowledge,
        "coverage": historical_coverage,
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
    archetype = match_archetype(evidence, frameworks)
    historical = build_historical(company=company, ticker=t, frameworks=frameworks, cases=cases)
    prior_dna = get_dna(t)
    dna = build_dna(
        company=company,
        ticker=t,
        evidence=evidence,
        frameworks=frameworks,
        prior_dna=prior_dna,
    )
    if t:
        put_dna(t, dna)
    benches = benchmark(evidence, frameworks)

    learning = {
        "cases": cases,
        "archetype": archetype,
        "historical": historical,
        "financial_dna": dna,
    }
    reasoned = synthesize(
        company=company,
        frameworks=frameworks,
        learning=learning,
        benchmarks=benches,
        previous=previous,
    )

    conf = _confidence(
        conf_in,
        archetype_bias=float((archetype.get("primary") or {}).get("confidence_bias") or 0),
        accounting_ok=bool((frameworks.get("earnings_quality") or {}).get("trusted")),
    )

    checklist = run_checklist(evidence, frameworks)
    executive = (
        checklist.get("explanation")
        if checklist.get("incomplete")
        else str(reasoned.get("executive_opinion") or "")
    )
    validation = run_validation(evidence=evidence, frameworks=frameworks, executive=executive)

    prior = extract_prior(previous)
    comparison = compare_trajectory(
        {
            "stance": reasoned.get("stance"),
            "component_trajectories": reasoned.get("component_trajectories"),
        },
        prior,
    )

    structured = build_structured_opinion(
        {
            "executive_opinion": executive,
            "financial_quality": reasoned.get("financial_quality"),
            "profitability": frameworks.get("profitability"),
            "growth_quality": frameworks.get("growth_quality"),
            "earnings_quality": frameworks.get("earnings_quality"),
            "cash_flow": frameworks.get("cash_flow"),
            "balance_sheet": frameworks.get("balance_sheet"),
            "capital_allocation": frameworks.get("capital_allocation"),
            "financial_dna": dna,
            "historical_trend": {
                "overall": (frameworks.get("trends") or {}).get("overall"),
                "components": reasoned.get("component_trajectories"),
                "narrative": historical.get("historical_narrative"),
                "timeline": historical.get("timeline"),
            },
            "benchmarking": benches,
            "assumptions": reasoned.get("assumptions"),
            "uncertainties": reasoned.get("uncertainties"),
            "missing_evidence": reasoned.get("missing_evidence") or checklist.get("failed_items"),
            "confidence": conf,
            "quality_checks": checklist,
        }
    )

    record_opinion(
        t,
        {
            "stance": reasoned.get("stance") if not checklist.get("incomplete") else "Neutral",
            "quality_grade": (reasoned.get("financial_quality") or {}).get("grade"),
            "reason": executive,
            "evidence": [e.get("claim") if isinstance(e, dict) else str(e) for e in (evidence.get("evidence_refs") or [])][:6],
            "trajectory": comparison.get("trajectory"),
            "component_trajectories": reasoned.get("component_trajectories"),
            "accuracy": None,
            "lessons": reasoned.get("lessons_learned"),
        },
    )

    stance_out = "Neutral" if checklist.get("incomplete") else str(reasoned.get("stance") or "Neutral")
    summary = executive

    return {
        "iai_version": IAI_FINANCIAL_VERSION,
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
        "financial_dna": dna,
        "benchmarks": benches,
        "structured_financial_opinion": structured,
        "executive_opinion": structured["executive_opinion"],
        "financial_quality": structured["financial_quality"],
        "profitability": structured["profitability"],
        "growth_quality": structured["growth_quality"],
        "earnings_quality": structured["earnings_quality"],
        "cash_flow": structured["cash_flow"],
        "balance_sheet": structured["balance_sheet"],
        "capital_allocation": structured["capital_allocation"],
        "historical_trend": structured["historical_trend"],
        "benchmarking": structured["benchmarking"],
        "assumptions": structured["assumptions"],
        "uncertainties": structured["uncertainties"],
        "missing_evidence": structured["missing_evidence"],
        "confidence": conf,
        "quality_checks": checklist,
        "validation": validation,
        "summary": summary,
        "institutional_financial_opinion": summary,
        "stance": stance_out,
        "strengths": list(reasoned.get("strengths") or []),
        "weaknesses": list(reasoned.get("weaknesses") or []),
        "reasoning": list(reasoned.get("reasoning_steps") or []),
        "unanswered_questions": list(reasoned.get("missing_evidence") or [])
        or [
            "Is incremental return on capital expanding or fading?",
            "How clean is cash conversion versus reported earnings?",
        ],
        "memory": {
            "trajectory": comparison.get("trajectory"),
            "what_changed": comparison.get("what_changed"),
            "opinion_timeline": get_timeline(t, limit=8),
            "lessons_learned": reasoned.get("lessons_learned"),
            "component_trajectories": reasoned.get("component_trajectories"),
        },
        "what_changed": list(comparison.get("what_changed") or []),
        "trajectory": comparison.get("trajectory") or historical.get("overall_trend") or "Stable",
        "ready_for_committee": bool(checklist.get("ready_for_committee", True)),
        "primary_question_answer": reasoned.get("primary_question_answer"),
    }


__all__ = ["think", "IAI_FINANCIAL_VERSION"]
