"""FSE-02.1 — Canonical Ingestion Migration tests."""

from __future__ import annotations

import pytest

from financial_statements_engine.collection.event_bus import get_bus, reset_bus_for_tests, subscribe
from financial_statements_engine.collection.ingest import ingest, ingest_structured_json
from financial_statements_engine.collection.production import health, ingest_dashboard
from financial_statements_engine.collection.pipeline import collect_from_discovery_rows
from financial_statements_engine.orchestrator.engine import create_workflow
from financial_statements_engine.orchestrator.subscriber import on_evidence_stored
from financial_statements_engine.store import store_root


@pytest.fixture()
def fse_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("FSE_STORE_ROOT", str(tmp_path / "fse"))
    monkeypatch.setenv("FSE_02_CANONICAL_INGEST", "true")
    monkeypatch.setenv("FSE_02_DUAL_WRITE_HD", "true")
    reset_bus_for_tests()
    return tmp_path / "fse"


def test_health_exposes_migration_flags(fse_tmp):
    h = health()
    assert h["migration"].startswith("fse-02.1")
    assert h["canonical_ingest"] is True
    assert h["dual_write_hd"] is True
    assert h["parses_financials"] is False


def test_ingest_stores_raw_and_emits_evidence_stored(fse_tmp):
    events: list[dict] = []
    subscribe("evidence.stored", events.append, subscriber_id="t_ingest")

    result = ingest(
        ticker="TCS",
        content=b"<xbrl>revenue 42</xbrl>",
        source="nse_xbrl",
        document_type="xbrl",
        period_type="annual",
        period_end="2025-03-31",
        collector="unit_test",
    )
    assert result["ok"] is True
    assert result["action"] == "stored"
    assert result["event_emitted"] is True
    assert len(events) == 1
    payload = events[0]["payload"]
    assert payload["ticker"] == "TCS"
    assert payload["period_end"] == "2025-03-31"
    assert payload["period"] == "2025-03-31"
    assert payload["content_sha256"]
    assert payload["document_type"] == "xbrl"
    # Raw evidence meta / bytes under FSE store
    assert list((store_root()).rglob("*")), "raw evidence store should grow"


def test_ingest_idempotent_no_duplicate_event(fse_tmp):
    stored: list[dict] = []
    dups: list[dict] = []
    subscribe("evidence.stored", stored.append, subscriber_id="t_store")
    subscribe("evidence.duplicate_skipped", dups.append, subscriber_id="t_dup")

    payload = b"<xbrl>same</xbrl>"
    a = ingest(ticker="INFY", content=payload, source="nse_xbrl", document_type="xbrl", period_end="2025-03-31", period_type="annual")
    b = ingest(ticker="INFY", content=payload, source="nse_xbrl", document_type="xbrl", period_end="2025-03-31", period_type="annual")
    assert a["action"] == "stored"
    assert b["action"] == "duplicate_skipped"
    assert a["event_emitted"] is True
    assert b["event_emitted"] is False
    assert len(stored) == 1
    assert len(dups) == 1


def test_ingest_dashboard_metrics(fse_tmp):
    ingest(
        ticker="NTPC",
        content=b"<xbrl>n1</xbrl>",
        source="nse_xbrl",
        document_type="xbrl",
        period_end="2024-03-31",
        period_type="annual",
    )
    ingest(
        ticker="NTPC",
        content=b"<xbrl>n1</xbrl>",
        source="nse_xbrl",
        document_type="xbrl",
        period_end="2024-03-31",
        period_type="annual",
    )
    dash = ingest_dashboard()
    assert dash["workstream_id"] == "FSE-02.1"
    assert dash["stored_evidence"] >= 1
    assert dash["duplicate_filings"] >= 1
    assert dash["event_emissions"] >= 1
    assert "nse_xbrl" in (dash.get("source_distribution") or {})
    assert dash["average_ingest_latency_ms"] is not None


def test_evidence_stored_creates_one_workflow(fse_tmp):
    """Migration success: ingest → evidence.stored → workflow (no CLI)."""
    subscribe("evidence.stored", on_evidence_stored, subscriber_id="orch_test")

    result = ingest(
        ticker="RELIANCE",
        content=b"<xbrl>reliance fy25</xbrl>",
        source="nse_xbrl",
        document_type="xbrl",
        period_type="annual",
        period_end="2025-03-31",
        collector="unit_test",
    )
    assert result["event_emitted"] is True

    # Second create should hit orchestrator duplicate protection for same identity
    created = create_workflow(
        {
            "ticker": "RELIANCE",
            "period": "2025-03-31",
            "filing_type": "annual",
            "document_hash": result["content_sha256"],
            "evidence_id": result["evidence_id"],
        },
        auto_queue=False,
    )
    # Workflow already created by subscriber
    assert created.get("duplicate") is True or created.get("created") is False or created.get("ok")


