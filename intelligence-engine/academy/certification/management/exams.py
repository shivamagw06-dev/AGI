"""Management Analyst certification exams — target 30."""

from __future__ import annotations

from academy.certification.levels.factory import build_topic_exams
from academy.certification.schema import ExamSpec

TOPICS = [
    "Capital Allocation",
    "Communication Quality",
    "Governance",
    "Compensation Alignment",
    "Execution",
    "Integrity",
    "Incentive Design",
    "M&A Discipline",
    "Buyback Judgment",
    "Culture Signals",
]


def exams() -> list[ExamSpec]:
    return build_topic_exams(
        analyst="management",
        level=6,
        topics=TOPICS,
        target=30,
        question_tmpl="As Management Analyst for {company}, evaluate {topic}.",
        prefix="acs_mgmt",
    )
