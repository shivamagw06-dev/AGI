"""Institutional Regression Suite (IRS) V1 — schemas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

IRS_VERSION = "institutional-regression-suite-v1.0.0"
GOLDEN_SET_VERSION = "v1"

# Merge blocked if overall IQ falls by more than this (absolute points)
REGRESSION_EPSILON = 0.05


@dataclass
class GoldenQuestion:
    question_id: str
    domain: str  # business|financial|valuation|risk|management|macro|sector|portfolio
    analyst: str
    question: str
    company: str | None = None
    ticker: str | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GoldenAnswerRef:
    question_id: str
    institutional_reference: str
    evidence_checklist: list[str] = field(default_factory=list)
    framework_checklist: list[str] = field(default_factory=list)
    concept_checklist: list[str] = field(default_factory=list)
    reasoning_checklist: list[str] = field(default_factory=list)
    must_not: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HallucinationFinding:
    finding_id: str
    severity: str  # critical|high|medium|low
    category: str
    detail: str
    question_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DriftFinding:
    finding_id: str
    analyst: str
    violation: str
    detail: str
    question_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
