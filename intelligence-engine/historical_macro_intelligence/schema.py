"""HMIP contracts — Historical Macroeconomic Intelligence Platform (Sprint 10.2)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

HMIP_VERSION = "0.1.0"
PROGRAMME = "Historical Macroeconomic Intelligence Platform"
PROGRAMME_SHORT = "HMIP"
PRIMARY_PRINCIPLE = (
    "Historical macro knowledge is immutable and forms the long-term institutional memory of AGI. "
    "Analysis consumes the Historical Macro Knowledge Store — never external providers."
)

MacroCategory = Literal[
    "Monetary",
    "Inflation",
    "Growth",
    "Fiscal",
    "External Sector",
    "Financial Markets",
]

# Separate historical storage namespaces (never overwrite)
STORAGE_NAMESPACES: tuple[str, ...] = (
    "historical_macro",
    "historical_inflation",
    "historical_rates",
    "historical_gdp",
    "historical_iip",
    "historical_fiscal",
    "historical_trade",
    "historical_liquidity",
    "historical_forex",
    "historical_budget",
)

CATEGORY_TO_NAMESPACE: dict[str, str] = {
    "Monetary": "historical_rates",
    "Inflation": "historical_inflation",
    "Growth": "historical_gdp",
    "Fiscal": "historical_fiscal",
    "External Sector": "historical_forex",
    "Financial Markets": "historical_liquidity",
}

INDICATOR_NAMESPACE_OVERRIDE: dict[str, str] = {
    "IIP": "historical_iip",
    "GDP": "historical_gdp",
    "GVA": "historical_gdp",
    "CPI": "historical_inflation",
    "WPI": "historical_inflation",
    "Core Inflation": "historical_inflation",
    "Repo Rate": "historical_rates",
    "Reverse Repo": "historical_rates",
    "CRR": "historical_rates",
    "SLR": "historical_rates",
    "Federal Funds Rate": "historical_rates",
    "Fiscal Deficit": "historical_fiscal",
    "Union Budget": "historical_budget",
    "Government Borrowing": "historical_fiscal",
    "Forex Reserves": "historical_forex",
    "Exports": "historical_trade",
    "Imports": "historical_trade",
    "Banking Liquidity": "historical_liquidity",
    "Credit Growth": "historical_liquidity",
}

SOURCES: tuple[str, ...] = (
    "rbi",
    "mospi",
    "nso",
    "mof",
    "cga",
    "sebi",
    "fred",
    "imf",
    "world_bank",
    "oecd",
)

NO_HMIP_ACTIONS = (
    "overwrite_historical_records",
    "call_external_providers_during_analysis",
    "fetch_during_ask",
    "mutate_published_hmko",
    "recommend_buy_sell",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "hmip") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def checksum_for(*parts: Any) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def namespace_for(category: str, indicator: str) -> str:
    if indicator in INDICATOR_NAMESPACE_OVERRIDE:
        return INDICATOR_NAMESPACE_OVERRIDE[indicator]
    return CATEGORY_TO_NAMESPACE.get(category, "historical_macro")


class RawHistoricalObservation(BaseModel):
    observation_id: str = Field(default_factory=lambda: new_id("hraw"))
    source: str
    country: str
    category: str
    indicator: str
    value: float | None = None
    period: str  # e.g. 2020, 2020-Q2, FY2021
    previous: float | None = None
    unit: str = ""
    publication_date: str
    effective_date: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime = Field(default_factory=utc_now)


class HistoricalMacroKnowledgeObject(BaseModel):
    """Immutable historical observation — never overwritten; revisions append."""

    hmko_id: str = Field(default_factory=lambda: new_id("hmko"))
    country: str
    category: str
    indicator: str
    value: float | None = None
    period: str
    previous: float | None = None
    unit: str = ""
    source: str
    publication_date: str
    effective_date: str | None = None
    version: int = 1
    parent_hmko_id: str | None = None
    confidence: float = 0.9
    provenance: dict[str, Any] = Field(default_factory=dict)
    checksum: str = ""
    namespace: str = "historical_macro"
    revision_note: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    programme_version: str = HMIP_VERSION
    immutable: bool = True

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        data["overwritable"] = False
        data["providers_queried"] = []
        return data


class TimelineNode(BaseModel):
    year: int
    period: str
    label: str
    value: float | None = None
    importance: str = "Medium"  # Critical | High | Medium | Low
    event: str | None = None
    hmko_id: str | None = None


class IndicatorTimeline(BaseModel):
    timeline_id: str = Field(default_factory=lambda: new_id("htl"))
    country: str
    indicator: str
    category: str
    nodes: list[TimelineNode] = Field(default_factory=list)
    years_span: list[int] = Field(default_factory=list)
    completeness_pct: float = 0.0
    missing_periods: list[str] = Field(default_factory=list)
    built_at: datetime = Field(default_factory=utc_now)
    version: str = HMIP_VERSION

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme_short"] = PROGRAMME_SHORT
        data["providers_queried"] = []
        return data
