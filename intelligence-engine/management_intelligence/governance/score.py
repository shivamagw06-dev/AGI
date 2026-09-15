"""Governance engine — independence, controversies, related-party, auditor."""

from __future__ import annotations

from typing import Any


def governance_score(board: dict[str, Any] | None, events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    board = board or {}
    events = events or []
    base = 70.0
    if "independent" in str(board.get("independence") or "").lower():
        base += 10.0
    if board.get("audit_committee") == "active":
        base += 5.0
    high = sum(1 for e in events if e.get("severity") == "high")
    med = sum(1 for e in events if e.get("severity") == "medium")
    base -= 12.0 * high + 5.0 * med
    score = max(0.0, min(100.0, base))
    return {
        "governance": round(score, 1),
        "board": board,
        "events": events,
        "high_severity_events": high,
    }
