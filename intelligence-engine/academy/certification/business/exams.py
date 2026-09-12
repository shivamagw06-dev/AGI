"""Business Analyst certification exams — target 50."""

from __future__ import annotations

from academy.certification.levels.factory import build_topic_exams
from academy.certification.schema import ExamSpec

TOPICS = [
    "Economic Moat",
    "Pricing Power",
    "Porter Five Forces",
    "Value Chain",
    "Amazon Flywheel",
    "Capital Cycle",
    "Network Effects",
    "Switching Costs",
    "Business DNA",
    "Capital Allocation",
    "Growth Runway",
    "Competitive Advantage",
    "Management Quality",
    "Customer Retention",
    "Distribution Strength",
    "Brand Durability",
    "Platform Economics",
    "Creative Destruction",
    "Industry Structure",
    "Unit Economics",
]


def exams() -> list[ExamSpec]:
    return build_topic_exams(
        analyst="business",
        level=6,
        topics=TOPICS,
        target=50,
        question_tmpl="As Business Analyst for {company}, analyse {topic}. Use evidence, reasoning and a conclusion.",
        must_tokens={
            "Porter Five Forces": ["porter", "rivalry", "conclusion"],
            "Amazon Flywheel": ["flywheel", "customer", "conclusion"],
            "Economic Moat": ["moat", "durable", "conclusion"],
            "Pricing Power": ["pricing", "margin", "conclusion"],
        },
        prefix="acs_ba",
    )
