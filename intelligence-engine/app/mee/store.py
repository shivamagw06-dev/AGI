"""MEE store — immutable event append log; soft-delete only; never overwrite."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.mee.models import (
    AuditEntry,
    EventHealth,
    ImpactGraph,
    MarketEvent,
    PropagationRecord,
    RelationshipEdge,
    TimelineEntry,
)


@dataclass
class MeeMetrics:
    events_detected: int = 0
    events_verified: int = 0
    verification_latency_ms: float = 0.0
    propagation_latency_ms: float = 0.0
    duplicate_rate: float = 0.0
    false_positive_rate: float = 0.0
    timeline_entries: int = 0
    relationships: int = 0
    impact_calculations: int = 0
    queue_depth: int = 0
    api_latency_ms: float = 0.0
    processing_failures: int = 0

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        return {
            "events_detected": self.events_detected,
            "events_verified": self.events_verified,
            "verification_latency_ms": self.verification_latency_ms,
            "propagation_latency_ms": self.propagation_latency_ms,
            "duplicate_rate": self.duplicate_rate,
            "false_positive_rate": self.false_positive_rate,
            "timeline_entries": self.timeline_entries,
            "relationships": self.relationships,
            "impact_calculations": self.impact_calculations,
            "queue_depth": self.queue_depth,
            "api_latency_ms": self.api_latency_ms,
            "processing_failures": self.processing_failures,
        }


class MeeStore:
    def __init__(self) -> None:
        self.events: dict[str, MarketEvent] = {}
        self.impacts: dict[str, ImpactGraph] = {}  # by event_id
        self.timelines: list[TimelineEntry] = []
        self.relationships: dict[str, RelationshipEdge] = {}
        self.propagations: list[PropagationRecord] = []
        self.queue: list[str] = []  # event_ids awaiting verify/propagate
        self.audit: list[AuditEntry] = []
        self.health = EventHealth()
        self.metrics = MeeMetrics()

    def add_event(self, event: MarketEvent) -> MarketEvent:
        if event.event_id in self.events:
            return self.events[event.event_id]
        self.events[event.event_id] = event
        self.metrics.events_detected = len(self.events)
        self.queue.append(event.event_id)
        self.metrics.queue_depth = len(self.queue)
        self._refresh_health()
        self.audit_event("add_event", object_kind="event", object_id=event.event_id)
        return event

    def mark_status(self, event_id: str, status: str, *, verified: bool = False) -> None:
        ev = self.events.get(event_id)
        if not ev or ev.soft_deleted:
            return
        ev.status = status
        if verified:
            from app.mee.models import now_iso

            ev.verified_at = now_iso()
            self.metrics.events_verified = len(
                [e for e in self.events.values() if e.status in {"verified", "published", "resolved"}]
            )
        self._refresh_health()
        self.audit_event("mark_status", object_kind="event", object_id=event_id, detail=status)

    def supersede(self, old_id: str, new_event: MarketEvent) -> MarketEvent:
        old = self.events.get(old_id)
        if old:
            old.status = "superseded"
        new_event.parent_event_id = old_id
        new_event.version = (old.version + 1) if old else new_event.version
        return self.add_event(new_event)

    def mark_duplicate(self, event_id: str, of_id: str) -> None:
        ev = self.events.get(event_id)
        if not ev:
            return
        ev.duplicate_of = of_id
        ev.status = "archived"
        dupes = len([e for e in self.events.values() if e.duplicate_of])
        total = max(1, len(self.events))
        self.metrics.duplicate_rate = round(dupes / total, 4)
        self._refresh_health()

    def soft_delete(self, event_id: str) -> bool:
        ev = self.events.get(event_id)
        if not ev or ev.soft_deleted:
            return False
        ev.soft_deleted = True
        ev.status = "archived"
        self.audit_event("soft_delete", object_kind="event", object_id=event_id)
        self._refresh_health()
        return True

    def active_events(
        self,
        *,
        company_id: str | None = None,
        sector_id: str | None = None,
        theme_id: str | None = None,
        category: str | None = None,
        event_type: str | None = None,
        status: str | None = None,
        severity: str | None = None,
    ) -> list[MarketEvent]:
        rows = [e for e in self.events.values() if not e.soft_deleted and not e.duplicate_of]
        if company_id:
            rows = [
                e
                for e in rows
                if company_id in e.company_ids or company_id in e.company_symbols
            ]
        if sector_id:
            rows = [e for e in rows if sector_id in e.sector_ids]
        if theme_id:
            rows = [e for e in rows if theme_id in e.theme_ids]
        if category:
            rows = [e for e in rows if e.category == category]
        if event_type:
            rows = [e for e in rows if e.event_type == event_type]
        if status:
            rows = [e for e in rows if e.status == status]
        if severity:
            rows = [e for e in rows if e.severity == severity]
        return rows

    def put_impact(self, graph: ImpactGraph) -> ImpactGraph:
        self.impacts[graph.event_id] = graph
        self.metrics.impact_calculations = len(self.impacts)
        return graph

    def add_timeline(self, entry: TimelineEntry) -> None:
        self.timelines.append(entry)
        self.metrics.timeline_entries = len(self.timelines)

    def add_relationship(self, edge: RelationshipEdge) -> None:
        key = f"{edge.from_id}|{edge.relation_type}|{edge.to_id}"
        self.relationships[key] = edge
        self.metrics.relationships = len(self.relationships)

    def add_propagation(self, rec: PropagationRecord) -> None:
        self.propagations.append(rec)

    def dequeue(self, event_id: str) -> None:
        self.queue = [e for e in self.queue if e != event_id]
        self.metrics.queue_depth = len(self.queue)

    def audit_event(self, action: str, *, object_kind: str = "", object_id: str = "", detail: str = "") -> None:
        self.audit.append(
            AuditEntry(action=action, object_kind=object_kind, object_id=object_id, detail=detail)
        )

    def _refresh_health(self) -> None:
        active = [e for e in self.events.values() if not e.soft_deleted]
        verified = [e for e in active if e.status in {"verified", "published", "resolved"}]
        pending = [e for e in active if e.status in {"detected", "updated"}]
        conf = [e.confidence for e in active]
        self.health = EventHealth(
            events_total=len(active),
            verified=len(verified),
            pending=len(pending),
            duplicates=len([e for e in self.events.values() if e.duplicate_of]),
            queue_depth=len(self.queue),
            avg_confidence=round(sum(conf) / len(conf), 4) if conf else 0.0,
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "events": len(self.events),
            "active_events": len(self.active_events()),
            "impacts": len(self.impacts),
            "timelines": len(self.timelines),
            "relationships": len(self.relationships),
            "propagations": len(self.propagations),
            "queue": len(self.queue),
            "audit": len(self.audit),
        }
