"""Recognise business archetypes from assembled evidence."""

from __future__ import annotations

from typing import Any

from institutional_analysts.business.brain._text import blob_of
from institutional_analysts.business.brain.archetypes.templates import ARCHETYPES


def match_archetype(evidence: dict[str, Any], frameworks: dict[str, Any] | None = None) -> dict[str, Any]:
    fw = frameworks or {}
    blob = blob_of(
        evidence.get("business_model"),
        evidence.get("advantages"),
        evidence.get("competitive_position"),
        evidence.get("revenue_drivers"),
        evidence.get("growth_opportunities"),
        evidence.get("business_risks"),
        evidence.get("capital_allocation"),
        (fw.get("moat") or {}).get("sources"),
    )

    scored = []
    for arch in ARCHETYPES:
        score = sum(1 for s in (arch.get("signals") or ()) if s in blob)
        scored.append((score, arch))
    scored.sort(key=lambda x: x[0], reverse=True)

    primary = scored[0][1] if scored and scored[0][0] > 0 else ARCHETYPES[3]  # default regulated franchise-ish
    secondary = scored[1][1] if len(scored) > 1 and scored[1][0] > 0 else None

    return {
        "primary": {
            "id": primary["id"],
            "name": primary["name"],
            "pattern": list(primary.get("pattern") or []),
            "implications": primary.get("implications"),
            "match_score": scored[0][0] if scored else 0,
        },
        "secondary": (
            {
                "id": secondary["id"],
                "name": secondary["name"],
                "pattern": list(secondary.get("pattern") or []),
                "match_score": scored[1][0],
            }
            if secondary
            else None
        ),
        "template_reasoning": (
            f"Archetype recognised: {primary['name']}. Pattern — "
            + "; ".join(primary.get("pattern") or [])
            + f". {primary.get('implications')}"
        ),
    }
