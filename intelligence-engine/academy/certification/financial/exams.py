"""Financial Analyst certification exams — target 50."""

from __future__ import annotations

from academy.certification.levels.factory import build_topic_exams
from academy.certification.schema import ExamSpec

TOPICS = [
    "Cash Flow Quality",
    "Revenue Quality",
    "Working Capital",
    "Capital Allocation",
    "ROIC",
    "Debt Capacity",
    "Liquidity",
    "Leverage",
    "Margin Expansion",
    "Financial Durability",
    "Earnings Quality",
    "Free Cash Flow",
    "Incremental ROIC",
    "Interest Coverage",
    "Accruals",
    "Cash Conversion",
    "Balance Sheet Resilience",
    "Operating Leverage",
    "Capex Intensity",
    "Returns on Capital",
]


def exams() -> list[ExamSpec]:
    return build_topic_exams(
        analyst="financial",
        level=6,
        topics=TOPICS,
        target=50,
        question_tmpl="As Financial Analyst for {company}, assess {topic}. Evidence, reasoning, conclusion.",
        must_tokens={
            "ROIC": ["roic", "cash", "conclusion"],
            "Cash Flow Quality": ["cash", "earnings", "conclusion"],
            "Working Capital": ["working capital", "cash", "conclusion"],
        },
        prefix="acs_fa",
    )
