"""Apply Editorial Excellence Program — review loop after institutional writing."""

from __future__ import annotations

from typing import Any

from editorial_excellence.reports import monthly_report, weekly_review
from editorial_excellence.rules import rule_count
from editorial_excellence.schema import (
    ARCHITECTURE_STATUS,
    LAYER,
    PROGRAM_VERSION,
    PROGRAMME,
)
from editorial_excellence.scorecard import quality_gates, score_editorial
from editorial_excellence.workspace import build_review_workspace
from institutional_investor_curriculum.schema import CURRICULUM_NAME, CURRICULUM_VERSION
from institutional_writing_benchmark.schema import TARGET_BENCHMARK_COUNT


def apply_editorial_excellence(out: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Research → Planning → Writing → Editorial Review → Rule Improvement."""
    if not isinstance(out, dict):
        return out

    query = str(kwargs.get("query") or out.get("query") or "")
    benchmark_id = kwargs.get("benchmark_id") or out.get("benchmark_id")

    editorial = score_editorial(out)
    gates = quality_gates(out, editorial)
    workspace = build_review_workspace(out, benchmark_id=benchmark_id)

    # Hall of Fame update when benchmark_id provided
    hof_result = None
    if benchmark_id:
        from institutional_writing_benchmark.hall_of_fame import compare_and_maybe_update

        text = workspace.get("current_response_excerpt") or ""
        hof_result = compare_and_maybe_update(
            benchmark_id,
            question=query,
            response_text=text,
            editorial_score=editorial.get("overall_editorial_score", 0),
            forward_rating=editorial.get("forward_without_editing", "REWRITE"),
        )

    program = {
        "enabled": True,
        "version": PROGRAM_VERSION,
        "programme": PROGRAMME,
        "layer": LAYER,
        "architecture_status": ARCHITECTURE_STATUS,
        "pipeline": "research → response_planning → writing → editorial_review → rule_improvement",
        "constitution_stable": True,
        "editorial_rules_evolve": True,
        "editorial_scorecard": editorial,
        "quality_gates": gates,
        "review_workspace": workspace,
        "forward_test": editorial.get("forward_test"),
        "forward_without_editing": editorial.get("forward_without_editing"),
        "rule_count": rule_count(),
        "hall_of_fame_update": hof_result,
    }

    out["editorial_excellence"] = program
    out["editorial_scorecard"] = editorial.get("scorecard")
    out["editorial_score"] = editorial.get("overall_editorial_score")
    out["forward_without_editing"] = editorial.get("forward_without_editing")
    out["editorial_quality_gates"] = gates
    out["editorial_review_workspace"] = workspace
    return out


def health() -> dict[str, Any]:
    from institutional_writing_benchmark.hall_of_fame import hall_of_fame_ids
    from institutional_writing_benchmark.registry import BENCHMARK_QUESTIONS

    return {
        "status": "ok",
        "programme": PROGRAMME,
        "version": PROGRAM_VERSION,
        "layer": LAYER,
        "architecture_status": ARCHITECTURE_STATUS,
        "benchmark_questions": len(BENCHMARK_QUESTIONS),
        "benchmark_target": TARGET_BENCHMARK_COUNT,
        "hall_of_fame_size": len(hall_of_fame_ids()),
        "editorial_rules": rule_count(),
        "llm": False,
        "deterministic": True,
    }


def run_weekly_review(results: list[dict[str, Any]]) -> dict[str, Any]:
    return weekly_review(results)


def run_monthly_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    return monthly_report(results)
