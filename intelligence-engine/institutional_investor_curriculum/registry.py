"""Institutional Investor Curriculum — registry API."""

from __future__ import annotations

from typing import Any

from institutional_investor_curriculum.benchmarks import (
    EDITORIAL_BENCHMARKS,
    hall_of_fame_benchmark_ids,
    weekly_review_sample,
)
from institutional_investor_curriculum.domains import UNIVERSAL_QUESTIONS
from institutional_investor_curriculum.schema import (
    ANCHOR_COMPANIES,
    CURRICULUM_NAME,
    CURRICULUM_VERSION,
    DECISION_DOMAINS,
    DOMAIN_EDITORIAL_OBJECTIVES,
    DOMAIN_PURPOSES,
    DOMAIN_TITLES,
    EDITORIAL_PRINCIPLES,
    EDITORIAL_WORKFLOW,
    HALL_OF_FAME_COUNT,
    SUCCESS_QUOTE,
    TARGET_BENCHMARK_COUNT,
    UNIVERSAL_QUESTION_COUNT,
)


def list_domains() -> list[dict[str, Any]]:
    return [
        {
            "domain": slug,
            "title": DOMAIN_TITLES[slug],
            "domain_number": i + 1,
            "purpose": DOMAIN_PURPOSES[slug],
            "editorial_objective": DOMAIN_EDITORIAL_OBJECTIVES[slug],
            "universal_question_ids": [
                q["id"] for q in UNIVERSAL_QUESTIONS if q["domain"] == slug
            ],
        }
        for i, slug in enumerate(DECISION_DOMAINS)
    ]


def get_domain(domain: str) -> dict[str, Any] | None:
    questions = [q for q in UNIVERSAL_QUESTIONS if q["domain"] == domain]
    if not questions:
        return None
    return {
        "domain": domain,
        "title": DOMAIN_TITLES.get(domain, domain),
        "purpose": DOMAIN_PURPOSES.get(domain, ""),
        "editorial_objective": DOMAIN_EDITORIAL_OBJECTIVES.get(domain, ""),
        "universal_questions": questions,
    }


def list_universal_questions(*, domain: str | None = None) -> list[dict[str, Any]]:
    items = list(UNIVERSAL_QUESTIONS)
    if domain:
        items = [q for q in items if q["domain"] == domain]
    return items


def list_benchmarks(
    *,
    domain: str | None = None,
    ticker: str | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    items = list(EDITORIAL_BENCHMARKS)
    if domain:
        items = [b for b in items if b.get("domain") == domain]
    if ticker:
        items = [b for b in items if b.get("ticker") == ticker]
    return items[:limit]


def get_benchmark(benchmark_id: str) -> dict[str, Any] | None:
    for b in EDITORIAL_BENCHMARKS:
        if b.get("id") == benchmark_id:
            return dict(b)
    return None


def get_universal_question(universal_id: str) -> dict[str, Any] | None:
    for q in UNIVERSAL_QUESTIONS:
        if q.get("id") == universal_id:
            return dict(q)
    return None


def curriculum_summary() -> dict[str, Any]:
    return {
        "curriculum": CURRICULUM_NAME,
        "version": CURRICULUM_VERSION,
        "structure": "10 domains → 100 universal questions → 10 anchors → 1000 benchmarks",
        "decision_domains": len(DECISION_DOMAINS),
        "universal_questions": UNIVERSAL_QUESTION_COUNT,
        "anchor_companies": len(ANCHOR_COMPANIES),
        "editorial_benchmarks": len(EDITORIAL_BENCHMARKS),
        "target_benchmarks": TARGET_BENCHMARK_COUNT,
        "hall_of_fame_size": HALL_OF_FAME_COUNT,
        "editorial_workflow": list(EDITORIAL_WORKFLOW),
        "editorial_principles": list(EDITORIAL_PRINCIPLES),
        "success_metric": SUCCESS_QUOTE,
    }


def editorial_process() -> dict[str, Any]:
    """Recommended weekly editorial refinement loop."""
    return {
        "cadence": "weekly",
        "steps": [
            "Run 100 benchmark questions",
            "Read every answer manually",
            "Improve only the weakest responses",
            "Add 1–3 editorial rules",
            "Re-run Hall of Fame",
            "Repeat",
        ],
        "weekly_sample_size": 100,
        "rule_additions_per_week": "1–3",
        "architecture_changes": False,
    }
