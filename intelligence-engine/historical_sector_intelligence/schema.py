"""HSIP contracts — Historical Sector Intelligence Platform (Sprint 11.2)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

HSIP_VERSION = "0.1.0"
PROGRAMME = "Historical Sector Intelligence Platform"
PROGRAMME_SHORT = "HSIP"
PRIMARY_PRINCIPLE = (
    "Historical sector knowledge is immutable institutional memory. "
    "Analysis consumes the Historical Sector Knowledge Store — never external providers."
)

SectorCategory = Literal[
    "Growth",
    "Valuation",
    "Profitability",
    "Competition",
    "Government",
    "Capital Allocation",
    "Events",
]

STORAGE_NAMESPACES: tuple[str, ...] = (
    "historical_sector",
    "historical_sector_growth",
    "historical_sector_valuation",
    "historical_sector_profitability",
    "historical_sector_policy",
    "historical_sector_events",
    "historical_sector_leadership",
)

CATEGORY_TO_NAMESPACE: dict[str, str] = {
    "Growth": "historical_sector_growth",
    "Valuation": "historical_sector_valuation",
    "Profitability": "historical_sector_profitability",
    "Competition": "historical_sector_leadership",
    "Government": "historical_sector_policy",
    "Capital Allocation": "historical_sector_events",
    "Events": "historical_sector_events",
}

INDICATOR_NAMESPACE_OVERRIDE: dict[str, str] = {
    "Revenue Growth": "historical_sector_growth",
    "Earnings Growth": "historical_sector_growth",
    "Average PE": "historical_sector_valuation",
    "Average EV/EBITDA": "historical_sector_valuation",
    "Average PB": "historical_sector_valuation",
    "Average ROE": "historical_sector_profitability",
    "EBITDA Margin": "historical_sector_profitability",
    "Sector Leader": "historical_sector_leadership",
    "Market Share Shift": "historical_sector_leadership",
    "Government Policy": "historical_sector_policy",
    "Regulatory Reform": "historical_sector_policy",
    "Key Event": "historical_sector_events",
    "Capex Cycle": "historical_sector_events",
}

NO_HSIP_ACTIONS = (
    "overwrite_historical_records",
    "call_external_providers_during_analysis",
    "fetch_during_ask",
    "mutate_published_hsko",
    "recommend_buy_sell",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "hsip") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def checksum_for(*parts: Any) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def namespace_for(category: str, indicator: str) -> str:
    if indicator in INDICATOR_NAMESPACE_OVERRIDE:
        return INDICATOR_NAMESPACE_OVERRIDE[indicator]
    return CATEGORY_TO_NAMESPACE.get(category, "historical_sector")


class RawHistoricalSectorObservation(BaseModel):
    observation_id: str = Field(default_factory=lambda: new_id("hsraw"))
    source: str
    sector_key: str
    sector_label: str
    category: str
    indicator: str
    value: float | None = None
    period: str  # FY2018 / 2020 / 2008
    previous: float | None = None
    unit: str = ""
    sector_leader: str | None = None
    government_policies: list[str] = Field(default_factory=list)
    macro_regime: str | None = None
    key_events: list[str] = Field(default_factory=list)
    publication_date: str
    effective_date: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime = Field(default_factory=utc_now)


class HistoricalSectorKnowledgeObject(BaseModel):
    """Immutable historical sector observation — never overwritten; revisions append."""

    hsko_id: str = Field(default_factory=lambda: new_id("hsko"))
    sector_key: str
    sector_label: str
    category: str
    indicator: str
    value: float | None = None
    period: str
    previous: float | None = None
    unit: str = ""
    source: str
    sector_leader: str | None = None
    government_policies: list[str] = Field(default_factory=list)
    macro_regime: str | None = None
    key_events: list[str] = Field(default_factory=list)
    publication_date: str
    effective_date: str | None = None
    version: int = 1
    parent_hsko_id: str | None = None
    historical_confidence: float = 0.9
    provenance: dict[str, Any] = Field(default_factory=dict)
    checksum: str = ""
    namespace: str = "historical_sector"
    revision_note: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    programme_version: str = HSIP_VERSION
    immutable: bool = True

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        data["overwritable"] = False
        data["providers_queried"] = []
        # Spec-friendly aliases
        data["revenue_growth"] = data["value"] if data["indicator"] == "Revenue Growth" else None
        data["sector_margin"] = data["value"] if data["indicator"] == "EBITDA Margin" else None
        data["average_pe"] = data["value"] if data["indicator"] == "Average PE" else None
        data["average_roe"] = data["value"] if data["indicator"] == "Average ROE" else None
        return data


class TimelineNode(BaseModel):
    year: int
    period: str
    label: str
    value: float | None = None
    importance: str = "Medium"
    event: str | None = None
    hsko_id: str | None = None
    sector_leader: str | None = None
    macro_regime: str | None = None


class SectorTimeline(BaseModel):
    timeline_id: str = Field(default_factory=lambda: new_id("stl"))
    sector_key: str
    sector_label: str
    indicator: str
    category: str
    nodes: list[TimelineNode] = Field(default_factory=list)
    years_span: list[int] = Field(default_factory=list)
    completeness_pct: float = 0.0
    missing_periods: list[str] = Field(default_factory=list)
    built_at: datetime = Field(default_factory=utc_now)
    version: str = HSIP_VERSION

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme_short"] = PROGRAMME_SHORT
        data["providers_queried"] = []
        return data
