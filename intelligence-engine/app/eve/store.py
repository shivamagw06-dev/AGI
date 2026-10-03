"""EVE store — immutable evidence append log; soft-delete only."""

from __future__ import annotations

from typing import Any

from app.eve.models import (
    AuditLogEntry,
    CompanyKnowledgeHealth,
    ConflictRecord,
    EvidenceObject,
    EveMetrics,
    FactVersion,
    RelationshipEvidence,
    SourceRecord,
    TimelineEvent,
    VerificationTask,
)


class EveStore:
    def __init__(self) -> None:
        self.sources: dict[str, SourceRecord] = {}
        self.evidence: dict[str, EvidenceObject] = {}  # immutable records
        self.evidence_by_fact: dict[str, list[str]] = {}  # company|fact_key -> evidence ids
        self.versions: list[FactVersion] = []
        self.conflicts: dict[str, ConflictRecord] = {}
        self.timeline: list[TimelineEvent] = []
        self.relationships: dict[str, RelationshipEvidence] = {}
        self.health: dict[str, CompanyKnowledgeHealth] = {}
        self.tasks: list[VerificationTask] = []
        self.audit: list[AuditLogEntry] = []
        self.metrics = EveMetrics()

    def add_source(self, source: SourceRecord) -> SourceRecord:
        self.sources[source.source_id] = source
        return source

    def add_evidence(self, ev: EvidenceObject) -> EvidenceObject:
        # Immutable: never overwrite existing evidence_id
        if ev.evidence_id in self.evidence:
            return self.evidence[ev.evidence_id]
        self.evidence[ev.evidence_id] = ev
        key = self._fact_index_key(ev.company_id, ev.fact_key)
        self.evidence_by_fact.setdefault(key, []).append(ev.evidence_id)
        self.metrics.evidence_count = len(self.evidence)
        self.metrics.evidence_growth += 1
        return ev

    def soft_delete_evidence(self, evidence_id: str) -> bool:
        ev = self.evidence.get(evidence_id)
        if not ev or ev.soft_deleted:
            return False
        self.evidence[evidence_id] = ev.model_copy(
            update={"soft_deleted": True, "verification_status": "soft_deleted"}
        )
        self.audit_event("soft_delete_evidence", object_kind="evidence", object_id=evidence_id)
        return True

    def active_evidence(self, *, company_id: str | None = None, fact_key: str | None = None) -> list[EvidenceObject]:
        rows = [e for e in self.evidence.values() if not e.soft_deleted]
        if company_id:
            rows = [e for e in rows if e.company_id == company_id]
        if fact_key:
            rows = [e for e in rows if e.fact_key == fact_key]
        return rows

    def add_version(self, version: FactVersion) -> None:
        self.versions.append(version)

    def add_conflict(self, conflict: ConflictRecord) -> ConflictRecord:
        self.conflicts[conflict.conflict_id] = conflict
        self.metrics.conflicts = len([c for c in self.conflicts.values() if c.status == "open"])
        return conflict

    def add_timeline(self, event: TimelineEvent) -> None:
        self.timeline.append(event)

    def add_relationship(self, rel: RelationshipEvidence) -> None:
        key = f"{rel.src}|{rel.rel}|{rel.dst}"
        self.relationships[key] = rel

    def add_task(self, task: VerificationTask) -> None:
        self.tasks.append(task)

    def audit_event(self, action: str, *, object_kind: str = "", object_id: str = "", detail: str = "") -> None:
        self.audit.append(
            AuditLogEntry(action=action, object_kind=object_kind, object_id=object_id, detail=detail)
        )

    @staticmethod
    def _fact_index_key(company_id: str | None, fact_key: str) -> str:
        return f"{company_id or 'macro'}|{fact_key}"

    def snapshot(self) -> dict[str, Any]:
        return {
            "sources": len(self.sources),
            "evidence": len(self.evidence),
            "active_evidence": len(self.active_evidence()),
            "versions": len(self.versions),
            "conflicts_open": len([c for c in self.conflicts.values() if c.status == "open"]),
            "timeline_events": len(self.timeline),
            "relationships": len(self.relationships),
            "tasks_open": len([t for t in self.tasks if t.status == "open"]),
            "audit": len(self.audit),
        }
