"""CSKP contracts — Continuous Sector Knowledge Platform (Sprint 11.1)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

CSKP_VERSION = "0.1.0"
PROGRAMME = "Continuous Sector Knowledge Platform"
PROGRAMME_SHORT = "CSKP"
PRIMARY_PRINCIPLE = (
    "Sector intelligence sits between Macro and Company intelligence. "
    "Sector Knowledge Objects are continuously derived from company, macro, market, "
    "event and research tips — user requests never trigger construction."
)

Outlook = Literal["Positive", "Neutral", "Negative", "Mixed"]
Trend = Literal["Improving", "Stable", "Deteriorating", "Mixed", "Unknown"]
Importance = Literal["Critical", "High", "Medium", "Low"]
MaterialityTier = Literal["Ignore", "Low", "Medium", "High", "Critical"]

# Institutional Indian sector universe (Sprint 11.1)
SECTOR_UNIVERSE: tuple[str, ...] = (
    "banking",
    "financial_services",
    "nbfc",
    "insurance",
    "it_services",
    "software_products",
    "pharma",
    "healthcare",
    "fmcg",
    "retail",
    "auto",
    "auto_ancillary",
    "capital_goods",
    "industrials",
    "cement",
    "metals",
    "mining",
    "oil_gas",
    "chemicals",
    "specialty_chemicals",
    "defence",
    "power",
    "utilities",
    "renewable_energy",
    "telecom",
    "infrastructure",
    "real_estate",
    "aviation",
    "logistics",
    "textiles",
    "consumer_durables",
)

SECTOR_ALIASES: dict[str, str] = {
    "banks": "banking",
    "bank": "banking",
    "banking": "banking",
    "private_banks": "banking",
    "financials": "financial_services",
    "financial_services": "financial_services",
    "nbfc": "nbfc",
    "insurance": "insurance",
    "it_services": "it_services",
    "information_technology": "it_services",
    "it": "it_services",
    "software_products": "software_products",
    "pharma": "pharma",
    "pharmaceuticals": "pharma",
    "healthcare": "healthcare",
    "fmcg": "fmcg",
    "retail": "retail",
    "auto": "auto",
    "automobiles": "auto",
    "auto_ancillary": "auto_ancillary",
    "capital_goods": "capital_goods",
    "industrials": "industrials",
    "cement": "cement",
    "metals": "metals",
    "mining": "mining",
    "oil_gas": "oil_gas",
    "oil_and_gas": "oil_gas",
    "energy": "oil_gas",
    "chemicals": "chemicals",
    "specialty_chemicals": "specialty_chemicals",
    "specialty_chem": "specialty_chemicals",
    "defence": "defence",
    "defense": "defence",
    "power": "power",
    "utilities": "utilities",
    "renewable_energy": "renewable_energy",
    "renewables": "renewable_energy",
    "telecom": "telecom",
    "infrastructure": "infrastructure",
    "real_estate": "real_estate",
    "realty": "real_estate",
    "aviation": "aviation",
    "logistics": "logistics",
    "textiles": "textiles",
    "consumer_durables": "consumer_durables",
    "consumer": "consumer_durables",
}

NO_CSKP_ACTIONS = (
    "fetch_during_ask",
    "fetch_during_research",
    "fetch_during_forecast",
    "trigger_builders_from_user_request",
    "call_external_providers",
    "recommend_buy_sell",
    "construct_sector_on_ask",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "cskp") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def canonicalize(sector: str | None) -> str | None:
    if not sector:
        return None
    key = str(sector).strip().lower().replace(" ", "_").replace("&", "and").replace("-", "_")
    key = key.replace("oil_and_gas", "oil_gas")
    return SECTOR_ALIASES.get(key, key if key in SECTOR_UNIVERSE else None)


class RawSectorDraft(BaseModel):
    """Derived tip before validation — never from live external APIs."""

    draft_id: str = Field(default_factory=lambda: new_id("rawsec"))
    sector_key: str
    label: str
    source_layers: list[str] = Field(default_factory=list)
    company_tips: list[dict[str, Any]] = Field(default_factory=list)
    macro_tips: dict[str, Any] = Field(default_factory=dict)
    market_tips: dict[str, Any] = Field(default_factory=dict)
    event_tips: list[dict[str, Any]] = Field(default_factory=list)
    research_tips: dict[str, Any] = Field(default_factory=dict)
    catalog: dict[str, Any] = Field(default_factory=dict)
    trigger: str = "ops_refresh"  # company_change | macro_change | policy | earnings | ma | ops_refresh
    importance: Importance = "Medium"
    collected_at: datetime = Field(default_factory=utc_now)


class SectorKnowledgeObject(BaseModel):
    """Published institutional sector knowledge — versioned."""

    sko_id: str = Field(default_factory=lambda: new_id("sko"))
    sector_key: str
    label: str
    current_outlook: Outlook = "Neutral"
    revenue_trend: Trend = "Unknown"
    margin_trend: Trend = "Unknown"
    valuation: str | None = None
    growth_drivers: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    government_policy: list[str] = Field(default_factory=list)
    macro_sensitivity: dict[str, str] = Field(default_factory=dict)
    leading_companies: list[str] = Field(default_factory=list)
    market_share_notes: list[str] = Field(default_factory=list)
    sector_confidence: float = 0.7
    knowledge_freshness_sec: int = 0
    materiality_tier: MaterialityTier = "Low"
    materiality_score: float = 0.0
    learning_generated: bool = False
    version: int = 1
    parent_sko_id: str | None = None
    source_layers: list[str] = Field(default_factory=list)
    company_coverage: int = 0
    normalized: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    published: bool = False
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    programme_version: str = CSKP_VERSION
    trigger: str = "ops_refresh"

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        data["providers_queried"] = []
        data["ask_triggers_collection"] = False
        data["constructed_on_request"] = False
        return data


class SectorLearningEvent(BaseModel):
    learning_id: str = Field(default_factory=lambda: new_id("slearn"))
    sko_id: str
    sector_key: str
    topic: str
    summary: str
    materiality_tier: MaterialityTier
    trigger: str
    source_layers: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    programme_version: str = CSKP_VERSION

    def to_public_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SectorCalendarEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: new_id("scal"))
    sector_key: str | None = None
    event: str
    importance: Importance = "Medium"
    status: str = "Scheduled"
    window: str | None = None
    notes: str | None = None
