"""KIP v2 core schema — dataclasses shared by every module.

These are plain, serializable dataclasses (dict-friendly via ``asdict``-style
``to_dict()`` methods) so the same objects can move between the extraction
pipeline, the SQLite store, the Postgres/pgvector store, and the REST layer
without translation bugs.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


def now_ts() -> float:
    return time.time()


def sha256_hex(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", errors="ignore"))
        h.update(b"\x1f")
    return h.hexdigest()


class DocType(str, Enum):
    ANNUAL_REPORT = "annual_report"
    QUARTERLY_RESULT = "quarterly_result"
    INVESTOR_PRESENTATION = "investor_presentation"
    CONFERENCE_CALL = "conference_call"
    RESEARCH_NOTE = "research_note"
    PRESS_RELEASE = "press_release"
    FILING = "filing"
    OTHER = "other"


class FactStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    REJECTED = "rejected"


KNOWLEDGE_CATEGORIES: tuple[str, ...] = (
    "business_model",
    "products",
    "segments",
    "revenue_drivers",
    "cost_drivers",
    "customers",
    "suppliers",
    "competition",
    "management",
    "risks",
    "strategy",
    "capital_allocation",
    "mna",
    "esg",
    "financial_kpis",
)

FINANCIAL_METRICS: tuple[str, ...] = (
    "revenue",
    "ebitda",
    "pat",
    "eps",
    "operating_cash_flow",
    "free_cash_flow",
    "capex",
    "debt",
    "cash",
    "roe",
    "roce",
    "ebitda_margin",
    "pat_margin",
    "gross_margin",
    "share_count",
    "dividend_per_share",
    "buyback",
    "working_capital",
    "revenue_growth",
)

MANAGEMENT_TOPICS: tuple[str, ...] = (
    "growth_priorities",
    "expansion",
    "demand_outlook",
    "pricing",
    "margin_expectations",
    "hiring",
    "ai_strategy",
    "capital_allocation",
)


@dataclass
class Evidence:
    """Module 7 contract: every fact must carry this, verbatim, or it is
    rejected before it ever reaches storage."""

    document_id: str
    page: int
    paragraph_id: str
    snippet: str
    evidence_hash: str = ""
    created_at: float = field(default_factory=now_ts)

    def __post_init__(self) -> None:
        if not self.evidence_hash:
            self.evidence_hash = sha256_hex(self.document_id, str(self.page), self.snippet[:500])

    def recompute_hash(self) -> str:
        return sha256_hex(self.document_id, str(self.page), self.snippet[:500])

    def is_hash_consistent(self) -> bool:
        return self.evidence_hash == self.recompute_hash()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Document:
    document_id: str
    company_id: str
    doc_type: str
    period: str
    title: str
    source: str
    page_count: int = 1
    published_at: Optional[str] = None
    ingested_at: float = field(default_factory=now_ts)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Paragraph:
    paragraph_id: str
    document_id: str
    company_id: str
    section: str
    page: int
    index: int
    text: str
    is_table: bool = False
    entities: list[str] = field(default_factory=list)
    importance_score: float = 0.0
    embedding: list[float] = field(default_factory=list)
    evidence_hash: str = ""

    def __post_init__(self) -> None:
        if not self.evidence_hash:
            self.evidence_hash = sha256_hex(self.document_id, str(self.page), self.text[:500])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Fact:
    """Generic evidence-backed fact record. Used as the storage envelope for
    Module 2 (structured knowledge objects), Module 3 (financial metrics) and
    Module 4 (management statements) — each sets ``category`` accordingly.
    """

    fact_id: str
    company_id: str
    category: str  # one of KNOWLEDGE_CATEGORIES, "financial_metric", "management_statement"
    key: str  # e.g. "risks", "revenue", "growth_priorities"
    value: Any
    period: Optional[str]
    unit: Optional[str]
    currency: Optional[str]
    confidence: float
    evidence: Evidence
    source_document_id: str
    timestamp: float = field(default_factory=now_ts)
    version: int = 1
    status: str = FactStatus.ACTIVE.value
    superseded_by: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["evidence"] = self.evidence.to_dict()
        return d

    @staticmethod
    def make_id(company_id: str, category: str, key: str, period: Optional[str], evidence_hash: str) -> str:
        return sha256_hex(company_id, category, key, period or "", evidence_hash)[:24]


@dataclass
class GraphNode:
    node_id: str
    node_type: str  # company|sector|industry|peer|customer|supplier|subsidiary|executive|product|fund|country|event
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphEdge:
    edge_id: str
    source_id: str
    target_id: str
    relation: str
    confidence: float = 0.7
    evidence_hash: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChangeDelta:
    delta_id: str
    company_id: str
    category: str
    key: str
    change_type: str  # new|removed|increased|decreased|changed|unchanged
    from_period: str
    to_period: str
    old_value: Any
    new_value: Any
    old_evidence: Optional[dict[str, Any]] = None
    new_evidence: Optional[dict[str, Any]] = None
    magnitude_pct: Optional[float] = None
    detected_at: float = field(default_factory=now_ts)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
