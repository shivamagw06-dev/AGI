"""Evidence Intelligence Layer (EIL) V1 — schemas.

Every institutional claim must carry source attribution, evidence class,
and explainable confidence. Memory/priors are never labelled as facts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

EIL_VERSION = "evidence-intelligence-layer-v1.0.0"

EVIDENCE_CLASSES = (
    "fact",           # sourced filing / dataset / exchange print
    "prior",          # institutional memory / working hypothesis — NOT evidence
    "inference",      # conditional on facts
    "judgement",      # provisional conclusion
    "street",         # consensus / broker — must name the consensus source
    "market",         # price/index action — must name the feed/window
)


@dataclass
class SourceRef:
    source_id: str
    publisher: str
    title: str
    url: str = ""
    as_of: str = ""
    source_type: str = "filing"  # filing|press|exchange|wire|broker|internal|prior
    reliability: float = 0.85

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MetricPoint:
    metric: str
    value: float | str
    unit: str = ""
    period: str = ""
    entity: str = ""
    source_id: str = ""
    peer_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Claim:
    claim_id: str
    statement: str
    evidence_class: str  # fact|prior|inference|judgement|street|market
    analyst: str = "general"
    company: str | None = None
    ticker: str | None = None
    metric_ids: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    supports: list[str] = field(default_factory=list)
    contradicts: list[str] = field(default_factory=list)
    peers_required: list[str] = field(default_factory=list)
    history_required: list[str] = field(default_factory=list)
    confidence: float | None = None
    confidence_breakdown: dict[str, float] = field(default_factory=dict)
    decision_trigger: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionTrigger:
    trigger_id: str
    claim_id: str
    evidence_required: str
    expected_timeline: str
    decision_trigger: str
    action_if_met: str
    action_if_missed: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
