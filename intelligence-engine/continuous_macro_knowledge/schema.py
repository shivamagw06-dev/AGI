"""CMKP contracts — Continuous Macroeconomic Knowledge Platform (Sprint 10.1)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

CMKP_VERSION = "0.1.0"
PROGRAMME = "Continuous Macroeconomic Knowledge Platform"
PROGRAMME_SHORT = "CMKP"
PRIMARY_PRINCIPLE = (
    "Macroeconomic intelligence should behave exactly like company intelligence. "
    "Official macro releases continuously update AGI's institutional knowledge. "
    "User requests consume published macro knowledge—they never trigger data collection."
)

MacroCategory = Literal[
    "Monetary",
    "Inflation",
    "Growth",
    "Fiscal",
    "External Sector",
    "Financial Markets",
]

Importance = Literal["Critical", "High", "Medium", "Low"]
MaterialityTier = Literal["Ignore", "Low", "Medium", "High", "Critical"]

CATEGORIES: tuple[str, ...] = (
    "Monetary",
    "Inflation",
    "Growth",
    "Fiscal",
    "External Sector",
    "Financial Markets",
)

SOURCES: tuple[dict[str, Any], ...] = (
    {"source_id": "rbi", "region": "India", "role": "monetary_liquidity_fx_banking", "schedule": "event_and_daily"},
    {"source_id": "mospi", "region": "India", "role": "cpi_wpi_iip_gdp", "schedule": "official_release"},
    {"source_id": "nso", "region": "India", "role": "national_accounts", "schedule": "official_release"},
    {"source_id": "mof", "region": "India", "role": "budget_fiscal_gst", "schedule": "monthly_annual"},
    {"source_id": "cga", "region": "India", "role": "fiscal_position", "schedule": "monthly"},
    {"source_id": "sebi", "region": "India", "role": "mf_flows_capital_markets", "schedule": "periodic"},
    {"source_id": "fred", "region": "Global", "role": "us_macro", "schedule": "daily"},
    {"source_id": "imf", "region": "Global", "role": "weo_bop", "schedule": "publication"},
    {"source_id": "world_bank", "region": "Global", "role": "development_indicators", "schedule": "publication"},
    {"source_id": "oecd", "region": "Global", "role": "cli_confidence", "schedule": "publication"},
)

COLLECTION_SCHEDULE: dict[str, str] = {
    "RBI Policy": "Event-driven",
    "RBI Liquidity": "Daily",
    "CPI": "Official release",
    "WPI": "Official release",
    "GDP": "Official release",
    "IIP": "Official release",
    "Fiscal Data": "Monthly",
    "GST Collections": "Monthly",
    "Budget": "Annual",
    "FRED": "Daily",
    "IMF": "Publication-driven",
    "World Bank": "Publication-driven",
    "OECD": "Publication-driven",
    "SEBI": "Periodic",
    "CGA": "Monthly",
}

NO_CMKP_ACTIONS = (
    "fetch_during_ask",
    "fetch_during_research",
    "fetch_during_forecast",
    "trigger_collectors_from_user_request",
    "recommend_buy_sell",
    "execute_trades",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "cmkp") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class RawMacroRelease(BaseModel):
    release_id: str = Field(default_factory=lambda: new_id("raw"))
    source: str
    country: str
    category: str
    indicator: str
    current_value: float | None = None
    previous_value: float | None = None
    consensus: float | None = None
    unit: str = ""
    release_date: str
    effective_date: str | None = None
    importance: Importance = "Medium"
    payload: dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime = Field(default_factory=utc_now)


class MacroKnowledgeObject(BaseModel):
    """Versioned institutional macro knowledge object."""

    mko_id: str = Field(default_factory=lambda: new_id("mko"))
    country: str
    category: str
    indicator: str
    current_value: float | None = None
    previous_value: float | None = None
    consensus: float | None = None
    unit: str = ""
    release_date: str
    effective_date: str | None = None
    importance: Importance = "Medium"
    source: str
    freshness_sec: int = 0
    confidence: float = 0.8
    version: int = 1
    parent_mko_id: str | None = None
    materiality_tier: MaterialityTier = "Low"
    materiality_score: float = 0.0
    learning_generated: bool = False
    published: bool = False
    published_at: datetime | None = None
    normalized: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    programme_version: str = CMKP_VERSION

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        data["ask_triggers_collection"] = False
        return data


class LearningEvent(BaseModel):
    learning_id: str = Field(default_factory=lambda: new_id("mlearn"))
    mko_id: str
    topic: str
    observation: str
    learning: str
    future_guidance: str
    materiality_tier: MaterialityTier
    category: str
    indicator: str
    country: str
    created_at: datetime = Field(default_factory=utc_now)
    forecast_refresh_hint: bool = False
    history_rewritten: bool = False


class CalendarEntry(BaseModel):
    event_id: str = Field(default_factory=lambda: new_id("cal"))
    indicator: str
    country: str
    source: str
    category: str
    scheduled_date: str
    status: str = "upcoming"  # upcoming | released | delayed
    importance: Importance = "Medium"
