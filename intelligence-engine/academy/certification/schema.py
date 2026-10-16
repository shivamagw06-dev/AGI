"""Academy Certification Suite (ACS) V1 — schemas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

ACS_VERSION = "academy-certification-suite-v1.0.0"

# Merge gate: overall institutional IQ must clear this band floor.
CERTIFICATION_PASS_SCORE = 80.0  # Competent (B) minimum
INSTITUTIONAL_READY_SCORE = 90.0

LEVELS: dict[int, str] = {
    1: "concept_recall",
    2: "framework_application",
    3: "cross_book_synthesis",
    4: "case_transfer",
    5: "counter_examples",
    6: "analyst_certification",
    7: "long_term_memory",
    8: "decision_chain",
    9: "case_history",
    10: "pattern_recognition",
    11: "portfolio_thinking",
    12: "prediction_accuracy",
    13: "research_writer",
    14: "cio",
    15: "stress_tests",
    16: "benchmark_suite",
    17: "knowledge_coverage",
    18: "overall_institutional_iq",
}

ANALYSTS = [
    "business",
    "financial",
    "valuation",
    "sector",
    "macro",
    "risk",
    "management",
    "ownership",
    "committee",
    "cio",
    "portfolio",
    "research_writer",
]


@dataclass
class ExamSpec:
    exam_id: str
    level: int
    analyst: str
    question: str
    company: str | None = None
    ticker: str | None = None
    topic: str = ""
    framework: str | None = None
    must_include: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExamScore:
    exam_id: str
    level: int
    analyst: str
    score: float
    passed: bool
    band: str
    answer: str = ""
    criteria_passed: int = 0
    criteria_total: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnalystCertificate:
    analyst: str
    score: float
    band: str
    exams_passed: int
    exams_total: int
    weak_areas: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
