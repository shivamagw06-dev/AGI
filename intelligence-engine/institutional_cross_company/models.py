"""CCI-01 core objects — InstitutionalRelationship (immutable, versioned)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class EvidenceRef:
    evidence_id: str
    label: str
    source: str = ""
    snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "label": self.label,
            "source": self.source,
            "snippet": self.snippet,
        }


@dataclass(frozen=True)
class InstitutionalRelationship:
    """First-class cross-company relationship — reasoning object, not a graph store."""

    relationship_id: str
    source_entity: str
    target_entity: str
    relationship_type: str
    strength: float
    confidence: float
    evidence: tuple[EvidenceRef, ...] = ()
    propagation_path: tuple[str, ...] = ()
    diagnostics: Optional[dict[str, Any]] = None
    category: str = ""
    provider: str = ""
    version: str = "cci-01-v1.0.0"
    kg_backed: bool = False
    bidirectional: bool = True
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "source_entity": self.source_entity,
            "target_entity": self.target_entity,
            "relationship_type": self.relationship_type,
            "strength": float(self.strength),
            "confidence": float(self.confidence),
            "evidence": [e.to_dict() for e in self.evidence],
            "propagation_path": list(self.propagation_path),
            "diagnostics": dict(self.diagnostics or {}),
            "category": self.category,
            "provider": self.provider,
            "version": self.version,
            "kg_backed": self.kg_backed,
            "bidirectional": self.bidirectional,
            "generated_at": self.generated_at,
            "immutable": True,
            "owns_graph": False,
            "generates_recommendations": False,
        }


@dataclass(frozen=True)
class PropagationResult:
    driver: str
    steps: tuple[str, ...]
    affected_entities: tuple[str, ...]
    portfolio_holdings: tuple[str, ...]
    path_summaries: tuple[dict[str, Any], ...] = ()
    predictive: bool = False
    diagnostics: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "driver": self.driver,
            "steps": list(self.steps),
            "affected_entities": list(self.affected_entities),
            "portfolio_holdings": list(self.portfolio_holdings),
            "path_summaries": list(self.path_summaries),
            "predictive": False,
            "dependency_propagation_only": True,
            "diagnostics": dict(self.diagnostics or {}),
        }


@dataclass(frozen=True)
class SimilarityHit:
    ticker: str
    score: float
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "score": float(self.score),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class Cluster:
    cluster_id: str
    label: str
    members: tuple[str, ...]
    kind: str = "sector"  # sector | thematic (future)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "label": self.label,
            "members": list(self.members),
            "kind": self.kind,
            "member_count": len(self.members),
        }


@dataclass
class RelationshipQueryResult:
    query: str
    intent: str
    relationships: list[InstitutionalRelationship] = field(default_factory=list)
    propagation: Optional[PropagationResult] = None
    similarities: list[SimilarityHit] = field(default_factory=list)
    clusters: list[Cluster] = field(default_factory=list)
    kg_refs: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "intent": self.intent,
            "relationships": [r.to_dict() for r in self.relationships],
            "propagation": self.propagation.to_dict() if self.propagation else None,
            "similarities": [s.to_dict() for s in self.similarities],
            "clusters": [c.to_dict() for c in self.clusters],
            "kg_refs": list(self.kg_refs),
            "diagnostics": dict(self.diagnostics or {}),
            "owns_graph": False,
            "graph_system_of_record": "KG-01",
            "generates_recommendations": False,
        }
