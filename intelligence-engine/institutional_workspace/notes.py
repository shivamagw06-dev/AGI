"""RW-01 research notes — analyst-owned; never mutate system intelligence."""

from __future__ import annotations

import hashlib
from typing import Any, Optional

from institutional_workspace.models import ResearchNote

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


_NOTES: dict[str, list[ResearchNote]] = {}


def reset_for_tests() -> None:
    _NOTES.clear()


def _nid(title: str, context_key: str) -> str:
    return f"note-{hashlib.sha256(f'{context_key}|{title}'.encode()).hexdigest()[:12]}"


def add_note(
    *,
    context_key: str,
    title: str,
    body: str,
    tags: tuple[str, ...] = (),
    linked_decision_id: str = "",
    linked_object_id: str = "",
    author: str = "analyst",
) -> ResearchNote:
    note = ResearchNote(
        note_id=_nid(title, context_key),
        title=title,
        body=body,
        tags=tags,
        linked_decision_id=linked_decision_id,
        linked_object_id=linked_object_id,
        author=author,
        created_at=now_iso(),
        system_generated=False,
    )
    _NOTES.setdefault(context_key, []).append(note)
    return note


def list_notes(context_key: str) -> tuple[ResearchNote, ...]:
    return tuple(_NOTES.get(context_key) or ())


def seed_demo_notes(context_key: str, *, ticker: str = "", portfolio_id: str = "") -> tuple[ResearchNote, ...]:
    """Non-system demo notes for empty workspaces — clearly analyst-owned."""
    if _NOTES.get(context_key):
        return list_notes(context_key)
    if ticker:
        add_note(
            context_key=context_key,
            title=f"{ticker} — desk watchpoint",
            body="Analyst note: track next disclosure cycle and liability franchise commentary.",
            tags=("desk", "watch"),
            linked_object_id=ticker,
        )
    if portfolio_id:
        add_note(
            context_key=context_key,
            title=f"{portfolio_id} — rebalance reminder",
            body="Analyst note: revisit concentration after committee conditions clear.",
            tags=("portfolio", "rebalance"),
            linked_object_id=portfolio_id,
        )
    return list_notes(context_key)


def notes_metrics() -> dict[str, Any]:
    return {
        "contexts": sorted(_NOTES.keys()),
        "note_count": sum(len(v) for v in _NOTES.values()),
        "orphaned_notes": sum(
            1
            for rows in _NOTES.values()
            for n in rows
            if not n.linked_decision_id and not n.linked_object_id
        ),
    }
