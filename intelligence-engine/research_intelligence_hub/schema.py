"""RIH contracts — Research Intelligence Hub (AGIB v4.0).

Every research note is an Intelligence Object / Hub node in the
research-centric knowledge graph — not a static document.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

RIH_VERSION = "4.0.0"
PROGRAMME = "Research Intelligence Hub"
PROGRAMME_SHORT = "RIH"
PRIMARY_PRINCIPLE = (
    "Users come to AGI to read research; they stay because every research note "
    "becomes an interactive gateway into the institutional intelligence graph."
)

SessionLabel = Literal[
    "Pre Market",
    "Morning",
    "Afternoon",
    "Post Market",
    "Global",
]

NO_RIH_ACTIONS = (
    "call_external_providers",
    "fetch_during_ask",
    "recommend_buy_sell",
    "set_target_prices",
    "invent_evidence",
    "query_live_market_feeds",
    "replace_underlying_intelligence_stores",
)

LINK_DOMAINS: tuple[str, ...] = (
    "companies",
    "sectors",
    "markets",
    "macro_topics",
    "ipo_links",
    "global_topics",
    "historical_context",
    "relationships",
    "historical_analogues",
    "forecast",
    "supporting_evidence",
    "related_research",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "rih") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class EntityLink(BaseModel):
    """Clickable link into an AGI intelligence domain."""

    id: str
    label: str
    kind: str
    role: str | None = None  # mentioned | competitor | supplier | customer | primary | secondary | ...
    href: str | None = None
    gateway: str | None = None
    confidence_pct: int | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class RelationshipLink(BaseModel):
    source: str
    target: str
    relationship: str
    direction: str = "positive"
    strength: str = "Medium"
    confidence_pct: int = 70
    evidence: list[str] = Field(default_factory=list)
    gateway: str | None = None


class AnalogueLink(BaseModel):
    matched_period: str
    label: str | None = None
    similarity_score: float = 0.0
    matching_dimensions: list[str] = Field(default_factory=list)
    historical_outcome: str | None = None
    differences: list[str] = Field(default_factory=list)
    gateway: str | None = None


class ForecastScenario(BaseModel):
    scenario: Literal["Bull", "Base", "Bear"]
    probability_pct: int
    confidence_pct: int
    narrative: list[str] = Field(default_factory=list)
    catalysts: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    invalidators: list[str] = Field(default_factory=list)


class ForecastBundle(BaseModel):
    horizon: str = "6 Months"
    scenarios: list[ForecastScenario] = Field(default_factory=list)
    probability_distribution: dict[str, int] = Field(default_factory=dict)
    confidence: dict[str, Any] = Field(default_factory=dict)
    gateways: list[str] = Field(default_factory=list)
    predicts_single_path: bool = False


class EvidenceItem(BaseModel):
    kind: str
    summary: str
    refs: list[str] = Field(default_factory=list)
    source_gateway: str | None = None
    traceable: bool = True


class ResearchObject(BaseModel):
    """Primary knowledge object — Intelligence Hub for one research note."""

    id: str = Field(default_factory=lambda: new_id("note"))
    headline: str
    publication_date: str | None = None
    session: SessionLabel | None = None
    body: str = ""
    executive_summary: list[str] = Field(default_factory=list)
    investment_thesis: str | None = None
    key_conclusions: list[str] = Field(default_factory=list)
    why_it_matters: list[str] = Field(default_factory=list)
    companies: list[EntityLink] = Field(default_factory=list)
    sectors: list[EntityLink] = Field(default_factory=list)
    markets: list[EntityLink] = Field(default_factory=list)
    macro_topics: list[EntityLink] = Field(default_factory=list)
    ipo_links: list[EntityLink] = Field(default_factory=list)
    global_topics: list[EntityLink] = Field(default_factory=list)
    historical_context: list[EntityLink] = Field(default_factory=list)
    relationships: list[RelationshipLink] = Field(default_factory=list)
    historical_analogues: list[AnalogueLink] = Field(default_factory=list)
    forecast: ForecastBundle = Field(default_factory=ForecastBundle)
    supporting_evidence: list[EvidenceItem] = Field(default_factory=list)
    related_research: list[EntityLink] = Field(default_factory=list)
    confidence: dict[str, Any] = Field(default_factory=dict)
    importance_score: int = 50
    freshness: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    published: bool = False
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    programme_version: str = RIH_VERSION
    sources: list[str] = Field(default_factory=list)
    providers_queried: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        data["principle"] = PRIMARY_PRINCIPLE
        data["is_document"] = False
        data["is_intelligence_object"] = True
        data["is_recommendation"] = False
        data["providers_queried"] = []
        data["collected_on_request"] = False
        data["navigation"] = [
            "executive_summary",
            "why_it_matters",
            "companies",
            "sectors",
            "markets",
            "macro_topics",
            "historical_context",
            "relationships",
            "historical_analogues",
            "forecast",
            "supporting_evidence",
            "related_research",
        ]
        return data


class HubGraph(BaseModel):
    """Lightweight graph view rooted at a research note."""

    note_id: str
    headline: str
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    providers_queried: list[str] = Field(default_factory=list)
