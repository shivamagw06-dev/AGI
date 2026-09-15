"""RIH production facade."""

from __future__ import annotations

from typing import Any

from research_intelligence_hub.engine import ResearchIntelligenceHubEngine

_ENGINE = ResearchIntelligenceHubEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def run(*, note_id: str | None = None) -> dict[str, Any]:
    return _ENGINE.run(note_id=note_id)


def hub(note_id: str, *, persist_if_missing: bool = False) -> dict[str, Any]:
    return _ENGINE.hub(note_id, persist_if_missing=persist_if_missing)


def list_hubs(*, limit: int = 50) -> dict[str, Any]:
    return _ENGINE.list_hubs(limit=limit)


def graph(note_id: str) -> dict[str, Any]:
    return _ENGINE.graph(note_id)


def history(note_id: str, *, limit: int = 20) -> dict[str, Any]:
    return _ENGINE.history(note_id, limit=limit)


def build(
    *,
    note_id: str | None = None,
    headline: str,
    body: str = "",
    publication_date: str | None = None,
    session: str | None = None,
    tickers: list[str] | None = None,
    importance_score: int = 50,
    persist: bool = False,
) -> dict[str, Any]:
    obj = _ENGINE.build(
        note_id=note_id,
        headline=headline,
        body=body,
        publication_date=publication_date,
        session=session,
        tickers=tickers,
        importance_score=importance_score,
        persist=persist,
    )
    return {**obj.to_public_dict(), "mode": "published" if persist else "computed", "gateway": "RIH_KRIG"}
