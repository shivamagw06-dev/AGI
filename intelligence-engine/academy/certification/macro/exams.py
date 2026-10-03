"""Macro Analyst certification exams — target 40."""

from __future__ import annotations

from academy.certification.levels.factory import build_topic_exams
from academy.certification.schema import ExamSpec

TOPICS = [
    "Inflation Transmission",
    "Interest Rates",
    "Currency",
    "Oil Shock",
    "GDP Growth",
    "Policy Transmission",
    "Bond Yields",
    "Liquidity Conditions",
    "Credit Impulse",
    "Real Rates",
]


def exams() -> list[ExamSpec]:
    return build_topic_exams(
        analyst="macro",
        level=6,
        topics=TOPICS,
        target=40,
        question_tmpl="As Macro Analyst, how does {topic} affect {company}? Transmission, evidence, conclusion.",
        must_tokens={
            "Interest Rates": ["rate", "transmission", "conclusion"],
            "Inflation Transmission": ["inflation", "margin", "conclusion"],
        },
        prefix="acs_mac",
    )
