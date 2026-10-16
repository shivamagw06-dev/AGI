"""RW-01 InstitutionalWorkspace — presentation object over linked institutional intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class TimelineEvent:
    event_id: str
    timestamp: str
    kind: str
    title: str
    object_type: str
    object_id: str
    summary: str = ""
    severity: str = "info"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "kind": self.kind,
            "title": self.title,
            "object_type": self.object_type,
            "object_id": self.object_id,
            "summary": self.summary,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class LinkedObject:
    object_type: str
    object_id: str
    label: str
    href: str
    relation: str = "related"
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "object_id": self.object_id,
            "label": self.label,
            "href": self.href,
            "relation": self.relation,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    source_type: str
    title: str
    date: str = ""
    href: str = ""
    linked_object_ids: tuple[str, ...] = ()
    snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_type": self.source_type,
            "title": self.title,
            "date": self.date,
            "href": self.href,
            "linked_object_ids": list(self.linked_object_ids),
            "snippet": self.snippet,
        }


@dataclass(frozen=True)
class ResearchNote:
    note_id: str
    title: str
    body: str
    tags: tuple[str, ...] = ()
    linked_decision_id: str = ""
    linked_object_id: str = ""
    author: str = "analyst"
    created_at: str = ""
    system_generated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "note_id": self.note_id,
            "title": self.title,
            "body": self.body,
            "tags": list(self.tags),
            "linked_decision_id": self.linked_decision_id,
            "linked_object_id": self.linked_object_id,
            "author": self.author,
            "created_at": self.created_at,
            "system_generated": False,
            "mutates_system_intelligence": False,
        }


@dataclass(frozen=True)
class InstitutionalWorkspace:
    workspace_id: str
    context: str
    active_object: str
    title: str
    timeline: tuple[TimelineEvent, ...] = ()
    linked_objects: tuple[LinkedObject, ...] = ()
    sections: dict[str, Any] = field(default_factory=dict)
    evidence: tuple[EvidenceItem, ...] = ()
    notes: tuple[ResearchNote, ...] = ()
    navigation: tuple[str, ...] = ()
    ask_deep_link: str = ""
    diagnostics: Optional[dict[str, Any]] = None
    generated_at: str = ""
    ticker: str = ""
    portfolio_id: str = ""
    mutates_system_intelligence: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "context": self.context,
            "active_object": self.active_object,
            "title": self.title,
            "timeline": [e.to_dict() for e in self.timeline],
            "linked_objects": [o.to_dict() for o in self.linked_objects],
            "sections": dict(self.sections or {}),
            "evidence": [e.to_dict() for e in self.evidence],
            "notes": [n.to_dict() for n in self.notes],
            "navigation": list(self.navigation),
            "ask_deep_link": self.ask_deep_link,
            "diagnostics": dict(self.diagnostics or {}),
            "generated_at": self.generated_at,
            "ticker": self.ticker,
            "portfolio_id": self.portfolio_id,
            "mutates_system_intelligence": False,
            "generates_recommendations": False,
            "presentation_only": True,
            "timeline_count": len(self.timeline),
            "linked_count": len(self.linked_objects),
            "evidence_count": len(self.evidence),
            "note_count": len(self.notes),
        }
