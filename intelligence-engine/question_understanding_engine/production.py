"""Question Understanding Engine — production wiring."""

from __future__ import annotations

from typing import Any

from question_understanding_engine.research_brief import (
    build_research_brief,
    downstream_contract,
)
from question_understanding_engine.schema import (
    ARCHITECTURE_STATUS,
    LAYER,
    QUE_NAME,
    QUE_VERSION,
    TARGET_TAXONOMY_COUNT,
)
from question_understanding_engine.taxonomy import QUESTION_TAXONOMY
from question_understanding_engine.validation import validate_research_brief


def apply_question_understanding_engine(out: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """First deterministic stage — every answer starts here (QUE v1.1)."""
    if not isinstance(out, dict):
        out = {}

    query = str(kwargs.get("query") or out.get("query") or "")
    ticker = kwargs.get("ticker") or out.get("ticker")
    company = kwargs.get("company") or out.get("company")
    benchmark_id = kwargs.get("benchmark_id") or out.get("benchmark_id")

    domain = kwargs.get("domain")
    if benchmark_id and not domain:
        try:
            from institutional_writing_benchmark.registry import get_benchmark

            bench = get_benchmark(benchmark_id)
            if bench:
                domain = bench.get("domain")
                ticker = ticker or bench.get("ticker")
                company = company or bench.get("company")
                if not query:
                    query = bench.get("question") or ""
        except ImportError:
            pass

    brief = build_research_brief(
        query,
        ticker=ticker,
        company=company,
        benchmark_id=benchmark_id,
        domain=domain,
    )
    validation = validate_research_brief(brief)
    contract = downstream_contract(brief)

    que = {
        "enabled": True,
        "version": QUE_VERSION,
        "engine": QUE_NAME,
        "layer": LAYER,
        "architecture_status": ARCHITECTURE_STATUS,
        "deterministic": True,
        "llm": False,
        "pipeline_position": "first",
        "pipeline": (
            "user_question → question_understanding → research_brief → research_workflow → "
            "knowledge_objects → evidence_graph → response_planning → writing → editorial_review"
        ),
        "research_brief": brief,
        "question_understanding": brief,
        "downstream_contract": contract,
        "validation": validation,
        "passed": validation["passed"],
        "success_test": "Every downstream engine can answer what am I trying to accomplish without reading the original question.",
    }

    out["question_understanding_engine"] = que
    out["research_brief"] = brief
    out["question_understanding"] = brief
    out["downstream_contract"] = contract
    out["research_objective"] = brief.get("research_objective")
    out["decision_type"] = brief.get("decision_type")
    out["primary_investment_question"] = brief.get("primary_investment_question")
    out["required_information"] = brief.get("required_information")
    out["optional_information"] = brief.get("optional_information")
    out["irrelevant_information"] = brief.get("irrelevant_information")
    out["knowledge_gap"] = brief.get("knowledge_gap")
    out["top_research_questions"] = brief.get("top_research_questions")
    out["response_promise"] = brief.get("response_promise")
    out["success_criteria"] = brief.get("success_criteria")
    out["response_objective"] = brief.get("response_objective")
    out["expected_deliverable"] = brief.get("expected_deliverable")

    out["intent_resolution"] = {
        **(out.get("intent_resolution") or {}),
        "intent": brief.get("decision_type"),
        "research_objective": brief.get("research_objective"),
        "primary_investment_question": brief.get("primary_investment_question"),
        "investor_meaning": brief.get("investor_meaning"),
        "research_brief": brief,
        "que_v1_1": True,
    }

    return out


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "engine": QUE_NAME,
        "version": QUE_VERSION,
        "layer": LAYER,
        "feature": "research_brief_generator",
        "taxonomy_entries": len(QUESTION_TAXONOMY),
        "taxonomy_target": TARGET_TAXONOMY_COUNT,
        "deterministic": True,
        "llm": False,
        "pipeline_position": "first",
    }
