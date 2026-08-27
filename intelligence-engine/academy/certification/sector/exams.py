"""Sector Analyst certification exams — target 40."""

from __future__ import annotations

from academy.certification.levels.factory import build_topic_exams
from academy.certification.schema import ExamSpec

TOPICS = [
    "Industry Structure",
    "Competition Intensity",
    "Supply Chain",
    "Regulation",
    "Technology Disruption",
    "Capacity Cycle",
    "Demand Drivers",
    "Pricing Regime",
    "Entry Barriers",
    "Profit Pool",
]


def exams() -> list[ExamSpec]:
    return build_topic_exams(
        analyst="sector",
        level=6,
        topics=TOPICS,
        target=40,
        question_tmpl="As Sector Analyst covering {company}, analyse sector lens: {topic}.",
        prefix="acs_sec",
    )
