"""Sector event calendar — earnings seasons, policy, M&A watches."""

from __future__ import annotations

from typing import Any

from continuous_sector_knowledge.schema import SectorCalendarEntry


def calendar(*, limit: int = 50) -> dict[str, Any]:
    entries = [
        SectorCalendarEntry(
            sector_key=None,
            event="Pan-India earnings season",
            importance="Critical",
            status="Scheduled",
            window="Quarterly",
            notes="Updates company tips → sector refresh",
        ),
        SectorCalendarEntry(
            sector_key="banking",
            event="RBI MPC / policy transmission watch",
            importance="Critical",
            status="Scheduled",
            window="Bi-monthly",
        ),
        SectorCalendarEntry(
            sector_key="fmcg",
            event="CPI / rural demand prints",
            importance="High",
            status="Scheduled",
            window="Monthly",
        ),
        SectorCalendarEntry(
            sector_key="auto",
            event="Monthly auto sales releases",
            importance="High",
            status="Scheduled",
            window="Monthly",
        ),
        SectorCalendarEntry(
            sector_key="it_services",
            event="IT services earnings + guidance",
            importance="High",
            status="Scheduled",
            window="Quarterly",
        ),
        SectorCalendarEntry(
            sector_key="oil_gas",
            event="Crude / marketing margin watch",
            importance="High",
            status="Watching",
            window="Continuous",
        ),
        SectorCalendarEntry(
            sector_key="defence",
            event="Defence order / budget updates",
            importance="High",
            status="Watching",
            window="Event-driven",
        ),
        SectorCalendarEntry(
            sector_key="real_estate",
            event="Housing launches / rate path",
            importance="Medium",
            status="Watching",
            window="Event-driven",
        ),
        SectorCalendarEntry(
            sector_key=None,
            event="Union Budget / sector policy papers",
            importance="Critical",
            status="Scheduled",
            window="Annual",
        ),
        SectorCalendarEntry(
            sector_key=None,
            event="Significant M&A / capacity expansions",
            importance="High",
            status="Watching",
            window="Event-driven",
        ),
    ]
    rows = [e.model_dump(mode="json") for e in entries[:limit]]
    return {
        "n": len(rows),
        "calendar": rows,
        "providers_queried": [],
        "collected_on_request": False,
        "ask_triggered": False,
        "gateway": "CSKP_KRIG",
    }
