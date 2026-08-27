"""MEE domain models — immutable canonical market events."""

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
class ImpactNode:
    order: int  # 1 direct, 2 second-order, 3 third-order
    entity_type: str  # company | sector | theme | macro
    entity_id: str
    impact: str = "indirect"
    description: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ImpactGraph:
    impact_id: str
    event_id: str
    direct: list[ImpactNode] = field(default_factory=list)
    indirect: list[ImpactNode] = field(default_factory=list)
    first_order: list[ImpactNode] = field(default_factory=list)
    second_order: list[ImpactNode] = field(default_factory=list)
    third_order: list[ImpactNode] = field(default_factory=list)
    chain: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "impact_id": self.impact_id,
            "event_id": self.event_id,
            "direct": [n.to_dict() for n in self.direct],
            "indirect": [n.to_dict() for n in self.indirect],
            "first_order": [n.to_dict() for n in self.first_order],
            "second_order": [n.to_dict() for n in self.second_order],
            "third_order": [n.to_dict() for n in self.third_order],
            "chain": list(self.chain),
            "created_at": self.created_at,
        }


@dataclass
class MarketEvent:
    event_id: str
    event_type: str
    category: str
    subcategory: str = ""
    title: str = ""
    summary: str = ""
    created_at: str = field(default_factory=_now)
    detected_at: str = field(default_factory=_now)
    verified_at: str | None = None
    effective_date: str | None = None
    event_time: str | None = None
    severity: str = "medium"
    confidence: float = 0.0
    importance: str = "normal"
    status: str = "detected"
    source_count: int = 0
    evidence_ids: list[str] = field(default_factory=list)
    evidence_links: list[dict[str, Any]] = field(default_factory=list)
    version: int = 1
    parent_event_id: str = ""
    company_ids: list[str] = field(default_factory=list)
    company_symbols: list[str] = field(default_factory=list)
    sector_ids: list[str] = field(default_factory=list)
    theme_ids: list[str] = field(default_factory=list)
    forecast_ids: list[str] = field(default_factory=list)
    risk_ids: list[str] = field(default_factory=list)
    catalyst_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    country: str = "IN"
    expected_duration: str = ""
    monitoring_checklist: list[str] = field(default_factory=list)
    forecast_implications: list[str] = field(default_factory=list)
    portfolio_implications: list[str] = field(default_factory=list)
    historical_analogues: list[str] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    origin: str = "eve"  # eve | iie | fle | user | scheduled
    soft_deleted: bool = False
    duplicate_of: str = ""
    merged_into: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RelationshipEdge:
    edge_id: str
    from_id: str
    to_id: str
    relation_type: str
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PropagationRecord:
    propagation_id: str
    event_id: str
    targets: list[str] = field(default_factory=list)  # iie | fle | pmo | ime | ams | ask_agi
    status: str = "queued"  # queued | running | done | failed
    idempotency_key: str = ""
    detail: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TimelineEntry:
    entry_id: str
    scope: str  # company | sector | theme
    scope_id: str
    event_id: str
    event_type: str
    title: str
    effective_date: str | None
    severity: str
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EventHealth:
    events_total: int = 0
    verified: int = 0
    pending: int = 0
    duplicates: int = 0
    queue_depth: int = 0
    avg_confidence: float = 0.0
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditEntry:
    action: str
    object_kind: str = ""
    object_id: str = ""
    detail: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
