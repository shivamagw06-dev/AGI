"""KG-01 entity / node model — every node carries provenance fields."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from institutional_graph.schema import ENTITY_TYPES


@dataclass(frozen=True)
class Provenance:
    origin: str
    timestamp: str
    source_document: str = ""
    evidence_ids: tuple[str, ...] = ()
    engine: str = ""
    version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "origin": self.origin,
            "timestamp": self.timestamp,
            "source_document": self.source_document,
            "evidence_ids": list(self.evidence_ids),
            "engine": self.engine,
            "version": self.version,
        }


@dataclass(frozen=True)
class Entity:
    """Canonical graph node."""

    id: str
    type: str
    label: str
    version: str
    timestamp: str
    source: str
    confidence: float
    ticker: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    provenance: Optional[Provenance] = None
    impact_score: int = 0

    def __post_init__(self) -> None:
        if self.type not in ENTITY_TYPES:
            raise ValueError(f"unknown entity type: {self.type}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "version": self.version,
            "timestamp": self.timestamp,
            "source": self.source,
            "confidence": float(self.confidence),
            "ticker": self.ticker,
            "attributes": dict(self.attributes or {}),
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "impact_score": int(self.impact_score),
        }


def make_node(
    *,
    node_id: str,
    node_type: str,
    label: str,
    version: str,
    timestamp: str,
    source: str,
    confidence: float,
    ticker: str = "",
    attributes: Optional[dict[str, Any]] = None,
    provenance: Optional[Provenance] = None,
    impact_score: int = 0,
) -> Entity:
    return Entity(
        id=node_id,
        type=node_type,
        label=label,
        version=version,
        timestamp=timestamp,
        source=source,
        confidence=float(confidence),
        ticker=ticker,
        attributes=dict(attributes or {}),
        provenance=provenance,
        impact_score=int(impact_score),
    )


# Typed aliases for clarity in builders / APIs
EvidenceNode = Entity
MetricNode = Entity
ReasonNode = Entity
DecisionNode = Entity
