"""Academy Validation Suite schemas — demonstrate knowledge, not ingest status."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

AVS_VERSION = "academy-validation-suite-v1.0.0"

LEVELS = {
    1: "concept_recall",
    2: "framework_application",
    3: "cross_book_synthesis",
    4: "case_transfer",
    5: "counter_example_reasoning",
    6: "analyst_specific",
    7: "memory_test",
    8: "decision_test",
}


@dataclass
class ExamItem:
    exam_id: str
    level: int
    question: str
    analyst: str = "general"  # business|financial|valuation|risk|general|committee
    company: str | None = None
    ticker: str | None = None
    framework: str | None = None
    authors: list[str] = field(default_factory=list)
    analogues: list[str] = field(default_factory=list)
    must_include: list[str] = field(default_factory=list)
    must_not_include: list[str] = field(default_factory=list)
    pass_criteria: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CriterionResult:
    name: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExamResult:
    exam_id: str
    level: int
    level_name: str
    question: str
    passed: bool
    score: float
    answer: str
    structure: dict[str, Any] = field(default_factory=dict)
    criteria: list[CriterionResult] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    version: str = AVS_VERSION

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d
