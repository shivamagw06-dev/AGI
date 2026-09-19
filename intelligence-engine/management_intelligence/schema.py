"""Management Intelligence Engine (MII) V1 — schemas.

Primary question: Can this management team be trusted to compound shareholder value?
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

MII_VERSION = "management-intelligence-engine-v1.0.0"

DNA_ARCHETYPES = (
    "Capital Allocator",
    "Growth Builder",
    "Operator",
    "Turnaround Specialist",
    "Financial Engineer",
    "Founder-led Visionary",
    "Professional Steward",
    "Empire Builder",
    "Value Creator",
    "Value Destroyer",
)

GUIDANCE_OUTCOMES = (
    "raised",
    "maintained",
    "lowered",
    "withdrawn",
    "delivered",
    "missed",
    "partially_delivered",
)

VALUE_LABELS = ("value_creating", "neutral", "value_destructive", "unknown")
THESIS_IMPACT = (
    "strengthens_thesis",
    "neutral",
    "weakens_thesis",
    "needs_monitoring",
    "committee_review_required",
)


@dataclass
class ExecutiveProfile:
    role: str
    name: str
    tenure_start: str = ""
    tenure_end: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GuidanceEvent:
    event_id: str
    ticker: str
    metric: str
    period: str
    statement: str
    status: str  # raised|maintained|lowered|withdrawn
    outcome: str  # delivered|missed|partially_delivered|pending
    as_of: str = ""
    source_doc: str = ""
    evidence_tier: int = 2

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionRecord:
    decision_id: str
    ticker: str
    decision: str
    reason: str
    expected_outcome: str
    actual_outcome: str
    value_label: str
    as_of: str
    lessons: str = ""
    source_doc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
