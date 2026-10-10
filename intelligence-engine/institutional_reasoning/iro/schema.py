"""IRO schema — research goals, tasks, and Phase 4 exit targets."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

IRO_VERSION = "institutional-research-orchestration-v1.0.0"
MODULE_CODE = "IRO"
PROGRAMME = "Institutional Research Orchestration"

GOAL_TYPES = ("investment", "credit", "ma", "ipo", "monitoring")

TASK_STATUSES = (
    "pending",
    "executed",
    "adapted",
    "insufficient",
    "not_applicable",
    "skipped",
)

PHASE4_TARGETS: dict[str, float] = {
    "planning_suite": 95.0,
    "dependency_resolution": 100.0,
    "djg_coverage": 100.0,
    "package_completeness": 100.0,
}


@dataclass
class ResearchTask:
    task_id: str
    label: str
    question_template: str
    depends_on: tuple[str, ...] = ()
    committee: str = "investment"
    required_evidence: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    optional: bool = False
    deliverable: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchGoal:
    goal_id: str
    goal_type: str
    objective: str
    entity_id: str | None = None
    entity_name: str | None = None
    amount: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskResult:
    task_id: str
    label: str
    question: str
    status: str
    committee: str
    confidence: float | None = None
    summary: str = ""
    evidence_pack: dict[str, Any] = field(default_factory=dict)
    justification_graph: dict[str, Any] = field(default_factory=dict)
    missing_evidence: list[str] = field(default_factory=list)
    adaptations: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0
    deliverable: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
