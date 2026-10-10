"""MRI contracts — Macroeconomic Relationship Intelligence (Sprint 10.3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4, uuid5, NAMESPACE_URL

from pydantic import BaseModel, Field

MRI_VERSION = "0.1.0"
PROGRAMME = "Macroeconomic Relationship Intelligence"
PROGRAMME_SHORT = "MRI"
PRIMARY_PRINCIPLE = (
    "Relationships must always be evidence-backed, versioned and traceable. "
    "MRI never relies on hard-coded rules without supporting historical evidence."
)

RelationshipKind = Literal[
    "macro_to_company",
    "macro_to_sector",
    "macro_to_market",
    "macro_to_macro",
    "global_to_india",
]

Direction = Literal["Positive", "Negative", "Mixed", "Neutral"]
EvidenceStrength = Literal["High", "Medium", "Low"]
ConfidenceLabel = Literal["High", "Medium", "Low"]

NO_MRI_ACTIONS = (
    "infer_without_evidence",
    "call_external_providers",
    "fetch_during_ask",
    "hardcode_rules_without_history",
    "recommend_buy_sell",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "mri") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def stable_relationship_id(source: str, target: str, relationship: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"mri:{source}:{target}:{relationship}"))


class RelationshipEvidence(BaseModel):
    kind: str  # historical_macro | historical_company | historical_sector | historical_market | timeline
    summary: str
    period: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    weight: float = 1.0


class MacroRelationship(BaseModel):
    relationship_id: str = Field(default_factory=lambda: new_id("mrel"))
    source: str
    source_label: str | None = None
    target: str
    target_label: str | None = None
    relationship: str
    kind: RelationshipKind
    direction: Direction = "Positive"
    evidence_strength: EvidenceStrength = "Medium"
    confidence_pct: int = 70
    confidence_label: ConfidenceLabel = "Medium"
    historical_observations: int = 1
    average_lag: str | None = None
    first_observed: str | None = None
    last_confirmed: str | None = None
    chain: list[str] = Field(default_factory=list)
    evidence: list[RelationshipEvidence] = Field(default_factory=list)
    supporting_layers: list[str] = Field(default_factory=list)
    version: int = 1
    parent_relationship_id: str | None = None
    stale: bool = False
    published: bool = False
    published_at: datetime | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    programme_version: str = MRI_VERSION

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        data["providers_queried"] = []
        data["inferred_without_evidence"] = False
        return data


class GraphNode(BaseModel):
    node_id: str
    label: str
    node_type: str  # macro | sector | industry | company | market | theme | global
    meta: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    relationship_id: str
    source: str
    target: str
    relationship: str
    direction: Direction
    confidence_pct: int
    chain: list[str] = Field(default_factory=list)
