"""Determine institutional speaking order."""

from __future__ import annotations

from typing import Any

# Canonical company-research order from sprint brief
_CANONICAL = [
    "Business",
    "Financial",
    "Accounting",
    "Valuation",
    "Risk",
    "Forecast",
    "Portfolio",
    "Sector",
    "Macro",
    "Management",
    "Ownership",
    "Market",
    "News",
    "Academy",
    "Committee",
    "CIO",
]


def order_speakers(
    required: list[str],
    optional: list[str] | None = None,
    synthesis: list[str] | None = None,
) -> dict[str, Any]:
    participants = list(required)
    for a in optional or []:
        if a not in participants:
            participants.append(a)
    for a in synthesis or []:
        if a not in participants:
            participants.append(a)

    rank = {name: i for i, name in enumerate(_CANONICAL)}
    ordered = sorted(participants, key=lambda a: rank.get(a, 999))
    return {
        "speaking_order": ordered,
        "speaking_order_detailed": [
            {"order": i + 1, "analyst": a, "tier": _tier(a, required, optional or [], synthesis or [])}
            for i, a in enumerate(ordered)
        ],
        "map_version": "iar-v1",
    }


def _tier(analyst: str, required: list[str], optional: list[str], synthesis: list[str]) -> str:
    if analyst in required:
        return "required"
    if analyst in synthesis:
        return "synthesis"
    if analyst in optional:
        return "optional"
    return "other"
