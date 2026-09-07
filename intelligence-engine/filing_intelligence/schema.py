"""Filing Intelligence Layer (FIL) V1 — schemas.

Primary question: What do the company's own filings actually say?
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

FIL_VERSION = "filing-intelligence-layer-v1.0.0"

EVIDENCE_TIERS = {
    1: "official_filing",
    2: "investor_presentation",
    3: "transcript",
    4: "press_release",
    5: "external_commentary",
}

DOC_TYPES = (
    "annual_report",
    "quarterly_results",
    "investor_presentation",
    "transcript",
    "presentation_deck",
    "shareholding_filing",
    "board_meeting",
    "dividend_announcement",
    "acquisition_filing",
    "capital_raise",
    "governance_report",
    "sustainability_report",
    "press_release",
    "regulatory_filing",
)

VALIDATION_STATUS = ("verified", "partially_verified", "needs_review", "rejected")


@dataclass
class FilingDocument:
    doc_id: str
    ticker: str
    company: str
    doc_type: str
    title: str
    period: str
    as_of: str
    url: str = ""
    evidence_tier: int = 1
    source_publisher: str = ""
    pages: int | None = None
    text: str = ""
    tables: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedFact:
    fact_id: str
    ticker: str
    metric: str
    value: float | str
    unit: str
    period: str
    doc_id: str
    section: str
    page: str | int | None = None
    evidence_tier: int = 1
    confidence: float = 0.9
    validation_status: str = "verified"
    category: str = "financial"  # financial|note|segment|management|guidance|risk|capital|ownership|governance
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TimelineEvent:
    event_id: str
    ticker: str
    doc_id: str
    as_of: str
    period: str
    summary: str
    metrics: list[str] = field(default_factory=list)
    management_view: str = ""
    risks: list[str] = field(default_factory=list)
    guidance: list[str] = field(default_factory=list)
    capital_allocation: list[str] = field(default_factory=list)
    evidence_links: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
