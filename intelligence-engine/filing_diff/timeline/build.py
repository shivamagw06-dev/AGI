"""Append-only change timeline."""

from __future__ import annotations

from typing import Any


def build_change_timeline(changes: list[dict[str, Any]], ctx: dict[str, Any]) -> list[dict[str, Any]]:
    events = []
    # guidance evolution first-class
    for c in changes:
        if c.get("domain") != "guidance" and c.get("materiality") in {"ignore"}:
            continue
        if c.get("cosmetic"):
            continue
        events.append(
            {
                "period": c.get("current_period"),
                "previous_period": c.get("previous_period"),
                "domain": c.get("domain"),
                "metric": c.get("metric"),
                "change_type": c.get("change_type"),
                "materiality": c.get("materiality"),
                "thesis_impact": c.get("thesis_impact"),
                "summary": c.get("what_changed"),
                "change_id": c.get("change_id"),
            }
        )
    events.sort(key=lambda e: (e.get("period") or "", e.get("domain") or ""))
    return events
