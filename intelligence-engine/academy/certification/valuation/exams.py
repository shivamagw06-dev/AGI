"""Valuation Analyst certification exams — target 50."""

from __future__ import annotations

from academy.certification.levels.factory import build_topic_exams
from academy.certification.schema import ExamSpec

TOPICS = [
    "Reverse DCF",
    "Margin of Safety",
    "Intrinsic Value",
    "Relative Valuation",
    "Historical Valuation",
    "Scenario Analysis",
    "Market Expectations",
    "Valuation DNA",
    "WACC",
    "Cost of Equity",
    "Terminal Value Risk",
    "Premium Valuation Debate",
    "Value Trap Detection",
    "Implied Growth",
    "Multiple Context",
    "Downside Case",
    "Asymmetry",
    "Expectation Revision",
    "Cash Flow Duration",
    "Risk-Adjusted Value",
]


def exams() -> list[ExamSpec]:
    return build_topic_exams(
        analyst="valuation",
        level=6,
        topics=TOPICS,
        target=50,
        question_tmpl="As Valuation Analyst for {company}, evaluate {topic}. Debate expectations; no cheap/expensive slogans alone.",
        must_tokens={
            "Reverse DCF": ["reverse", "implied", "expectation"],
            "Margin of Safety": ["margin of safety", "intrinsic", "uncertainty"],
            "Intrinsic Value": ["intrinsic", "cash", "assumption"],
        },
        prefix="acs_va",
    )
