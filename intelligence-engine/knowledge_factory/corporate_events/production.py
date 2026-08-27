"""ICEI production facade — soft surface for routes / Mission Control."""

from __future__ import annotations

from typing import Any

from knowledge_factory.corporate_events import store as icei_store
from knowledge_factory.corporate_events.dashboard import corporate_events_dashboard
from knowledge_factory.corporate_events.objects.compile import compile_company_timeline
from knowledge_factory.corporate_events.pipeline import run_corporate_events_pipeline
from knowledge_factory.corporate_events.schema import FREEZE_LOCKS, ICEI_VERSION, LAYER, PROGRAMME
from knowledge_factory.corporate_events.timeline.build import replay_as_of


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "layer": LAYER,
        "version": ICEI_VERSION,
        "architecture_status": "SOFT_CORPORATE_EVENT_INTELLIGENCE",
        "not_a_reasoning_engine": True,
        "not_a_planner": True,
        "not_governance": True,
        "not_learning_system": True,
        "never_invent_events": True,
        "point_in_time_integrity": True,
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/corporate-events",
        "stack": [
            "Corporate Event Object",
            "Company Event Timeline",
            "Point-in-Time Replay",
            "Company Intelligence (soft upstream)",
            "Historical Depth (soft upstream)",
            "Knowledge Factory (frozen)",
            "Phase 1–7 Reasoning (frozen)",
        ],
    }


def dashboard(**kwargs: Any) -> dict[str, Any]:
    return corporate_events_dashboard(**kwargs)


def run_pipeline(**kwargs: Any) -> dict[str, Any]:
    return run_corporate_events_pipeline(**kwargs)


def get_company_events(ticker: str, *, refresh: bool = False) -> dict[str, Any]:
    t = str(ticker or "").upper()
    if not refresh:
        row = icei_store.get_timeline(t)
        if row:
            return row
    return compile_company_timeline(t, persist=True)


def get_company_timeline(ticker: str, *, as_of: str | None = None, refresh: bool = False) -> dict[str, Any]:
    tl = get_company_events(ticker, refresh=refresh)
    if as_of:
        return replay_as_of(tl, as_of)
    return {
        "kind": "company_timeline",
        "ticker": tl.get("ticker"),
        "events": tl.get("events") or [],
        "event_count": tl.get("event_count"),
        "by_year": tl.get("by_year"),
        "linked_evidence": tl.get("linked_evidence"),
        "relationships": tl.get("relationships"),
        "quality": tl.get("quality"),
        "icei_version": ICEI_VERSION,
        "fabricated": False,
    }


def events_today() -> dict[str, Any]:
    from datetime import date

    today = date.today().isoformat()
    rows = [e for e in icei_store.list_events() if str(e.get("announcement_date") or "")[:10] == today]
    return {"date": today, "n": len(rows), "events": rows, "version": ICEI_VERSION}


def events_critical(*, limit: int = 50) -> dict[str, Any]:
    rows = [e for e in icei_store.list_events() if e.get("importance") == "Critical"]
    rows = sorted(rows, key=lambda e: e.get("announcement_date") or "", reverse=True)[:limit]
    return {"n": len(rows), "events": rows, "version": ICEI_VERSION}


def search(q: str, *, limit: int = 25) -> dict[str, Any]:
    query = str(q or "").strip().upper()
    if icei_store.event_count() == 0:
        run_corporate_events_pipeline()
    hits = []
    for e in icei_store.list_events():
        blob = f"{e.get('company')} {e.get('type')} {e.get('title')} {e.get('category')}".upper()
        if not query or query in blob:
            hits.append(
                {
                    "event_id": e.get("event_id"),
                    "company": e.get("company"),
                    "type": e.get("type"),
                    "category": e.get("category"),
                    "announcement_date": e.get("announcement_date"),
                    "importance": e.get("importance"),
                    "title": e.get("title"),
                }
            )
        if len(hits) >= limit:
            break
    return {"q": q, "n": len(hits), "results": hits, "version": ICEI_VERSION}
