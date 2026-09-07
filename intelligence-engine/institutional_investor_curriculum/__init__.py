"""AGI Institutional Investor Curriculum v1.0 — lifelong editorial benchmark."""

from institutional_investor_curriculum.benchmarks import (
    EDITORIAL_BENCHMARKS,
    hall_of_fame_benchmark_ids,
    instantiate_question,
    weekly_review_sample,
)
from institutional_investor_curriculum.domains import UNIVERSAL_QUESTIONS
from institutional_investor_curriculum.registry import (
    curriculum_summary,
    editorial_process,
    get_benchmark,
    get_domain,
    get_universal_question,
    list_benchmarks,
    list_domains,
    list_universal_questions,
)
from institutional_investor_curriculum.schema import (
    ANCHOR_COMPANIES,
    CURRICULUM_NAME,
    CURRICULUM_SCORECARD,
    CURRICULUM_VERSION,
    DECISION_DOMAINS,
    DOMAIN_TITLES,
    EDITORIAL_PRINCIPLES,
    EDITORIAL_WORKFLOW,
    HALL_OF_FAME_COUNT,
    TARGET_BENCHMARK_COUNT,
    UNIVERSAL_QUESTION_COUNT,
)

__all__ = [
    "ANCHOR_COMPANIES",
    "CURRICULUM_NAME",
    "CURRICULUM_SCORECARD",
    "CURRICULUM_VERSION",
    "DECISION_DOMAINS",
    "DOMAIN_TITLES",
    "EDITORIAL_BENCHMARKS",
    "EDITORIAL_PRINCIPLES",
    "EDITORIAL_WORKFLOW",
    "HALL_OF_FAME_COUNT",
    "TARGET_BENCHMARK_COUNT",
    "UNIVERSAL_QUESTION_COUNT",
    "UNIVERSAL_QUESTIONS",
    "curriculum_summary",
    "editorial_process",
    "get_benchmark",
    "get_domain",
    "get_universal_question",
    "hall_of_fame_benchmark_ids",
    "instantiate_question",
    "list_benchmarks",
    "list_domains",
    "list_universal_questions",
    "weekly_review_sample",
]
