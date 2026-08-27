"""Macro release calendar — upcoming official publications."""

from __future__ import annotations

from typing import Any

from continuous_macro_knowledge.schema import CalendarEntry
from continuous_macro_knowledge.store import STORE

_SEED_CALENDAR: list[CalendarEntry] = [
    CalendarEntry(
        indicator="CPI",
        country="India",
        source="mospi",
        category="Inflation",
        scheduled_date="2026-08-12",
        importance="Critical",
    ),
    CalendarEntry(
        indicator="WPI",
        country="India",
        source="mospi",
        category="Inflation",
        scheduled_date="2026-08-14",
        importance="High",
    ),
    CalendarEntry(
        indicator="IIP",
        country="India",
        source="mospi",
        category="Growth",
        scheduled_date="2026-08-12",
        importance="High",
    ),
    CalendarEntry(
        indicator="GDP",
        country="India",
        source="nso",
        category="Growth",
        scheduled_date="2026-08-29",
        importance="Critical",
    ),
    CalendarEntry(
        indicator="MPC Decision",
        country="India",
        source="rbi",
        category="Monetary",
        scheduled_date="2026-08-08",
        importance="Critical",
    ),
    CalendarEntry(
        indicator="GST Collections",
        country="India",
        source="mof",
        category="Fiscal",
        scheduled_date="2026-08-01",
        importance="High",
    ),
    CalendarEntry(
        indicator="US CPI",
        country="United States",
        source="fred",
        category="Inflation",
        scheduled_date="2026-08-13",
        importance="High",
    ),
    CalendarEntry(
        indicator="FOMC Decision",
        country="United States",
        source="fred",
        category="Monetary",
        scheduled_date="2026-09-17",
        importance="Critical",
    ),
]


def calendar(*, limit: int = 50) -> dict[str, Any]:
    entries = list(_SEED_CALENDAR)
    # Mark released if we have published MKO matching indicator recently
    out = []
    for e in entries:
        status = e.status
        latest = STORE.latest(e.indicator.replace("MPC Decision", "Repo Rate").replace("FOMC Decision", "Federal Funds Rate"), country=e.country)
        if latest and latest.published:
            # Keep upcoming for future dates; tip only
            pass
        row = e.model_dump(mode="json")
        row["status"] = status
        out.append(row)
    return {
        "n": min(limit, len(out)),
        "calendar": out[:limit],
        "ask_triggered": False,
        "note": "Official release calendar tips — collectors run on schedule, not on Ask",
    }
