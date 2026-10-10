"""Append-only management timeline."""

from __future__ import annotations

from typing import Any


def build_timeline(profile: dict[str, Any], *, extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    events = list(profile.get("timeline") or [])
    for g in profile.get("guidance_events") or []:
        events.append(
            {
                "as_of": g.get("as_of"),
                "event": f"Guidance [{g.get('status')}/{g.get('outcome')}] {g.get('metric')}: {g.get('statement')}",
                "type": "guidance",
            }
        )
    for e in extra or []:
        events.append(e)
    events.sort(key=lambda e: str(e.get("as_of") or ""))
    return events
