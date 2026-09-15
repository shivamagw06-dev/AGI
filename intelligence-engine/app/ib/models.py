"""IB domain models — canonical events, subscriptions, delivery, DLQ."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.ib.config import SCHEMA_VERSION


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class BusEvent:
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    version: int = 1
    timestamp: str = field(default_factory=_now)
    producer: str = "system"
    correlation_id: str = ""
    causation_id: str = ""
    priority: str = "normal"  # critical | high | normal | low
    status: str = "published"  # published | delivering | delivered | failed | dead_lettered | replayed
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
    retry_count: int = 0
    category: str = ""
    routing: str = "broadcast"  # broadcast | targeted | topic | filtered
    targets: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    delay_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Subscription:
    subscription_id: str
    subscriber: str
    event_types: list[str] = field(default_factory=list)  # empty = all
    categories: list[str] = field(default_factory=list)
    priority: str = "normal"
    retry_max: int = 3
    timeout_ms: int = 2000
    max_concurrency: int = 4
    failure_strategy: str = "dlq"  # dlq | drop | retry
    version_compat: str = SCHEMA_VERSION
    enabled: bool = True
    filter: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DeliveryRecord:
    delivery_id: str
    event_id: str
    subscriber: str
    subscription_id: str
    status: str  # delivered | failed | skipped | retrying | dead_lettered
    attempt: int = 1
    latency_ms: float = 0.0
    error: str = ""
    idempotency_key: str = ""
    timestamp: str = field(default_factory=_now)
    replay: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DeadLetter:
    dlq_id: str
    event_id: str
    subscriber: str
    subscription_id: str
    error: str
    attempts: int
    payload_snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SchemaEntry:
    event_type: str
    schema_version: str
    category: str
    required_payload_keys: list[str] = field(default_factory=list)
    deprecated: bool = False
    migration_notes: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TraceNode:
    event_id: str
    event_type: str
    producer: str
    timestamp: str
    causation_id: str = ""
    correlation_id: str = ""
    subscribers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
