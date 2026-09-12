"""WO-01 — Watchlist Office deterministic + event-driven workflow tests."""

from __future__ import annotations

from office_sdk.contracts import SCHEMA_EVIDENCE_BLOCK, SCHEMA_RESPONSE, office_request
from office_sdk.registry import dispatch
from platform_event_bus.dispatcher import reset_bus_for_tests
from platform_event_bus.publisher import publish
from platform_event_bus.schema import (
    EVENT_BUSINESS_QUALITY_UPDATED,
    EVENT_COMPANY_RESEARCH_COMPLETED,
    EVENT_COMPARISON_COMPLETED,
    EVENT_WATCHLIST_COMPANY_ADDED,
    EVENT_WATCHLIST_COMPANY_REMOVED,
)

from watchlist_office.events import ensure_subscriptions, reset_subscriptions_for_tests
from watchlist_office.production import (
    add,
    create,
    get_queue,
    get_watchlist,
    health,
    remove,
    soft_slice_mission_control,
)
from watchlist_office.schema import WO01_OFFICE_ID, WO01_WORKSTREAM_ID
from watchlist_office import store as wl_store


def setup_function(_fn=None):
    reset_bus_for_tests()
    reset_subscriptions_for_tests()
    wl_store.reset_for_tests()


def _seed():
    return create({"name": "Core", "owner": "desk"})


def test_health_event_driven():
    h = health()
    assert h["workstream_id"] == WO01_WORKSTREAM_ID
    assert h["office_id"] == WO01_OFFICE_ID
    assert h["performs_research"] is False
    assert h["buy_sell"] is False
    assert h["event_driven"] is True
    assert "watchlist.company.added" in h["publishes"]
    assert "company.research.completed" in h["subscribes"]


def test_create_and_add_publishes_event():
    seen = []
    from platform_event_bus.subscriber import subscribe

    subscribe(EVENT_WATCHLIST_COMPANY_ADDED, lambda e: seen.append(e["payload"]["ticker"]), subscriber_id="cap")
    _seed()
    out = add("Core", {"ticker": "TCS", "priority": "High", "tags": ["it"]})
    assert out["ok"] is True
    assert out["created"] is True
    assert out["entry"]["status"] == "New"
    assert "TCS" in seen


def test_remove_publishes_event():
    seen = []
    from platform_event_bus.subscriber import subscribe

    subscribe(EVENT_WATCHLIST_COMPANY_REMOVED, lambda e: seen.append(e["payload"]["ticker"]), subscriber_id="rem")
    _seed()
    add("core", {"ticker": "INFY"})
    remove("core", "INFY")
    assert "INFY" in seen
    q = get_queue("core")
    assert q["counts"]["active"] == 0


def test_research_completed_updates_queue():
    ensure_subscriptions()
    _seed()
    add("Core", {"ticker": "TCS", "status": "New"})
    publish(
        EVENT_COMPANY_RESEARCH_COMPLETED,
        producer="io-01",
        payload={"ticker": "TCS", "package_type": "Institutional Brief"},
    )
    q = get_queue("Core")
    entry = q["queue"][0]
    assert entry["ticker"] == "TCS"
    assert entry["status"] == "Reviewing"  # New → Reviewing on research
    assert entry["last_research_at"]
    assert entry["last_event_type"] == EVENT_COMPANY_RESEARCH_COMPLETED
    assert entry["research_refs"]


def test_comparison_and_quality_events():
    ensure_subscriptions()
    _seed()
    add("Core", {"ticker": "HDFCBANK"})
    add("Core", {"ticker": "ICICIBANK"})
    publish(
        EVENT_COMPARISON_COMPLETED,
        producer="cio-01",
        payload={"tickers": ["HDFCBANK", "ICICIBANK"], "comparison_type": "Institutional Comparison"},
    )
    publish(
        EVENT_BUSINESS_QUALITY_UPDATED,
        producer="fire-06",
        payload={"ticker": "HDFCBANK", "overall_score": 0.81},
    )
    q = get_queue("Core")
    by = {e["ticker"]: e for e in q["queue"]}
    assert by["HDFCBANK"]["last_comparison_at"]
    assert by["ICICIBANK"]["last_comparison_at"]
    assert by["HDFCBANK"]["last_business_quality_score"] == 0.81


def test_full_event_driven_workflow():
    """User add → watchlist.added → (simulated) research → queue refresh."""
    ensure_subscriptions()
    bus_seen = []
    from platform_event_bus.subscriber import subscribe

    subscribe("watchlist.*", lambda e: bus_seen.append(e["event_type"]), subscriber_id="wf")
    _seed()
    add("Core", {"ticker": "TCS", "priority": "Critical"})
    assert EVENT_WATCHLIST_COMPANY_ADDED in bus_seen

    # Downstream research completes (IO-01 would publish this)
    publish(
        EVENT_COMPANY_RESEARCH_COMPLETED,
        producer="io-01",
        payload={"ticker": "TCS", "package_type": "Company Snapshot"},
    )
    pack = get_watchlist("Core")
    assert pack["ok"] is True
    assert pack["office_response"]["schema"] == SCHEMA_RESPONSE
    assert pack["office_response"]["report_type"] == "watchlist_queue_report"
    entry = pack["queue"]["queue"][0]
    assert entry["last_research_at"]
    assert pack["office_response"]["sections"][0]["blocks"][0]["schema"] == SCHEMA_EVIDENCE_BLOCK


def test_office_sdk_dispatch():
    _seed()
    add("core", {"ticker": "RELIANCE"})
    req = office_request(office_id="wo-01", options={"watchlist_id": "core"})
    resp = dispatch(req)
    assert resp["ok"] is True
    assert resp["metadata"]["office_id"] == "wo-01"
    assert resp["payload"]["watchlist_id"] == "core"


def test_queue_ordering():
    _seed()
    add("Core", {"ticker": "AAA", "priority": "Low", "status": "Monitoring"})
    add("Core", {"ticker": "BBB", "priority": "Critical", "status": "New"})
    add("Core", {"ticker": "CCC", "priority": "High", "status": "Reviewing"})
    q = get_queue("Core")["queue"]
    # New before Reviewing before Monitoring; within same status by priority
    assert q[0]["ticker"] == "BBB"
    assert q[1]["ticker"] == "CCC"
    assert q[2]["ticker"] == "AAA"


def test_soft_slice():
    _seed()
    add("Core", {"ticker": "TCS"})
    slice_ = soft_slice_mission_control()
    assert slice_["workstream_id"] == WO01_WORKSTREAM_ID
    assert slice_["panels"]["total_entries"] >= 1


def test_no_research_engine():
    h = health()
    assert h["performs_research"] is False
    assert "FIRE" not in str(h.get("role"))
