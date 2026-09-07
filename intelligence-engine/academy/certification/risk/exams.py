"""Risk Analyst certification exams — target 40."""

from __future__ import annotations

from academy.certification.levels.factory import build_topic_exams
from academy.certification.schema import ExamSpec

TOPICS = [
    "Tail Risk",
    "Scenario Analysis",
    "Stress Testing",
    "Black Swan",
    "Execution Risk",
    "Governance Risk",
    "Regulatory Risk",
    "Liquidity Risk",
    "Credit Risk",
    "Concentration Risk",
]


def exams() -> list[ExamSpec]:
    return build_topic_exams(
        analyst="risk",
        level=6,
        topics=TOPICS,
        target=40,
        question_tmpl="As Risk Analyst for {company}, assess {topic}. Warning signals, scenarios, conclusion.",
        must_tokens={
            "Tail Risk": ["tail", "stress", "conclusion"],
            "Governance Risk": ["governance", "risk", "conclusion"],
        },
        prefix="acs_risk",
    )
