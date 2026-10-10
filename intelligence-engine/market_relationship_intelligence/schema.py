"""MKRI contracts — Market Relationship Intelligence (Sprint 12.3).

Programme short is MKRI to avoid collision with Macroeconomic Relationship Intelligence (MRI).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4, uuid5, NAMESPACE_URL

from pydantic import BaseModel, Field

MKRI_VERSION = "0.1.0"
PROGRAMME = "Market Relationship Intelligence"
PROGRAMME_SHORT = "MKRI"
PRIMARY_PRINCIPLE = (
    "Market relationships must always be evidence-backed, versioned and explainable. "
    "MKRI never relies on hard-coded rules without supporting historical evidence."
)

RelationshipKind = Literal[
    "macro_to_market",
    "market_to_sector",
    "sector_to_market",
    "market_to_company",
    "cross_asset",
    "flows",
    "volatility",
]

Direction = Literal["Positive", "Negative", "Mixed", "Neutral"]
EvidenceStrength = Literal["High", "Medium", "Low"]
ConfidenceLabel = Literal["High", "Medium", "Low"]

NO_MKRI_ACTIONS = (
    "infer_without_evidence",
    "call_external_providers",
    "fetch_during_ask",
    "hardcode_rules_without_history",
    "recommend_buy_sell",
    "rebuild_graph_on_ask",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "mkri") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def stable_relationship_id(source: str, target: str, relationship: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"mkri:{source}:{target}:{relationship}"))


class RelationshipEvidence(BaseModel):
    kind: str  # historical_market | historical_macro | historical_sector | historical_company | research | timeline
    summary: str
    period: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    weight: float = 1.0


class MarketRelationship(BaseModel):
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
    contradictory_evidence: list[str] = Field(default_factory=list)
    version: int = 1
    parent_relationship_id: str | None = None
    stale: bool = False
    published: bool = False
    published_at: datetime | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    programme_version: str = MKRI_VERSION

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
    node_type: str  # macro | market | sector | company | asset | flow | volatility | global | theme
    meta: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    relationship_id: str
    source: str
    target: str
    relationship: str
    direction: Direction
    confidence_pct: int
    chain: list[str] = Field(default_factory=list)
