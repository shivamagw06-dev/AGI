"""Institutional writing benchmark package."""

from institutional_investor_curriculum import (
    CURRICULUM_NAME,
    CURRICULUM_VERSION,
    EDITORIAL_BENCHMARKS,
    EDITORIAL_PRINCIPLES,
    TARGET_BENCHMARK_COUNT,
    UNIVERSAL_QUESTION_COUNT,
    curriculum_summary,
    editorial_process,
    list_domains,
    list_universal_questions,
)
from institutional_investor_curriculum.registry import get_domain
from institutional_writing_benchmark.hall_of_fame import (
    HALL_OF_FAME_COUNT,
    compare_and_maybe_update,
    hall_of_fame_ids,
    load_hall_of_fame,
)
from institutional_writing_benchmark.registry import (
    BENCHMARK_QUESTIONS,
    get_benchmark,
    get_playbook,
    list_benchmarks,
    list_playbooks,
    phase2_expansion_plan,
)
from institutional_writing_benchmark.schema import (
    ANCHOR_COMPANIES,
    BENCHMARK_CATEGORIES,
    DECISION_DOMAINS,
    DOMAIN_TITLES,
    LIFECYCLE_PLAYBOOKS,
    PLAYBOOK_COUNT,
    PLAYBOOK_TITLES,
)

__all__ = [
    "ANCHOR_COMPANIES",
    "BENCHMARK_CATEGORIES",
    "BENCHMARK_QUESTIONS",
    "CURRICULUM_NAME",
    "CURRICULUM_VERSION",
    "DECISION_DOMAINS",
    "DOMAIN_TITLES",
    "EDITORIAL_BENCHMARKS",
    "EDITORIAL_PRINCIPLES",
    "HALL_OF_FAME_COUNT",
    "LIFECYCLE_PLAYBOOKS",
    "PLAYBOOK_COUNT",
    "PLAYBOOK_TITLES",
    "TARGET_BENCHMARK_COUNT",
    "UNIVERSAL_QUESTION_COUNT",
    "compare_and_maybe_update",
    "curriculum_summary",
    "editorial_process",
    "get_benchmark",
    "get_domain",
    "get_playbook",
    "hall_of_fame_ids",
    "list_benchmarks",
    "list_domains",
    "list_playbooks",
    "list_universal_questions",
    "load_hall_of_fame",
    "phase2_expansion_plan",
]
