"""Exam schema — items, answers, and the weighted rubric."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

EXAM_VERSION = "institutional-accounting-exam-v1.0.0"
PROGRAMME = "AGI Financial Foundations Exam (Level 1) — Phase 1/2 Release Gate"
MODULE_CODE = "IAE"

PASSING_SCORE = 0.90

RUBRIC_WEIGHTS: dict[str, float] = {
    "accounting_correctness": 0.20,
    "statement_linkage": 0.20,
    "interpretation": 0.25,
    "causal_reasoning": 0.20,
    "honesty_about_uncertainty": 0.10,
    "hallucination_penalty": -0.15,
}

RELEASE_GATE: dict[str, Any] = {
    "min_overall_score": 0.90,
    "min_journal_accuracy": 1.0,
    "min_statement_linkage_accuracy": 1.0,
    "max_hallucination_rate": 0.0,
    "every_interpretation_must_have_evidence": True,
    "must_correctly_admit_uncertainty": True,
}


@dataclass
class ExamAnswer:
    """The AGI's answer to one exam item, plus everything needed to grade it."""

    answer_text: str
    evidence: dict[str, Any] = field(default_factory=dict)

    # Section A / G — hard, verifiable accounting checks (booleans, not opinions).
    accounting_checks: dict[str, bool] = field(default_factory=dict)
    # Section B/D/G/H — does the answer correctly link IS -> BS -> CF?
    linkage_checks: dict[str, bool] = field(default_factory=dict)

    # Open-ended interpretation grading (keyword/keypoint coverage, same
    # style as the founder-evaluation and golden_founder_5 graders).
    interpretation_keypoints_expected: list[str] = field(default_factory=list)
    interpretation_keypoints_matched: list[str] = field(default_factory=list)

    causal_reasoning_present: bool = True
    admits_uncertainty_correctly: Optional[bool] = None  # None = not applicable to this item
    hallucination_detected: bool = False
    hallucination_reason: Optional[str] = None


@dataclass
class ExamItem:
    id: str
    section: str
    number: int
    prompt: str
    max_points: float
    run: Callable[[], ExamAnswer]
    category: str = "general"
