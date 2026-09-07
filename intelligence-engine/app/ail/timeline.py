"""Timeline Engine — complete historical company timeline with evidence IDs."""

from __future__ import annotations

from typing import Any

from app.ail.catalog import COMPANIES
from app.ail.models import CorporateEvent, EvidenceRecord, TimelineEntry, utc_now
from app.ail.store import AilStore


class TimelineEngine:
    def __init__(self, store: AilStore) -> None:
        self.store = store

    def ensure_seed(self, ticker: str, *, evidence_ids: list[str] | None = None) -> None:
        t = ticker.upper()
        if self.store.timeline_for(t):
            return
        profile = COMPANIES.get(t) or {}
        company = str(profile.get("company") or t)
        for row in profile.get("timeline_seed") or []:
            self.store.add_timeline(
                TimelineEntry(
                    ticker=t,
                    company=company,
                    year=int(row.get("year") or utc_now().year),
                    title=str(row.get("title")),
                    category=str(row.get("category") or "history"),
                    evidence_ids=list(evidence_ids or []),
                )
            )

    def add_from_event(self, event: CorporateEvent) -> TimelineEntry:
        entry = TimelineEntry(
            ticker=event.ticker,
            company=event.company,
            year=event.timestamp.year,
            timestamp=event.timestamp,
            title=f"{event.category}: {(event.new_value or '')[:120]}",
            category=event.category,
            evidence_ids=list(event.evidence_ids),
            event_id=event.event_id,
        )
        return self.store.add_timeline(entry)

    def add_from_evidence(self, evidence: EvidenceRecord) -> TimelineEntry | None:
        if not evidence.ticker:
            return None
        entry = TimelineEntry(
            ticker=evidence.ticker,
            company=evidence.company or evidence.ticker,
            year=(evidence.retrieved_at or utc_now()).year,
            timestamp=evidence.retrieved_at or utc_now(),
            title=evidence.claim[:160],
            category="evidence",
            evidence_ids=[evidence.evidence_id],
        )
        return self.store.add_timeline(entry)

    def get(self, ticker: str, *, limit: int = 100) -> dict[str, Any]:
        self.ensure_seed(ticker)
        entries = sorted(
            self.store.timeline_for(ticker),
            key=lambda e: (e.year or 0, e.timestamp),
            reverse=True,
        )
        return {
            "programme": "TIMELINE",
            "ticker": ticker.upper(),
            "entries": [e.to_dict() for e in entries[:limit]],
            "count": len(entries),
        }
