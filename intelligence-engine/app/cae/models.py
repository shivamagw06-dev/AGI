"""CAE domain models — query plans, ranked items, unified context packages."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def new_id(prefix: str) -> str:
    return _id(prefix)


def now_iso() -> str:
    return _now()


@dataclass
class QueryPlan:
    plan_id: str
    query: str
    intents: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    primary_ticker: str | None = None
    engines: list[str] = field(default_factory=list)
    expand_relationships: bool = False
    reasoning_strategy: str = "balanced_institutional"
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RankedItem:
    item_id: str
    engine: str
    kind: str
    title: str
    content: Any
    priority: str = "important"  # critical | important | optional
    relevance: float = 0.0
    freshness: float = 0.0
    confidence: float = 0.0
    evidence_quality: float = 0.0
    forecast_accuracy: float = 0.0
    event_severity: float = 0.0
    source_trust: float = 0.0
    knowledge_quality: float = 0.0
    ranking_score: float = 0.0
    why_included: str = ""
    token_estimate: int = 0
    version: str = "1"
    timestamp: str = field(default_factory=_now)
    retrieval_latency_ms: float = 0.0
    dedupe_key: str = ""
    compressed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EngineContribution:
    engine: str
    requested: bool = False
    succeeded: bool = False
    item_count: int = 0
    latency_ms: float = 0.0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContextPackage:
    package_id: str
    query: str
    query_summary: str = ""
    plan: dict[str, Any] = field(default_factory=dict)
    entities: list[str] = field(default_factory=list)
    knowledge: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    investment_intelligence: list[dict[str, Any]] = field(default_factory=list)
    forecasts: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    risks: list[dict[str, Any]] = field(default_factory=list)
    catalysts: list[dict[str, Any]] = field(default_factory=list)
    macro: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    confidence_summary: dict[str, Any] = field(default_factory=dict)
    recommended_reasoning_strategy: str = "balanced_institutional"
    engine_contributions: list[dict[str, Any]] = field(default_factory=list)
    ranking: list[dict[str, Any]] = field(default_factory=list)
    token_usage: dict[str, Any] = field(default_factory=dict)
    duplicates_removed: int = 0
    compression_ratio: float = 1.0
    cache_hit: bool = False
    assembly_latency_ms: float = 0.0
    explain: list[dict[str, Any]] = field(default_factory=list)
    # Soft-compat payloads for Ask AGI existing fields
    soft_fields: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CacheEntry:
    key: str
    package: dict[str, Any]
    created_at: float
    expires_at: float
    hits: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "hits": self.hits,
            "package_id": (self.package or {}).get("package_id"),
        }


@dataclass
class AuditEntry:
    action: str
    object_kind: str = ""
    object_id: str = ""
    detail: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
