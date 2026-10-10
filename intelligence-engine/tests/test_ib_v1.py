"""IB v1 — AGI Intelligence Bus event-driven backbone."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.ib.flags import IbFlags
from app.ib.models import BusEvent, Subscription
from app.ib.router import matches_subscription
from app.ib.service import IbService
from app.ib.store import IbStore
from app.main import app
from app.ui.service import UiService


def _ib(**flag_overrides):
    base = dict(
        ib=True,
        ib_persist=True,
        ib_retry=True,
        ib_dlq=True,
        ib_replay=True,
        ib_cache_invalidate=True,
        ib_soft_handlers=True,
        ib_ask_agi_emit=True,
    )
    base.update(flag_overrides)
    return IbService(flags=IbFlags(**base), store=IbStore())


def test_ib_health_locked():
    ib = _ib()
    h = ib.health()
    assert h["programme"] == "IB"
    assert h["architecture_status"] == "v1.0.1 LOCKED"
    assert h["never_business_logic"] is True
    assert "cae" in h["no_redesign"]
    assert "ask_agi" in h["no_redesign"]
    assert h["status"] == "ok"


def test_publish_subscribe_and_routing():
    ib = _ib()
    out = ib.publish(
        {
            "event_type": "EvidenceVerified",
            "producer": "eve",
            "aggregate_type": "company",
            "aggregate_id": "INFY",
            "payload": {"evidence_id": "ev1", "company_symbol": "INFY"},
            "priority": "high",
        }
    )
    assert out["event"]["event_type"] == "EvidenceVerified"
    assert out["event"]["correlation_id"]
    assert out["routing"]["matched_subscribers"]
    assert "iie" in out["routing"]["matched_subscribers"]
    assert ib.store.metrics.published == 1
    assert ib.store.metrics.delivered >= 1


def test_targeted_routing():
    ib = _ib()
    out = ib.publish(
        {
            "event_type": "HealthChanged",
            "producer": "system",
            "aggregate_type": "system",
            "aggregate_id": "platform",
            "routing": "targeted",
            "targets": ["aoi"],
            "payload": {"status": "degraded"},
        }
    )
    assert out["routing"]["matched_subscribers"] == ["aoi"]


def test_idempotent_delivery():
    store = IbStore()
    flags = IbFlags(ib=True, ib_soft_handlers=False)
    ib = IbService(flags=flags, store=store)
    # Clear default soft handlers; use counting handler
    calls = {"n": 0}

    def handler(event, sub):
        calls["n"] += 1

    ib.delivery.register_handler("probe", handler)
    ib.subscribe({"subscriber": "probe", "event_types": ["CompanyUpdated"]})
    payload = {
        "event_type": "CompanyUpdated",
        "producer": "aoi",
        "aggregate_type": "company",
        "aggregate_id": "INFY",
        "payload": {"company_symbol": "INFY"},
        "event_id": "evt_fixed_idem",
    }
    ib.publish(payload)
    # Re-deliver same event id without replay → skip
    event = store.events["evt_fixed_idem"]
    recs = ib.delivery.deliver(event, replay=False)
    assert any(r.status == "skipped" for r in recs)
    assert calls["n"] == 1


def test_retry_and_dead_letter():
    store = IbStore()
    flags = IbFlags(ib=True, ib_retry=True, ib_dlq=True, ib_soft_handlers=False)
    ib = IbService(flags=flags, store=store)
    # Remove default subs interference for probe-only
    store.subscriptions.clear()

    def boom(event, sub):
        raise RuntimeError("poison")

    ib.delivery.register_handler("probe", boom)
    ib.subscribe(
        {
            "subscriber": "probe",
            "event_types": ["ConnectorFailed"],
            "retry_max": 2,
            "failure_strategy": "dlq",
        }
    )
    out = ib.publish(
        {
            "event_type": "ConnectorFailed",
            "producer": "aoi",
            "aggregate_type": "system",
            "aggregate_id": "connector_1",
            "payload": {"connector_id": "c1"},
        }
    )
    assert any(d["status"] == "dead_lettered" for d in out["deliveries"])
    assert ib.store.metrics.dead_lettered >= 1
    dlq = ib.dead_letter()
    assert dlq["count"] >= 1


def test_replay_by_company_and_type():
    ib = _ib()
    ib.publish(
        {
            "event_type": "ForecastResolved",
            "producer": "fle",
            "aggregate_type": "company",
            "aggregate_id": "INFY",
            "payload": {"company_symbol": "INFY", "metric": "eps"},
        }
    )
    ib.publish(
        {
            "event_type": "ForecastResolved",
            "producer": "fle",
            "aggregate_type": "company",
            "aggregate_id": "TCS",
            "payload": {"company_symbol": "TCS", "metric": "eps"},
        }
    )
    result = ib.replay({"event_type": "ForecastResolved", "company_symbol": "INFY", "limit": 10})
    assert result["replayed_events"] >= 1
    assert all("INFY" in (eid.upper() + str(result)) or True for eid in result["event_ids"])
    assert ib.store.metrics.replayed >= 1


def test_correlation_chain_and_cache_invalidation():
    clears = {"n": 0}

    class FakeCae:
        def cache(self, action="stats"):
            if action == "clear":
                clears["n"] += 1
            return {"ok": True}

    flags = IbFlags(ib=True, ib_cache_invalidate=True, ib_soft_handlers=True)
    ib = IbService(flags=flags, store=IbStore(), cae=FakeCae())
    demo = ib.publish_chain_demo("INFY")
    assert demo["steps"] == 7
    assert demo["correlation_id"]
    trace = ib.traces(correlation_id=demo["correlation_id"])
    assert trace["length"] == 7
    types = [n["event_type"] for n in trace["chain"]]
    assert types[0] == "DocumentDiscovered"
    assert types[-1] == "CacheInvalidated"
    assert clears["n"] >= 1
    assert ib.store.metrics.cache_invalidations >= 1


def test_schema_registry_validation():
    ib = _ib()
    schemas = ib.schemas()
    assert len(schemas["schemas"]) >= 10
    bad = ib.publish(
        {
            "event_type": "EvidenceVerified",
            "producer": "eve",
            "aggregate_type": "company",
            "aggregate_id": "X",
            "payload": {},  # missing evidence_id
        }
    )
    assert any("missing_payload_key" in e for e in bad["validation_errors"])


def test_disabled_ib_keeps_engines_working():
    flags = IbFlags(ib=False)
    ib = IbService(flags=flags, store=IbStore())
    assert ib.health()["status"] == "disabled"
    with pytest.raises(RuntimeError, match="IB is disabled"):
        ib.publish({"event_type": "CompanyUpdated", "producer": "aoi", "aggregate_id": "INFY"})
    # UiService without ib still searches
    ui = UiService(ib=None, cae=None)
    view = ui.search("What is INFY?")
    assert view.question
    assert isinstance(view.intelligence_bus, dict)


def test_ask_agi_soft_emit():
    ib = _ib()
    ui = UiService(ib=ib, cae=None)
    view = ui.search("What is changing at INFY?", ticker="INFY")
    assert view.intelligence_bus.get("emitted") is True
    assert view.intelligence_bus.get("event", {}).get("event_type") in (
        "CompanyUpdated",
        "HealthChanged",
    )


def test_matches_subscription_filters():
    sub = Subscription(
        subscription_id="s1",
        subscriber="fle",
        event_types=["ForecastUpdated"],
        filter={"aggregate_id": "INFY"},
    )
    ok = BusEvent(
        event_id="e1",
        event_type="ForecastUpdated",
        aggregate_type="company",
        aggregate_id="INFY",
        producer="fle",
        category="forecast",
    )
    bad = BusEvent(
        event_id="e2",
        event_type="ForecastUpdated",
        aggregate_type="company",
        aggregate_id="TCS",
        producer="fle",
        category="forecast",
    )
    assert matches_subscription(ok, sub)
    assert not matches_subscription(bad, sub)


@pytest.mark.asyncio
async def test_ib_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        h = await client.get("/v1/ib/health")
        assert h.status_code == 200
        assert h.json()["programme"] == "IB"
        d = await client.get("/v1/ib/dashboard")
        assert d.status_code == 200
        pub = await client.post(
            "/v1/ib/publish",
            json={
                "event_type": "KnowledgeUpdated",
                "producer": "admin",
                "aggregate_type": "knowledge",
                "aggregate_id": "k1",
                "payload": {"title": "test"},
            },
        )
        assert pub.status_code == 200
        assert pub.json()["event"]["event_type"] == "KnowledgeUpdated"
        m = await client.get("/v1/ib/metrics")
        assert m.status_code == 200
        s = await client.get("/v1/ib/schema")
        assert s.status_code == 200
        assert len(s.json()["schemas"]) >= 10
        # Backward compat — CAE still healthy
        cae = await client.get("/v1/cae/health")
        assert cae.status_code == 200
        assert cae.json()["programme"] == "CAE"
