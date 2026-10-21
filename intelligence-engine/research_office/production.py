"""Research Office production facade — read APIs + morning runner."""

from __future__ import annotations

from typing import Any

from research_office import store
from research_office.dashboards.research import research_dashboard
from research_office.office.runner import run_after_scheduler_ready, run_morning_desk
from research_office.publications.builders import build_company_note
from research_office.publications.registry import get_replay
from research_office.schema import FREEZE_LOCKS, PROGRAMME, RO_VERSION
from research_office.telemetry.recorder import telemetry_board


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "version": RO_VERSION,
        "soft_wire_only": True,
        "knowledge_only": True,
        "no_recommendations": True,
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/research-office",
        "office_status": store.get_status(),
    }


def dashboard() -> dict[str, Any]:
    return research_dashboard()


def run(**kwargs: Any) -> dict[str, Any]:
    return run_morning_desk(**kwargs)


def after_scheduler_ready(scheduler_result: dict[str, Any]) -> dict[str, Any]:
    return run_after_scheduler_ready(scheduler_result)


def publications(*, limit: int = 100, pub_type: str | None = None) -> dict[str, Any]:
    rows = store.list_publications(limit=limit, pub_type=pub_type)
    return {"n": len(rows), "publications": rows, "fabricated": False}


def watchlists() -> dict[str, Any]:
    return {"watchlists": store.get_watchlists(), "fabricated": False, "knowledge_only": True}


def queue() -> dict[str, Any]:
    return {"queue": store.get_queue(), "fabricated": False, "knowledge_only": True}


def company(ticker: str, *, generate: bool = False) -> dict[str, Any]:
    t = str(ticker or "").upper()
    notes = [
        p
        for p in store.list_publications(limit=200, pub_type="company_research_note")
        if t in (p.get("covered_entities") or []) or t in str(p.get("title") or "")
    ]
    if generate and not notes:
        note = build_company_note(t, trigger_reason="api_request")
        notes = [note]
    return {
        "ticker": t,
        "n": len(notes),
        "notes": notes,
        "recommendation": None,
        "knowledge_only": True,
        "fabricated": False,
    }


def history(*, limit: int = 50) -> dict[str, Any]:
    return {"n": len(store.list_history(limit=limit)), "runs": store.list_history(limit=limit), "fabricated": False}


def replay(replay_id: str) -> dict[str, Any]:
    row = get_replay(replay_id)
    if not row:
        return {"found": False, "replay_id": replay_id, "reason": "replay_unavailable"}
    return row


def telemetry(*, limit: int = 50) -> dict[str, Any]:
    return telemetry_board(limit=limit)
