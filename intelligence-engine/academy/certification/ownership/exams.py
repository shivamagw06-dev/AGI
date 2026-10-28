"""Ownership Analyst certification exams — target 30."""

from __future__ import annotations

from academy.certification.levels.factory import build_topic_exams
from academy.certification.schema import ExamSpec

TOPICS = [
    "Institutional Holdings",
    "Promoter Ownership",
    "Mutual Fund Behaviour",
    "Foreign Investors",
    "Insider Activity",
    "Ownership Trends",
    "Pledge Risk",
    "Block Deals",
    "Free Float",
    "Stewardship Signals",
]


def exams() -> list[ExamSpec]:
    return build_topic_exams(
        analyst="ownership",
        level=6,
        topics=TOPICS,
        target=30,
        question_tmpl="As Ownership Analyst for {company}, analyse {topic}.",
        prefix="acs_own",
    )
