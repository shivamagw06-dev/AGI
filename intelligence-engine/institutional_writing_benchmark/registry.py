"""Institutional writing benchmark — powered by Institutional Investor Curriculum."""

from __future__ import annotations

from typing import Any

from institutional_investor_curriculum import (
    EDITORIAL_BENCHMARKS,
    TARGET_BENCHMARK_COUNT,
    hall_of_fame_benchmark_ids,
    list_benchmarks as _list_iic_benchmarks,
    list_domains,
    get_benchmark as _get_iic_benchmark,
    get_domain,
    curriculum_summary,
    editorial_process,
)

# Primary benchmark registry — 1000 editorial benchmarks
BENCHMARK_QUESTIONS: tuple[dict[str, Any], ...] = EDITORIAL_BENCHMARKS


def list_benchmarks(
    *,
    category: str | None = None,
    domain: str | None = None,
    playbook: str | None = None,
    ticker: str | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """List editorial benchmarks; domain/category/playbook are aliases."""
    domain_filter = domain or category or playbook
    return _list_iic_benchmarks(domain=domain_filter, ticker=ticker, limit=limit)


def get_benchmark(benchmark_id: str) -> dict[str, Any] | None:
    return _get_iic_benchmark(benchmark_id)


def list_playbooks() -> list[dict[str, Any]]:
    """Back-compat — decision domains are the curriculum playbooks."""
    return list_domains()


def get_playbook(playbook: str) -> dict[str, Any] | None:
    return get_domain(playbook)


def phase2_expansion_plan() -> dict[str, Any]:
    """Curriculum phase 1 complete — 1000 benchmarks across 10 anchors."""
    return curriculum_summary()


def hall_of_fame_ids() -> list[str]:
    return hall_of_fame_benchmark_ids()
