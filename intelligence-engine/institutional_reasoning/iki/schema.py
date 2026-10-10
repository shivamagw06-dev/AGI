"""IKI schema constants and Phase 3 exit targets."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

IKI_VERSION = "institutional-knowledge-intelligence-v1.0.0"
MODULE_CODE = "IKI"
PROGRAMME = "Institutional Knowledge Intelligence"

# Soft IKG relation types (in-process; no Neo4j).
IKI_EDGE_TYPES = (
    "REQUIRES",
    "SUPPORTED_BY",
    "CONFLICTS_WITH",
    "APPLIES_TO",
    "INVALIDATED_BY",
    "COMPETES_WITH",
    "ALTERNATIVE_TO",
)

PHASE3_TARGETS: dict[str, float] = {
    "overall_judgement": 90.0,
    "applicability_accuracy": 95.0,
    "conflict_explanation": 100.0,
    "unsupported_conclusions": 0.0,
}


@dataclass
class FrameworkSpec:
    framework_id: str
    name: str
    author: str
    version: str = "1.0.0"
    question_types: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
    applicable_entity_types: tuple[str, ...] = ("Company",)
    not_applicable_entity_types: tuple[str, ...] = ()
    not_applicable_sectors: tuple[str, ...] = ()
    applicable_sectors: tuple[str, ...] = ()
    priority: int = 50
    confidence_weight: float = 0.7
    failure_conditions: tuple[str, ...] = ()
    competing_frameworks: tuple[str, ...] = ()
    alternative_frameworks: tuple[str, ...] = ()
    school: str = ""  # damodaran | graham | buffett | institutional
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ApplicabilityScore:
    framework_id: str
    score: float
    applicable: bool
    reasons: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    confidence_band: str = "Medium"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
