"""Knowledge Bundle — the standard object consumed by the Intelligence Engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.krig.policies import BundleSection, QueryType


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeBundle(BaseModel):
    bundle_id: str = Field(default_factory=lambda: str(uuid4()))
    query_type: QueryType
    subjects: list[str] = Field(default_factory=list)
    question: str | None = None
    company: dict[str, Any] | None = None
    companies: dict[str, Any] = Field(default_factory=dict)  # compare mode
    financials: list[dict[str, Any]] = Field(default_factory=list)
    valuation: dict[str, Any] | None = None
    corporate_events: list[dict[str, Any]] = Field(default_factory=list)
    sector: dict[str, Any] | None = None
    market: dict[str, Any] | None = None
    macro: dict[str, Any] | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    learning: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    monitoring: list[dict[str, Any]] = Field(default_factory=list)
    memory: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    comparison: dict[str, Any] | None = None
    freshness: dict[str, Any] = Field(default_factory=dict)
    confidence: dict[str, Any] = Field(default_factory=dict)
    cache: dict[str, Any] = Field(default_factory=dict)
    sections_present: dict[str, bool] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(
        default_factory=lambda: {
            "gateway": "KRIG",
            "version": "0.5.0",
            "providers_hidden": True,
            "operate": {"kfe": True, "kce": True},
        }
    )
    assembled_at: datetime = Field(default_factory=utc_now)

    def checklist(self) -> dict[str, bool]:
        """Human-facing readiness checklist for Ask / ops."""
        return {
            "Company": bool(self.company or self.companies),
            "Financials": bool(self.financials),
            "Valuation": bool(self.valuation),
            "Corporate Events": bool(self.corporate_events),
            "Sector": bool(self.sector),
            "Market": bool(self.market or self.macro),
            "Historical Learning": bool(self.learning or self.timeline),
            "Monitoring": bool(self.monitoring),
            "Evidence": bool(self.evidence or self.relationships),
            "Memory": bool(self.memory),
        }

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["checklist"] = self.checklist()
        return data


def empty_section_flags(sections: tuple[BundleSection, ...]) -> dict[str, bool]:
    return {s.value: False for s in sections}
