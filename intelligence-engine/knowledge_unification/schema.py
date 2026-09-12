"""KUL schema — deterministic plan / evidence / coverage objects."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


QUESTION_TYPES = (
    "company",
    "concept",
    "accounting",
    "financial_statement",
    "business_model",
    "industry",
    "moat",
    "unit_economics",
    "comparison",
    "business_risk",
    "valuation",
    "consensus",
    "macro",
    "market",
    "portfolio",
    "news",
    "unknown",
)


@dataclass
class QueryPlan:
    question: str
    question_types: list[str]
    company_hint: Optional[str] = None
    ticker_hint: Optional[str] = None
    concept_hint: Optional[str] = None
    requires_company: bool = False
    requires_deterministic_finance: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderSpec:
    id: str
    label: str
    coverage: str
    priority: int  # lower = higher priority
    supported_question_types: tuple[str, ...]
    typical_latency_ms: int
    confidence_ceiling: float
    health: str = "unknown"  # ok | degraded | empty | error | unknown

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["supported_question_types"] = list(self.supported_question_types)
        return d


@dataclass
class ProviderResult:
    provider_id: str
    ok: bool
    empty: bool
    latency_ms: int
    confidence: float
    facts: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    why: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    rejected_reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgePlan:
    query: QueryPlan
    provider_ids: list[str]
    rationale: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query.to_dict(),
            "provider_ids": list(self.provider_ids),
            "rationale": list(self.rationale),
        }


@dataclass
class CoverageObject:
    coverage_level: str  # high | medium | low | none
    knowledge_sources_used: list[str]
    confidence: float
    evidence_strength: str  # strong | moderate | weak | none
    missing_information: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FusedEvidence:
    summary: str
    why: list[str]
    evidence: list[dict[str, Any]]
    company_intelligence: dict[str, Any]
    concept_intelligence: dict[str, Any]
    coverage: CoverageObject
    provider_results: list[ProviderResult]
    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "why": list(self.why),
            "evidence": list(self.evidence),
            "company_intelligence": self.company_intelligence,
            "concept_intelligence": self.concept_intelligence,
            "coverage": self.coverage.to_dict(),
            "provider_results": [p.to_dict() for p in self.provider_results],
            "diagnostics": self.diagnostics,
        }
