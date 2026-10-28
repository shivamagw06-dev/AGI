"""Investment calendar — package known categories; withhold dates without evidence."""

from __future__ import annotations

from typing import Any

from app.schemas.models import CalendarEvent

CATEGORIES = [
    "earnings",
    "rbi",
    "fed",
    "inflation",
    "gdp",
    "corporate_action",
    "agm",
    "dividend",
    "policy",
    "results",
]


def build_calendar(
    *,
    macro: dict[str, Any] | None = None,
    pre_market: dict[str, Any] | None = None,
    symbols: list[str] | None = None,
) -> list[CalendarEvent]:
    events: list[CalendarEvent] = []
    symbols = symbols or []

    # Pull structured event-ish blocks when present — never invent dates
    economist = (macro or {}).get("chiefEconomistBrief") or {}
    for risk in (economist.get("keyRisks") or [])[:4]:
        label = risk.get("label") or "Macro risk"
        events.append(
            CalendarEvent(
                category="policy",
                title=str(label),
                date=None,
                status="tentative",
                evidence=["agib:macro-briefing"],
                note=str(risk.get("why") or "From macro briefing — date not asserted."),
            )
        )

    morning = (pre_market or {}).get("morningNote") or {}
    for item in (morning.get("watchlist") or morning.get("events") or [])[:6]:
        if isinstance(item, dict):
            title = item.get("title") or item.get("label") or item.get("symbol")
            date = item.get("date") or item.get("when")
            cat = str(item.get("category") or "other").lower()
            if cat not in CATEGORIES and cat != "other":
                cat = "other"
            events.append(
                CalendarEvent(
                    category=cat,  # type: ignore[arg-type]
                    title=str(title or "Pre-market item"),
                    date=str(date) if date else None,
                    status="scheduled" if date else "tentative",
                    evidence=["agib:pre-market-briefing"],
                    symbols=[str(item.get("symbol"))] if item.get("symbol") else [],
                    note=str(item.get("detail") or item.get("why") or "")[:240] or None,
                )
            )
        elif isinstance(item, str) and item.strip():
            events.append(
                CalendarEvent(
                    category="other",
                    title=item.strip()[:120],
                    status="tentative",
                    evidence=["agib:pre-market-briefing"],
                )
            )

    # Scaffold tracked categories so workspace always shows the investment calendar shape
    present = {e.category for e in events}
    for cat in CATEGORIES:
        if cat in present:
            continue
        events.append(
            CalendarEvent(
                category=cat,  # type: ignore[arg-type]
                title=f"{cat.replace('_', ' ').title()} — awaiting calendar feed",
                date=None,
                status="withheld",
                evidence=[],
                symbols=symbols[:3] if cat in {"earnings", "results", "dividend", "agm", "corporate_action"} else [],
                note="Date withheld — Investment Office does not invent event timing.",
            )
        )

    return events[:40]
