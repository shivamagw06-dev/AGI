"""Timeline Builder — chronological institutional narratives from HKO + seeds."""

from __future__ import annotations

from typing import Any

from app.contracts.models import (
    Source,
    TimelineEvent,
    TimelineImportance,
    TimelineLink,
    TimelineScope,
)
from app.storage.db import HipStore
from app.timeline import traces
from app.timeline.seeds import (
    COMPANY_TIMELINE_SEEDS,
    MACRO_TIMELINE_SEEDS,
    MARKET_TIMELINE_SEEDS,
    SECTOR_TIMELINE_SEEDS,
)


def _year_from_date(value: str | None) -> int | None:
    if not value:
        return None
    raw = str(value)
    if raw.startswith("FY") and len(raw) >= 6:
        try:
            return int(raw[2:6])
        except ValueError:
            return None
    try:
        return int(raw[:4])
    except ValueError:
        return None


def _event_key(scope: str, subject: str, year: int, title: str) -> str:
    return f"{subject}:{year}:{title}"


class TimelineBuilder:
    def __init__(self, store: HipStore) -> None:
        self.store = store

    def rebuild_all(self, symbols: list[str]) -> dict[str, Any]:
        span = traces.begin("timeline_generation", meta={"symbols": symbols})
        # Market + macro once
        market_n = len(self.build_market_timeline(persist=True))
        macro_n = len(self.build_macro_timeline(persist=True))
        company_counts: dict[str, int] = {}
        sector_keys: set[str] = set()
        for symbol in symbols:
            events = self.build_company_timeline(symbol, persist=True)
            company_counts[symbol.upper()] = len(events)
            entity = self.store.get_entity(symbol)
            if entity and entity.get("sector_key"):
                sector_keys.add(str(entity["sector_key"]))
        sector_counts = {
            sk: len(self.build_sector_timeline(sk, persist=True)) for sk in sorted(sector_keys)
        }
        out = {
            "companies": company_counts,
            "sectors": sector_counts,
            "market_events": market_n,
            "macro_events": macro_n,
        }
        traces.end(span, output={"companies": len(company_counts), "sectors": len(sector_counts)})
        return out

    def build_company_timeline(self, symbol: str, *, persist: bool = True) -> list[dict[str, Any]]:
        symbol = symbol.upper()
        span = traces.begin("timeline_generation", meta={"scope": "company", "symbol": symbol})
        entity = self.store.get_entity(symbol) or {}
        nodes: dict[tuple[int, str], TimelineEvent] = {}

        # Institutional narrative seeds
        for seed in COMPANY_TIMELINE_SEEDS.get(symbol, []):
            year = int(seed["year"])
            title = str(seed["title"])
            links = [
                TimelineLink(**lnk) if isinstance(lnk, dict) else lnk
                for lnk in (seed.get("links") or [])
            ]
            ev = TimelineEvent(
                scope=TimelineScope.COMPANY,
                subject_key=symbol,
                year=year,
                title=title,
                description=seed.get("description"),
                importance=TimelineImportance(seed.get("importance") or TimelineImportance.HIGH.value),
                event_type=seed.get("event_type") or "institutional",
                source=Source.DERIVED,
                links=links,
            )
            nodes[(year, title)] = ev

        # Derive from stored corporate events / actions / financials
        for row in self.store.list_events(symbol, limit=200):
            year = _year_from_date(row.get("effective_date"))
            if year is None:
                continue
            title = (row.get("knowledge") or {}).get("subject") or (row.get("knowledge") or {}).get("event_type") or "Corporate Event"
            title = str(title)[:80]
            key = (year, title)
            if key not in nodes:
                nodes[key] = TimelineEvent(
                    scope=TimelineScope.COMPANY,
                    subject_key=symbol,
                    year=year,
                    date=row.get("effective_date"),
                    title=title,
                    description=(row.get("knowledge") or {}).get("subject"),
                    importance=TimelineImportance.MEDIUM,
                    event_type=str((row.get("knowledge") or {}).get("event_type") or "corporate"),
                    source=Source.DERIVED,
                    evidence_refs=[row.get("object_id")] if row.get("object_id") else [],
                )

        for row in self.store.list_actions(symbol, limit=100):
            year = _year_from_date(row.get("effective_date"))
            if year is None:
                continue
            action = (row.get("knowledge") or {}).get("action_type") or "Corporate Action"
            title = f"Corporate Action: {action}"
            key = (year, title)
            if key not in nodes:
                nodes[key] = TimelineEvent(
                    scope=TimelineScope.COMPANY,
                    subject_key=symbol,
                    year=year,
                    date=row.get("effective_date"),
                    title=title,
                    importance=TimelineImportance.MEDIUM,
                    event_type="corporate_action",
                    source=Source.DERIVED,
                )

        # Annual financial markers (versioned periods remain available)
        for row in self.store.list_financials(symbol, period_kind="annual", limit=50):
            year = _year_from_date(row.get("effective_date"))
            if year is None:
                continue
            title = f"Financial Year {row.get('effective_date')}"
            key = (year, title)
            if key not in nodes:
                rev = row.get("revenue") or (row.get("knowledge") or {}).get("revenue")
                nodes[key] = TimelineEvent(
                    scope=TimelineScope.COMPANY,
                    subject_key=symbol,
                    year=year,
                    date=row.get("effective_date"),
                    title=title,
                    description=f"Revenue {rev}" if rev is not None else None,
                    importance=TimelineImportance.LOW,
                    event_type="financial_period",
                    source=Source.DERIVED,
                    evidence_refs=[row.get("object_id")] if row.get("object_id") else [],
                )

        ordered = [nodes[k] for k in sorted(nodes.keys(), key=lambda x: (x[0], x[1]))]
        if persist:
            self.store.replace_timeline(TimelineScope.COMPANY.value, symbol, ordered)
            # Persist relationship edges
            for ev in ordered:
                for link in ev.links:
                    self.store.insert_timeline_link(
                        from_key=link.from_key,
                        to_key=link.to_key,
                        relation=link.relation,
                        note=link.note,
                        subject_key=symbol,
                    )

        payload = [self._public(ev, entity_name=entity.get("company_name")) for ev in ordered]
        traces.end(span, output={"count": len(payload)})
        return payload

    def build_sector_timeline(self, sector_key: str, *, persist: bool = True) -> list[dict[str, Any]]:
        sector_key = sector_key.lower().replace(" ", "_")
        span = traces.begin("timeline_generation", meta={"scope": "sector", "sector": sector_key})
        seeds = SECTOR_TIMELINE_SEEDS.get(sector_key) or []
        events = []
        for seed in seeds:
            year = int(seed["year"])
            title = str(seed["title"])
            ev = TimelineEvent(
                scope=TimelineScope.SECTOR,
                subject_key=sector_key,
                year=year,
                title=title,
                description=seed.get("description"),
                importance=TimelineImportance(seed.get("importance") or TimelineImportance.HIGH.value),
                event_type=seed.get("event_type") or "sector",
                source=Source.DERIVED,
                links=[
                    TimelineLink(
                        from_key=_event_key("macro", "india", year, title),
                        to_key=_event_key("sector", sector_key, year, title),
                        relation="caused",
                    )
                ],
            )
            events.append(ev)
        events.sort(key=lambda e: (e.year, e.title))
        if persist:
            self.store.replace_timeline(TimelineScope.SECTOR.value, sector_key, events)
        out = [self._public(e) for e in events]
        traces.end(span, output={"count": len(out)})
        return out

    def build_market_timeline(self, *, persist: bool = True) -> list[dict[str, Any]]:
        span = traces.begin("timeline_generation", meta={"scope": "market"})
        events = [
            TimelineEvent(
                scope=TimelineScope.MARKET,
                subject_key="nifty",
                year=int(seed["year"]),
                title=str(seed["title"]),
                description=seed.get("description"),
                importance=TimelineImportance(seed.get("importance") or TimelineImportance.HIGH.value),
                event_type="market",
                source=Source.DERIVED,
            )
            for seed in MARKET_TIMELINE_SEEDS
        ]
        events.sort(key=lambda e: e.year)
        if persist:
            self.store.replace_timeline(TimelineScope.MARKET.value, "nifty", events)
        out = [self._public(e) for e in events]
        traces.end(span, output={"count": len(out)})
        return out

    def build_macro_timeline(self, *, persist: bool = True) -> list[dict[str, Any]]:
        span = traces.begin("timeline_generation", meta={"scope": "macro"})
        events = [
            TimelineEvent(
                scope=TimelineScope.MACRO,
                subject_key="india",
                year=int(seed["year"]),
                title=str(seed["title"]),
                description=seed.get("description"),
                importance=TimelineImportance(seed.get("importance") or TimelineImportance.HIGH.value),
                event_type=seed.get("event_type") or "macro",
                source=Source.DERIVED,
            )
            for seed in MACRO_TIMELINE_SEEDS
        ]
        events.sort(key=lambda e: e.year)
        if persist:
            self.store.replace_timeline(TimelineScope.MACRO.value, "india", events)
        out = [self._public(e) for e in events]
        traces.end(span, output={"count": len(out)})
        return out

    @staticmethod
    def _public(ev: TimelineEvent, *, entity_name: str | None = None) -> dict[str, Any]:
        return {
            "event_id": ev.event_id,
            "scope": ev.scope.value,
            "subject_key": ev.subject_key,
            "entity_name": entity_name,
            "year": ev.year,
            "date": ev.date,
            "title": ev.title,
            "description": ev.description,
            "importance": ev.importance.value,
            "event_type": ev.event_type,
            "source": ev.source.value,
            "links": [lnk.model_dump() for lnk in ev.links],
            "evidence_refs": list(ev.evidence_refs),
            "version": ev.version,
            "key": _event_key(ev.scope.value, ev.subject_key, ev.year, ev.title),
        }
