"""Timeline engine — queryable institutional events from evidence."""

from __future__ import annotations

from app.eve.config import TIMELINE_EVENT_HINTS
from app.eve.models import EvidenceObject, TimelineEvent
from app.eve.store import EveStore


def maybe_timeline_event(store: EveStore, evidence: EvidenceObject) -> TimelineEvent | None:
    blob = f"{evidence.fact_key} {evidence.value_text} {evidence.raw_field}".lower()
    event_type = None
    for etype, hints in TIMELINE_EVENT_HINTS.items():
        if any(h in blob for h in hints):
            event_type = etype
            break
    if event_type is None:
        # Still record guidance / board / shareholding as timeline-ish
        if evidence.fact_key in {"guidance", "board", "management", "shareholding", "capex"}:
            event_type = {
                "guidance": "guidance_revision",
                "board": "board_change",
                "management": "ceo_appointment",
                "shareholding": "board_change",
                "capex": "capacity_expansion",
            }.get(evidence.fact_key, "update")
        else:
            return None

    title = f"{(evidence.company_symbol or evidence.company_id or 'Macro')} — {event_type.replace('_', ' ').title()}"
    event = TimelineEvent(
        company_id=evidence.company_id,
        company_symbol=evidence.company_symbol,
        event_type=event_type,
        title=title,
        detail=evidence.value_text[:500],
        event_date=evidence.provenance.observation_timestamp or evidence.created_at[:10],
        evidence_ids=[evidence.evidence_id],
        confidence=evidence.confidence,
    )
    # Dedup similar recent events
    for existing in store.timeline[-50:]:
        if (
            existing.company_id == event.company_id
            and existing.event_type == event.event_type
            and existing.detail[:80] == event.detail[:80]
        ):
            return None
    store.add_timeline(event)
    return event


def company_timeline(store: EveStore, company_id: str) -> list[TimelineEvent]:
    rows = [e for e in store.timeline if e.company_id == company_id]
    rows.sort(key=lambda e: e.event_date or e.created_at or "", reverse=True)
    return rows
