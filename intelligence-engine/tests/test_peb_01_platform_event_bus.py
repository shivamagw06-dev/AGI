"""PEB-01 — Platform Event Bus deterministic tests."""

from __future__ import annotations

import time

from platform_event_bus.dispatcher import get_dispatcher, reset_bus_for_tests
from platform_event_bus.envelope import make_event, validate_envelope
from platform_event_bus.matching import matches
from platform_event_bus.production import health, list_events, list_types, statistics
from platform_event_bus.publisher import EventPublisher, publish
from platform_event_bus import registry as event_registry
from platform_event_bus.schema import (
    EVENT_PORTFOLIO_SNAPSHOT_CREATED,
    EVENT_PORTFOLIO_UPDATED,
    PEB01_WORKSTREAM_ID,
)
from platform_event_bus.subscriber import subscribe


def setup_function(_fn=None):
    reset_bus_for_tests()


def test_health():
    h = health()
    assert h["workstream_id"] == PEB01_WORKSTREAM_ID
    assert h["infrastructure_only"] is True
    assert h["business_logic"] is False
    assert h["persistence"] is False
    assert h["broker"] == "in_process_sync"


def test_publish_and_subscribe():
    seen = []

    def handler(evt):
        seen.append(evt["event_type"])

    subscribe("company.research.completed", handler, subscriber_id="t1")
    result = publish(
        "company.research.completed",
        producer="io-01",
        payload={"ticker": "TCS"},
    )
    assert result["ok"] is True
    assert result["matched_subscribers"] == 1
    assert seen == ["company.research.completed"]


def test_wildcard_subscription():
    seen = []
    subscribe("portfolio.*", lambda e: seen.append(e["event_type"]), subscriber_id="wild")
    publish(EVENT_PORTFOLIO_UPDATED, producer="po-01", payload={"portfolio_id": "core"})
    publish(EVENT_PORTFOLIO_SNAPSHOT_CREATED, producer="po-01", payload={"snapshot_id": "s1"})
    publish("comparison.completed", producer="cio-01", payload={})
    assert EVENT_PORTFOLIO_UPDATED in seen
    assert EVENT_PORTFOLIO_SNAPSHOT_CREATED in seen
    assert "comparison.completed" not in seen


def test_unknown_event_type_allowed_by_default():
    result = publish("custom.future.event", producer="test", payload={"x": 1}, allow_unknown=True)
    assert result["ok"] is True
    assert result["known_type"] is False


def test_unknown_event_type_rejected_when_disallowed():
    try:
        publish("custom.future.event", producer="test", allow_unknown=False)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "unknown event type" in str(exc)


def test_handler_failure_isolation():
    seen = []

    def bad(_e):
        raise RuntimeError("boom")

    def good(e):
        seen.append(e["event_id"])

    subscribe("office.error", bad, subscriber_id="bad")
    subscribe("office.error", good, subscriber_id="good")
    result = publish("office.error", producer="office_sdk", payload={"error": "x"})
    assert result["matched_subscribers"] == 2
    statuses = {d["subscriber_id"]: d["status"] for d in result["deliveries"]}
    assert statuses["bad"] == "error"
    assert statuses["good"] == "ok"
    assert len(seen) == 1
    stats = statistics()["statistics"]
    assert stats["failed_handlers"] >= 1


def test_dispatcher_ordering():
    order = []
    subscribe("comparison.completed", lambda e: order.append("a"), subscriber_id="a")
    subscribe("comparison.completed", lambda e: order.append("b"), subscriber_id="b")
    subscribe("comparison.completed", lambda e: order.append("c"), subscriber_id="c")
    publish("comparison.completed", producer="cio-01", payload={})
    assert order == ["a", "b", "c"]


def test_registry_validation_and_register():
    types = list_types()["types"]
    assert any(t["event_type"] == "portfolio.updated" for t in types)
    row = event_registry.register_event_type(
        "alerts.threshold.breached",
        description="Future alerts office",
        producer="alert-01",
    )
    assert row["builtin"] is False
    assert event_registry.is_known("alerts.threshold.breached")
    try:
        event_registry.register_event_type("bad*")
        assert False
    except ValueError:
        pass


def test_envelope_fields():
    evt = make_event("office.request.completed", producer="office_sdk", payload={"ok": True})
    assert validate_envelope(evt) == []
    for field in (
        "event_id",
        "event_type",
        "timestamp",
        "producer",
        "correlation_id",
        "payload",
        "metadata",
        "version",
    ):
        assert field in evt


def test_matching_helpers():
    assert matches("portfolio.*", "portfolio.updated")
    assert matches("*", "anything")
    assert not matches("portfolio.*", "comparison.completed")


def test_publisher_never_mutates_payload():
    payload = {"ticker": "TCS", "nested": {"a": 1}}
    seen = []

    def handler(e):
        e["payload"]["ticker"] = "MUTATED"
        e["payload"]["nested"]["a"] = 99
        seen.append(e)

    subscribe("company.research.completed", handler, subscriber_id="m")
    publish("company.research.completed", producer="io-01", payload=payload)
    assert payload["ticker"] == "TCS"
    assert payload["nested"]["a"] == 1
    assert seen[0]["payload"]["ticker"] == "MUTATED"


def test_statistics_and_events_api():
    subscribe("*", lambda e: None, subscriber_id="all")
    publish("office.request.completed", producer="office_sdk", payload={})
    stats = statistics()
    assert stats["ok"] is True
    assert stats["statistics"]["published"] >= 1
    assert "panels" in stats["statistics"]
    ev = list_events(limit=10)
    assert ev["events"]


def test_soft_publish_from_po_create():
    from portfolio_office.production import create
    from portfolio_office import store as pf_store

    pf_store.reset_for_tests()
    seen = []
    subscribe("portfolio.*", lambda e: seen.append(e["event_type"]), subscriber_id="po-watcher")
    create({"name": "Core", "holdings": [], "cash_balance": 0})
    assert EVENT_PORTFOLIO_UPDATED in seen


def test_performance_smoke():
    subscribe("office.request.completed", lambda e: None, subscriber_id="perf")
    t0 = time.perf_counter()
    for i in range(200):
        publish("office.request.completed", producer="bench", payload={"i": i})
    elapsed = time.perf_counter() - t0
    assert elapsed < 2.0  # generous bound for CI; in-process should be fast


def test_event_publisher_class():
    pub = EventPublisher("io-01")
    seen = []
    subscribe("company.research.completed", lambda e: seen.append(e["producer"]), subscriber_id="p")
    pub.publish("company.research.completed", {"ticker": "INFY"})
    assert seen == ["io-01"]
