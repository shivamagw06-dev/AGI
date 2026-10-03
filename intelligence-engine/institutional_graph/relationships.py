"""KG-01 relationships — directed, versioned, evidence-backed."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from institutional_graph.entities import Provenance
from institutional_graph.schema import RELATIONSHIP_KINDS


@dataclass(frozen=True)
class Relationship:
    """Directed edge between two entities."""

    id: str
    source_id: str
    target_id: str
    kind: str  # positive | negative | supports | pressures | derived | ...
    direction: str  # alias of kind for API clarity
    strength: float  # 0–1
    confidence: float  # 0–1
    evidence_ids: tuple[str, ...] = ()
    version: str = ""
    timestamp: str = ""
    label: str = ""
    inferred: bool = False
    attributes: dict[str, Any] = field(default_factory=dict)
    provenance: Optional[Provenance] = None

    def __post_init__(self) -> None:
        kind = (self.kind or self.direction or "").strip().lower()
        if kind and kind not in RELATIONSHIP_KINDS:
            raise ValueError(f"unknown relationship kind: {kind}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "kind": self.kind,
            "direction": self.direction or self.kind,
            "strength": float(self.strength),
            "confidence": float(self.confidence),
            "evidence_ids": list(self.evidence_ids),
            "version": self.version,
            "timestamp": self.timestamp,
            "label": self.label,
            "inferred": bool(self.inferred),
            "attributes": dict(self.attributes or {}),
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }


def make_relationship(
    *,
    rel_id: str,
    source_id: str,
    target_id: str,
    kind: str,
    strength: float,
    confidence: float,
    evidence_ids: Optional[tuple[str, ...]] = None,
    version: str = "",
    timestamp: str = "",
    label: str = "",
    inferred: bool = False,
    attributes: Optional[dict[str, Any]] = None,
    provenance: Optional[Provenance] = None,
) -> Relationship:
    return Relationship(
        id=rel_id,
        source_id=source_id,
        target_id=target_id,
        kind=kind,
        direction=kind,
        strength=float(strength),
        confidence=float(confidence),
        evidence_ids=tuple(evidence_ids or ()),
        version=version,
        timestamp=timestamp,
        label=label,
        inferred=inferred,
        attributes=dict(attributes or {}),
        provenance=provenance,
    )
