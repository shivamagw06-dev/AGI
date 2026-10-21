"""Derive lessons and institutional narrative from historical outcomes + cases."""

from __future__ import annotations

from typing import Any


def derive_lessons(
    *,
    company: str,
    timeline: list[dict[str, Any]],
    quality_path: list[dict[str, Any]],
    cases: dict[str, Any],
    archetype: dict[str, Any],
    moat: dict[str, Any],
) -> dict[str, Any]:
    lessons: list[str] = []
    lessons.extend(list(cases.get("lessons_from_cases") or [])[:4])

    pressure_themes = {"funding_pressure", "margin_pressure", "integration"}
    strengthening = {"funding_advantage", "growth"}
    recent = timeline[-3:] if timeline else []
    earlier = timeline[: max(0, len(timeline) - 3)] if timeline else []

    recent_pressure = any(e.get("theme") in pressure_themes for e in recent)
    earlier_strength = any(e.get("theme") in strengthening for e in earlier)
    durability = str(moat.get("durability") or "Medium")

    narrative = ""
    if timeline and recent_pressure and earlier_strength:
        last_events = ", ".join(f"{e.get('year')} {e.get('event')}" for e in recent if e.get("event"))
        narrative = (
            f"Although the {company} franchise remains structurally {durability.lower()}, "
            "the committee notes that deposit competition and related funding pressure have gradually "
            "reduced one of the historical advantages. The moat remains durable, but the trajectory "
            f"is no longer strengthening as it did historically ({last_events})."
        )
        lessons.append(
            "A durable moat can coexist with a non-strengthening trajectory — monitor advantage erosion early."
        )
    elif timeline:
        narrative = (
            f"Historical sequence for {company}: "
            + " → ".join(f"{e.get('year')} {e.get('event')}" for e in timeline[-6:])
            + f". Current moat durability assessed as {durability.lower()}."
        )
    else:
        narrative = (
            f"No seeded multi-year outcome path for {company}; lessons currently draw from "
            f"archetype ({(archetype.get('primary') or {}).get('name')}) and case analogues "
            f"({cases.get('primary_success_analogue')} vs {cases.get('primary_failure_analogue')})."
        )

    quality_trend = "Stable"
    if len(quality_path) >= 2:
        first = float(quality_path[0].get("business_quality") or 0)
        last = float(quality_path[-1].get("business_quality") or 0)
        if last - first >= 3:
            quality_trend = "Improving"
        elif first - last >= 3:
            quality_trend = "Deteriorating"
        # Prefer recent turn
        if len(quality_path) >= 3:
            peak = max(float(p.get("business_quality") or 0) for p in quality_path)
            if peak - last >= 2:
                quality_trend = "Softening from peak"
                lessons.append(
                    "Business quality can roll over from a peak even while the franchise remains high quality."
                )

    if archetype.get("template_reasoning"):
        lessons.append(str((archetype.get("primary") or {}).get("implications") or "")[:220])

    lessons = [x for x in lessons if x][:8]
    return {
        "historical_narrative": narrative,
        "lessons_learned": lessons,
        "quality_path": quality_path,
        "quality_trend": quality_trend,
        "timeline": timeline,
        "trajectory_note": (
            "Moat durable but trajectory no longer strengthening"
            if recent_pressure and earlier_strength
            else quality_trend
        ),
    }
