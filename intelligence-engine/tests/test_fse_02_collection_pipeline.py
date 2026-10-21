"""FSE-02 — Data Sources & Collection Pipeline contract tests."""

from __future__ import annotations

import pytest

from financial_statements_engine.collection.event_bus import get_bus, reset_bus_for_tests, subscribe
from financial_statements_engine.collection.pipeline import collect_from_discovery_rows, run_job
from financial_statements_engine.collection.production import health
from financial_statements_engine.collection.retry import classify_error, is_retryable_http, retry_plan
from financial_statements_engine.collection.sources import is_higher_priority, logical_key
from financial_statements_engine.collection.jobs import make_job
from financial_statements_engine.collection.writer import write_evidence
from financial_statements_engine.store import store_root


@pytest.fixture()
def fse_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("FSE_STORE_ROOT", str(tmp_path / "fse"))
    reset_bus_for_tests()
    return tmp_path / "fse"


def test_collection_health_fse02(fse_tmp):
    h = health()
    assert h["status"] == "ok"
    assert h["workstream_id"] == "FSE-02"
    assert h["parses_financials"] is False
    assert h["writes_warehouse"] is False
    assert h["issues_recommendations"] is False
    assert "recommendation" not in h


def test_source_hierarchy_xbrl_beats_ir():
    xbrl = {"source": "nse_xbrl", "document_type": "xbrl"}
    ir = {"source": "company_ir", "document_type": "pdf"}
    assert is_higher_priority(xbrl, ir) is True
    assert is_higher_priority(ir, xbrl) is False


def test_retry_classifies_503_and_404():
    assert is_retryable_http(503) is True
    assert is_retryable_http(404) is False
    assert classify_error(http_status=503) == "transient"
    assert classify_error(http_status=404) == "permanent"
    plan = retry_plan(0, http_status=503)
    assert plan["retry"] is True
    plan404 = retry_plan(0, http_status=404)
    assert plan404["retry"] is False


def test_idempotent_duplicate_and_event(fse_tmp):
    events: list[dict] = []
    subscribe("evidence.duplicate_skipped", events.append, subscriber_id="test_dup")
    subscribe("evidence.stored", events.append, subscriber_id="test_store")

    rows = [
        {
            "ticker": "TCS",
            "source": "nse_xbrl",
            "document_type": "xbrl",
            "period_type": "quarterly",
            "period_end": "2025-03-31",
            "source_url": "mem://tcs-q4",
        }
    ]
    payload = b"<xbrl>revenue 1</xbrl>"
    a = collect_from_discovery_rows("TCS", rows, mode="live", bytes_by_url={"mem://tcs-q4": payload})
    b = collect_from_discovery_rows("TCS", rows, mode="live", bytes_by_url={"mem://tcs-q4": payload})
    assert a["ok"] and b["ok"]
    assert a["results"][0]["action"] == "stored"
    assert b["results"][0]["action"] == "duplicate_skipped"
    types = {e["event_type"] for e in get_bus().tail(50)}
    assert "evidence.stored" in types
    assert "evidence.duplicate_skipped" in types


def test_restatement_candidate_same_period_new_hash(fse_tmp):
    events: list[dict] = []
    subscribe("evidence.restatement_candidate", events.append, subscriber_id="test_restate")

    r1 = write_evidence(
        ticker="TCS",
        data=b"<xbrl>v1</xbrl>",
        source="nse_xbrl",
        document_type="xbrl",
        period_type="annual",
        period_end="2025-03-31",
    )
    assert r1["action"] == "stored"
    r2 = write_evidence(
        ticker="TCS",
        data=b"<xbrl>v2-restated</xbrl>",
        source="nse_xbrl",
        document_type="xbrl",
        period_type="annual",
        period_end="2025-03-31",
    )
    assert r2["action"] == "restatement_candidate"
    assert r2["prior_evidence_id"] == r1["evidence_id"]
    assert r2["logical_key"] == logical_key(
        ticker="TCS", period_type="annual", period_end="2025-03-31", document_type="xbrl"
    )

    # Also via job pipeline to emit bus event
    job = make_job(
        ticker="TCS",
        source="nse_xbrl",
        document_type="xbrl",
        period_type="annual",
        period_end="2025-03-31",
        url="mem://restate",
        job_id="job-restate-1",
    )
    run_job(job, bytes_provider=lambda j: {"ok": True, "bytes": b"<xbrl>v3</xbrl>", "http_status": 200, "error": None})
    assert any(e.get("event_type") == "evidence.restatement_candidate" for e in get_bus().tail(20))


def test_pipeline_does_not_publish_warehouse(fse_tmp):
    """Collectors stop at raw store — no published/ warehouse writes."""
    rows = [
        {
            "ticker": "INFY",
            "source": "nse_xbrl",
            "document_type": "xbrl",
            "period_type": "quarterly",
            "period_end": "2025-06-30",
            "source_url": "mem://infy",
        }
    ]
    collect_from_discovery_rows("INFY", rows, bytes_by_url={"mem://infy": b"<xbrl>ok</xbrl>"})
    published = store_root() / "published"
    assert not published.exists() or not any(published.rglob("*.json"))


def test_event_bus_delivers_to_subscriber(fse_tmp):
    seen: list[dict] = []
    subscribe("evidence.stored", seen.append, subscriber_id="parser_stub")
    # subscriber must not break collector if it raises
    subscribe("evidence.stored", lambda e: (_ for _ in ()).throw(RuntimeError("parser down")), subscriber_id="bad")

    rows = [
        {
            "ticker": "NTPC",
            "source": "nse_integrated_filing",
            "document_type": "html",
            "period_type": "annual",
            "period_end": "2024-03-31",
            "source_url": "mem://ntpc",
        }
    ]
    result = collect_from_discovery_rows("NTPC", rows, bytes_by_url={"mem://ntpc": b"<html>results</html>"})
    assert result["ok"] is True
    assert len(seen) >= 1
    assert seen[0]["event_type"] == "evidence.stored"
