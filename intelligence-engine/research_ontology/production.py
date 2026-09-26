"""RQ1 Research Ontology production facade — Sprint 1 classify-only."""

from __future__ import annotations

from typing import Any

from research_ontology.classifier import classify_question
from research_ontology.flags import flags_dict, is_enabled
from research_ontology.schema import (
    ARCHITECTURE_STATUS,
    BENCHMARK_QUESTIONS,
    MANDATORY_OUTPUT_FIELDS,
    PROGRAMME,
    PROGRAMME_SHORT,
    RQ1_VERSION,
    SPRINT,
    SPRINT_NAME,
    constitution_dict,
)

# Expected primary intent labels for Sprint 1 acceptance
BENCHMARK_EXPECTATIONS: dict[str, str] = {
    "Should I buy HDFC Bank?": "Company Research",
    "Is Nifty IT expensive versus history?": "Index Research",
    "Compare TCS vs Infosys.": "Company Comparison",
    "What happens if RBI cuts rates?": "Macro Research",
    "Explain ROIC.": "Educational",
    "Should I add Reliance to my portfolio?": "Portfolio Research",
    "Best FMCG companies with high ROIC.": "Screening",
    "Summarise today's Infosys earnings.": "News",
}


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": RQ1_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "not_a_top_level_intelligence_layer": True,
        "no_layer_execution": True,
        "no_analyst_execution": True,
        "constitution_locked": True,
    }


def constitution() -> dict[str, Any]:
    return {"enabled": is_enabled(), **constitution_dict()}


def classify(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "rq1_version": RQ1_VERSION}
    body = payload or {}
    question = str(body.get("question") or body.get("q") or "").strip()
    if not question:
        return {"ok": False, "error": "question is required", "rq1_version": RQ1_VERSION}
    out = classify_question(question)
    return {"enabled": True, **out}


def dashboard() -> dict[str, Any]:
    samples = []
    for q in BENCHMARK_QUESTIONS:
        row = classify_question(q)
        samples.append(
            {
                "question": q,
                "primary_intent": row.get("primary_intent"),
                "entity": row.get("entity"),
                "entity_type": row.get("entity_type"),
                "objective": row.get("research_objective"),
                "confidence_pct": row.get("confidence_pct"),
                "requires_clarification": row.get("requires_clarification"),
                "next_stage": row.get("next_stage"),
            }
        )
    gates = quality_gates()
    return {
        "programme": PROGRAMME,
        "rq1_version": RQ1_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "mandatory_output_fields": list(MANDATORY_OUTPUT_FIELDS),
        "benchmark_questions": list(BENCHMARK_QUESTIONS),
        "benchmark_samples": samples,
        "quality_gates": gates,
        "website_surfaces": ["/admin/intent-intelligence"],
        "api_prefix": "/v1/research-ontology",
        "law": "Classify research type before any analyst or intelligence layer executes.",
    }


def quality_gates() -> dict[str, Any]:
    results = []
    passed = 0
    for q, expected in BENCHMARK_EXPECTATIONS.items():
        row = classify_question(q)
        ok = row.get("primary_intent") == expected and row.get("executed_layers") == []
        # clarification case for Tata is separate; benchmarks should not clarify
        ok = ok and not row.get("requires_clarification")
        if ok:
            passed += 1
        results.append(
            {
                "question": q,
                "expected_primary": expected,
                "actual_primary": row.get("primary_intent"),
                "entity": row.get("entity"),
                "confidence_pct": row.get("confidence_pct"),
                "passed": ok,
                "executed_layers": row.get("executed_layers"),
                "executed_analysts": row.get("executed_analysts"),
            }
        )

    # Ambiguity gate
    amb = classify_question("Should I buy Tata?")
    amb_ok = bool(amb.get("requires_clarification")) and amb.get("executed_layers") == []
    results.append(
        {
            "question": "Should I buy Tata?",
            "expected_primary": "Company Research (clarify)",
            "actual_primary": amb.get("primary_intent"),
            "entity": amb.get("entity"),
            "confidence_pct": amb.get("confidence_pct"),
            "passed": amb_ok,
            "requires_clarification": amb.get("requires_clarification"),
            "possible_matches": amb.get("possible_matches"),
            "executed_layers": amb.get("executed_layers"),
        }
    )
    if amb_ok:
        passed += 1

    total = len(results)
    return {
        "ok": passed == total,
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "results": results,
        "rule": "Sprint 1 complete only if benchmarks classify without layer/analyst execution.",
    }


def soft_slice_for_ask_agi(question: str) -> dict[str, Any]:
    """Additive metadata for Ask AGI — does not trigger layers."""
    if not is_enabled():
        return {}
    row = classify_question(question or "")
    return {
        "research_ontology": {
            "enabled": True,
            "version": RQ1_VERSION,
            "sprint": SPRINT,
            "primary_intent": row.get("primary_intent"),
            "primary_intent_id": row.get("primary_intent_id"),
            "secondary_intents": row.get("secondary_intents"),
            "entity": row.get("entity"),
            "entity_type": row.get("entity_type"),
            "research_objective": row.get("research_objective"),
            "confidence": row.get("confidence"),
            "requires_clarification": row.get("requires_clarification"),
            "next_stage": row.get("next_stage"),
            "no_layer_execution": True,
        }
    }
