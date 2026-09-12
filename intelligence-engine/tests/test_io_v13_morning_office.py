"""AGI V1.3 / V1.3.1 — Institutional Morning Office tests (snapshot hot path)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from investment_office.v13_schema import (
    IO_V13_PLATFORM,
    IO_V13_PRODUCT,
    IO_V13_VERSION,
    IO_V13_WORKSTREAM_ID,
    MISSION,
    POLICY,
    RESEARCH_QUEUE_STAGES,
)
from investment_office.morning_snapshot import put_snapshot, reset_for_tests
from investment_office.production import (
    calendar_v13,
    daily_brief,
    generate_morning_brief,
    morning_office,
    morning_overview,
    opportunities_v13,
    refresh_morning_office,
    research_queue_v13,
    soft_slice_morning_office,
)


def setup_module():
    reset_for_tests()
    put_snapshot(
        {
            "ok": True,
            "enabled": True,
            "admin_only": True,
            "workstream_id": IO_V13_WORKSTREAM_ID,
            "product": IO_V13_PRODUCT,
            "platform": IO_V13_PLATFORM,
            "version": IO_V13_VERSION,
            "mission": MISSION,
            "role": "desk",
            "policy": POLICY,
            "generated_at": "2026-07-30T00:00:00Z",
            "header": {
                "greeting": "Good Morning",
                "title": "Investment Office",
                "subtitle": "Institutional Daily Briefing",
                "date": {"weekday": "Thursday"},
                "research_queue_count": 2,
            },
            "top_summary": {
                "market_mood": "Neutral",
                "global_risk": "Moderate",
                "research_queue": 2,
                "companies_updated_overnight": 1,
                "reports_refreshed": 0,
                "critical_alerts": 0,
                "macro_events_today": 0,
                "earnings_today": 0,
                "research_ready": None,
                "institutional_coverage_complete": 1,
            },
            "executive_brief": {"narrative": "Seeded brief", "bullets": ["a"]},
            "priorities": [],
            "overnight_activity": [],
            "research_queue": {
                "count": 2,
                "stages": {s: 0 for s in RESEARCH_QUEUE_STAGES},
                "items": [],
            },
            "opportunities": [],
            "market_summary": {},
            "macro": {"todays_events": []},
            "calendar": {"earnings_today": []},
            "portfolio_monitor": {},
            "sector_monitor": [],
            "metrics": {},
            "analyst_workspace": {"assigned_companies": [], "pending_reviews": []},
            "investment_calendar": {"today": [], "this_week": [], "macro": []},
            "ai_summary": {"text": "Seeded", "issues_recommendations": False},
            "actions": ["refresh_morning_office", "open_knowledge_operations"],
            "links": {
                "knowledge_operations": "/admin/knowledge-operations",
                "research_queue": "/admin/investment-office#research-queue",
            },
        },
        trigger="test_suite",
    )


def test_io_v13_identity():
    overview = morning_overview()
    assert overview["ok"] is True
    assert overview["admin_only"] is True
    assert overview["workstream_id"] == IO_V13_WORKSTREAM_ID
    assert overview["product"] == IO_V13_PRODUCT
    assert overview["platform"] == IO_V13_PLATFORM
    assert overview["version"] == IO_V13_VERSION
    assert overview["policy"]["buy_sell"] is False
    assert overview["policy"]["issues_recommendations"] is False
    assert "Morning Office" in MISSION or "morning" in MISSION.lower()
    assert POLICY["monitoring_only"] is True
    assert overview.get("building") is not True


def test_overview_has_required_surfaces():
    overview = morning_overview()
    for key in (
        "header",
        "top_summary",
        "executive_brief",
        "priorities",
        "overnight_activity",
        "research_queue",
        "opportunities",
        "market_summary",
        "macro",
        "calendar",
        "portfolio_monitor",
        "sector_monitor",
        "metrics",
        "analyst_workspace",
        "investment_calendar",
        "ai_summary",
        "actions",
        "links",
    ):
        assert key in overview, key

    top = overview["top_summary"]
    for k in (
        "market_mood",
        "global_risk",
        "research_queue",
        "companies_updated_overnight",
        "critical_alerts",
        "macro_events_today",
        "earnings_today",
        "institutional_coverage_complete",
    ):
        assert k in top, k

    assert overview["header"]["greeting"] == "Good Morning"
    assert overview["header"]["title"] == "Investment Office"
    assert overview["links"]["knowledge_operations"] == "/admin/knowledge-operations"
    assert "open_knowledge_operations" in overview["actions"]
    assert overview.get("cache", {}).get("source") == "morning_snapshot"


def test_research_queue_stages():
    q = research_queue_v13()
    assert q["ok"] is True
    stages = q.get("stages") or {}
    for stage in RESEARCH_QUEUE_STAGES:
        assert stage in stages
    assert isinstance(q.get("items"), list)


def test_opportunities_are_monitoring_only():
    opp = opportunities_v13()
    assert opp["ok"] is True
    assert opp["issues_recommendations"] is False
    assert "not recommendation" in (opp.get("note") or "").lower()


def test_morning_slices_and_mutations():
    mo = morning_office()
    assert mo["ok"] is True
    assert "executive_brief" in mo
    assert "priorities" in mo

    brief = daily_brief()
    assert brief["ok"] is True
    assert brief["policy"]["buy_sell"] is False

    cal = calendar_v13()
    assert cal["ok"] is True
    assert "earnings_today" in cal

    refreshed = refresh_morning_office(wait=False)
    assert refreshed["ok"] is True
    assert refreshed.get("status") in {"queued", "already_running", "running", "completed"}

    gen = generate_morning_brief()
    assert gen["ok"] is True
    assert gen["issues_recommendations"] is False
    assert "ai_summary" in gen
    assert "executive_brief" in gen

    soft = soft_slice_morning_office()
    assert soft["status"] in {"ok", "error"}
    assert soft["admin_only"] is True
    if soft["status"] == "ok":
        assert soft["buy_sell"] is False
        assert soft["route"] == "/admin/investment-office"
