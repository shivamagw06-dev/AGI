"""Generate 1000 editorial benchmarks from universal curriculum × anchor companies."""

from __future__ import annotations

from typing import Any

from institutional_investor_curriculum.domains import UNIVERSAL_QUESTIONS
from institutional_investor_curriculum.schema import (
    ANCHOR_COMPANIES,
    DOMAIN_TITLES,
    TARGET_BENCHMARK_COUNT,
    UNIVERSAL_QUESTION_COUNT,
)


def instantiate_question(template: str, company: str) -> str:
    return template.format(company=company)


def _build_benchmarks() -> tuple[dict[str, Any], ...]:
    items: list[dict[str, Any]] = []
    seq = 0

    for ticker, company_name in ANCHOR_COMPANIES:
        for uq in UNIVERSAL_QUESTIONS:
            seq += 1
            question = instantiate_question(uq["template"], company_name)
            items.append({
                "id": f"IIC_{seq:04d}",
                "universal_id": uq["id"],
                "question": question,
                "template": uq["template"],
                "domain": uq["domain"],
                "domain_title": DOMAIN_TITLES[uq["domain"]],
                "domain_number": uq["domain_number"],
                "question_in_domain": uq["question_in_domain"],
                "universal_number": int(uq["id"].split("_")[1]),
                "ticker": ticker,
                "company": company_name,
                "editorial_objective": uq["editorial_objective"],
                "curriculum": "institutional_investor_v1",
                "company_specific": True,
                "latest_score": None,
                "forward_without_editing": None,
                "revision_history": [],
            })

    assert len(items) == TARGET_BENCHMARK_COUNT
    assert len(items) == UNIVERSAL_QUESTION_COUNT * len(ANCHOR_COMPANIES)
    return tuple(items)


EDITORIAL_BENCHMARKS: tuple[dict[str, Any], ...] = _build_benchmarks()


def hall_of_fame_benchmark_ids() -> list[str]:
    """First 100 benchmarks — universal curriculum on TCS anchor."""
    return [b["id"] for b in EDITORIAL_BENCHMARKS if b["ticker"] == "TCS"]


def weekly_review_sample(limit: int = 100) -> list[dict[str, Any]]:
    """Sample for weekly editorial review — first N benchmarks."""
    return list(EDITORIAL_BENCHMARKS[:limit])
