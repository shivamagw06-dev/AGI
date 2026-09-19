"""Append-only audit history for ILM/IRS."""

from __future__ import annotations

from typing import Any

_HISTORY: list[dict[str, Any]] = []


def remember_audit(row: dict[str, Any]) -> dict[str, Any]:
    registry = row.get("registry") or {}
    entry = {
        "audit_id": registry.get("audit_id"),
        "question": row.get("question"),
        "status": row.get("audit_status"),
        "reasoning_score": row.get("reasoning_score"),
        "traceability": (row.get("traceability") or {}).get("traceability"),
        "replay_id": (row.get("reasoning_replay") or {}).get("replay_id"),
        "created_at": registry.get("created_at"),
        "feed_into": ["ILM", "IRS"],
    }
    _HISTORY.append(entry)
    if len(_HISTORY) > 1000:
        del _HISTORY[:-1000]
    return entry


def history_stats() -> dict[str, Any]:
    return {
        "stored": len(_HISTORY),
        "recent": list(reversed(_HISTORY[-5:])),
        "append_only": True,
    }