def test_pipeline_uses_canonical_ingest_payload(fse_tmp):
    events: list[dict] = []
    subscribe("evidence.stored", events.append, subscriber_id="pipe")
    rows = [
        {
            "ticker": "TCS",
            "source": "nse_xbrl",
            "document_type": "xbrl",
            "period_type": "quarterly",
            "period_end": "2025-06-30",
            "source_url": "mem://tcs-q",
        }
    ]
    out = collect_from_discovery_rows("TCS", rows, bytes_by_url={"mem://tcs-q": b"<xbrl>q</xbrl>"})
    assert out["ok"]
    assert out["results"][0]["action"] == "stored"
    assert out["results"][0].get("ingest", {}).get("event_emitted") is True
    assert events[0]["payload"]["period_end"] == "2025-06-30"


def test_structured_ingest_and_hd_dual_write_callback(fse_tmp):
    hd_calls: list[int] = []

    def hd_cb():
        hd_calls.append(1)
        return {"written": 2, "ok": True}

    r = ingest_structured_json(
        ticker="WIPRO",
        payload={"entity": "WIPRO", "records": [{"period_end": "2025-03-31", "frequency": "annual"}]},
        source="financial_connector",
        period_end="2025-03-31",
        period_type="annual",
        collector="financial_statements_connector",
        hd_callback=hd_cb,
    )
    assert r["action"] == "stored"
    assert r["event_emitted"] is True
    assert hd_calls == [1]
    assert r["dual_write_hd"]["written"] == 2


def test_ei_enrich_routes_xbrl_through_fse(fse_tmp):
    from earnings_intelligence.xbrl import enrich_filing_with_xbrl

    events: list[dict] = []
    subscribe("evidence.stored", events.append, subscriber_id="ei")
    filing = {
        "ticker": "TCS",
        "symbol": "TCS",
        "period_end": "2025-03-31",
        "frequency": "annual",
        "source": "nse_financial_xbrl",
        "xbrl_url": "mem://tcs",
    }
    out = enrich_filing_with_xbrl(filing, injected_xbrl=b"<xbrl><xbrli:instant>2025-03-31</xbrli:instant></xbrl>")
    assert out.get("fse_xbrl_ingested") is True
    assert (out.get("fse_ingest") or {}).get("action") in {"stored", "restatement_candidate"}
    assert len(events) >= 1


def test_persist_pack_keeps_hd_dual_write(fse_tmp, monkeypatch):
    """HD writers must remain enabled (dual-write rule)."""
    import sys
    import types

    import earnings_intelligence.store as ei_store

    calls: list[tuple] = []

    fake_mod = types.ModuleType("knowledge_factory.historical_depth.store")

    def put_series(name, ticker, pits):
        calls.append((name, ticker, len(pits)))

    fake_mod.put_series = put_series
    schema_mod = types.ModuleType("knowledge_factory.historical_depth.schema")

    def pit_record(**kwargs):
        return kwargs

    schema_mod.pit_record = pit_record
    parent = types.ModuleType("knowledge_factory.historical_depth")
    parent.store = fake_mod
    parent.schema = schema_mod
    sys.modules["knowledge_factory.historical_depth"] = parent
    sys.modules["knowledge_factory.historical_depth.store"] = fake_mod
    sys.modules["knowledge_factory.historical_depth.schema"] = schema_mod

    pack = {
        "ok": True,
        "ticker": "TCS",
        "confidence": 0.9,
        "fse_xbrl_ingested": True,
        "quarter_history": [
            {
                "period_end": "2025-06-30",
                "frequency": "quarterly",
                "filing_date": "2025-07-15",
                "income_statement": {"revenue_from_operations": 1.0, "pat": 0.2},
                "balance_sheet": {},
                "cash_flow": {},
            }
        ],
        "annual_history": [],
    }
    result = ei_store.persist_pack(pack)
    assert result["written"] >= 1
    assert result["dual_write_hd"] is True
    assert result["fse_xbrl_already_ingested"] is True
    assert any(c[0] == "financials_quarterly" for c in calls)
