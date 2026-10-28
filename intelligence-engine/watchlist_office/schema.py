"""WO-01 Watchlist Office — schema constants."""

from __future__ import annotations

WO01_WORKSTREAM_ID = "WO-01"
WO01_OFFICE_ID = "wo-01"
WO01_PRODUCT = "Watchlist Office"
WO01_VERSION = "wo-01-v1.0.0"
WO01_SUBSYSTEM = "watchlist_office"
WO01_SPEC = "docs/WO_01_WATCHLIST_OFFICE.md"
WO01_RECOMMENDATION_POLICY = "research_queue_no_buy_sell_no_research"
WO01_DOMAIN = "portfolio"

ENTRY_STATUSES = ("New", "Reviewing", "Monitoring", "Archived")
ENTRY_PRIORITIES = ("Critical", "High", "Medium", "Low")

WQR_SECTIONS = (
    "watchlist_summary",
    "research_queue",
    "by_status",
    "by_priority",
    "recent_events",
    "confidence_summary",
    "evidence_references",
)

WQR_SECTION_TITLES = {
    "watchlist_summary": "Watchlist Summary",
    "research_queue": "Research Queue",
    "by_status": "By Status",
    "by_priority": "By Priority",
    "recent_events": "Recent Events",
    "confidence_summary": "Confidence Summary",
    "evidence_references": "Evidence References",
}
