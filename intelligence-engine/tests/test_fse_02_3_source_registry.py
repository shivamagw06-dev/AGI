"""FSE-02.3 — Official Source Registry & multi-source collection tests."""

from __future__ import annotations

import pytest

from financial_statements_engine.collection.event_bus import get_bus, reset_bus_for_tests, subscribe
from financial_statements_engine.collection.source_layer.bse.adapter import BseSourceAdapter
from financial_statements_engine.collection.source_layer.collect import collect_and_ingest
from financial_statements_engine.collection.source_layer.coverage import source_coverage_dashboard, source_registry_health
from financial_statements_engine.collection.source_layer.fallback import collect_with_fallback
from financial_statements_engine.collection.source_layer.investor_relations.adapter import IrSourceAdapter
from financial_statements_engine.collection.source_layer.mca.adapter import McaSourceAdapter
from financial_statements_engine.collection.source_layer.nse.adapter import NseSourceAdapter
from financial_statements_engine.collection.source_layer.provenance import load_provenance
from financial_statements_engine.collection.source_layer.registry import (
    registry_manifest,
    reset_registry_for_tests,
    select_sources,
)
from financial_statements_engine.collection.sources import is_higher_priority, registry_priority_order


@pytest.fixture()
def fse_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("FSE_STORE_ROOT", str(tmp_path / "fse"))
    monkeypatch.setenv("ENABLE_MCA", "true")
    monkeypatch.setenv("ENABLE_NSE", "true")
    monkeypatch.setenv("ENABLE_BSE", "true")
    monkeypatch.setenv("ENABLE_IR", "true")
    monkeypatch.setenv("FSE_02_CANONICAL_INGEST", "true")
    reset_bus_for_tests()
    reset_registry_for_tests()
    return tmp_path / "fse"


def test_registry_priority_order():
    assert registry_priority_order() == ["mca_xbrl", "nse_official", "bse_official", "company_ir"]
    rows = registry_manifest()["sources"]
    assert [r["source_id"] for r in rows] == ["mca_xbrl", "nse_official", "bse_official", "company_ir"]
    assert rows[0]["priority"] == 1


def test_select_sources_respects_enable_flags(monkeypatch, fse_tmp):
    monkeypatch.setenv("ENABLE_MCA", "false")
    monkeypatch.setenv("ENABLE_BSE", "false")
    reset_registry_for_tests()
    adapters = select_sources(healthy_only=False)
    ids = [a.source_id for a in adapters]
    assert "mca_xbrl" not in ids
    assert "bse_official" not in ids
    assert "nse_official" in ids
    assert "company_ir" in ids


def test_mca_discover_and_download(fse_tmp):
    rows = [
        {
            "ticker": "TCS",
            "document_type": "xbrl",
            "period_type": "annual",
            "period_end": "2025-03-31",
            "source_url": "mem://mca/tcs",
            "filing_date": "2025-05-01",
            "company_name": "Tata Consultancy Services",
        }
    ]
    adapter = McaSourceAdapter(injected_rows=rows, injected_bytes={"mem://mca/tcs": b"<xbrl>mca</xbrl>"})
    discovered = adapter.discover("TCS")
    assert len(discovered) == 1
    assert discovered[0]["source_id"] == "mca_xbrl"
    assert discovered[0]["source_priority"] == 1
    meta = adapter.metadata(discovered[0])
    assert meta["reporting_period"] == "2025-03-31"
    dl = adapter.download(discovered[0])
    assert dl["ok"] is True
    assert dl["bytes"] == b"<xbrl>mca</xbrl>"
    assert adapter.health()["status"] in ("ok", "degraded")


def test_fallback_skips_failed_source(fse_tmp):
    mca = McaSourceAdapter(injected_rows=[], injected_bytes={})  # no discoveries
    nse = NseSourceAdapter(
        injected_rows=[
            {
                "ticker": "INFY",
                "document_type": "xbrl",
                "period_type": "annual",
                "period_end": "2025-03-31",
                "source_url": "mem://nse/infy",
            }
        ],
        injected_bytes={"mem://nse/infy": b"<xbrl>nse-win</xbrl>"},
    )
    result = collect_with_fallback("INFY", adapters=[mca, nse], filing_type="annual")
    assert result["ok"] is True
    assert result["source_id"] == "nse_official"
    assert result["fallback_used"] is True
    assert any(a.get("source_id") == "mca_xbrl" and not a.get("ok") for a in result["attempts"])


def test_collect_and_ingest_emits_evidence_stored(fse_tmp):
    events: list[dict] = []
    subscribe("evidence.stored", events.append, subscriber_id="src_ingest")
    mca = McaSourceAdapter(
        injected_rows=[
            {
                "ticker": "TCS",
                "document_type": "xbrl",
                "period_type": "annual",
                "period_end": "2025-03-31",
                "source_url": "mem://mca/tcs2",
                "filing_date": "2025-05-02",
                "company_name": "TCS",
                "original_filename": "tcs-fy25.xbrl",
                "mime_type": "application/xml",
            }
        ],
        injected_bytes={"mem://mca/tcs2": b"<xbrl>canonical</xbrl>"},
    )
    out = collect_and_ingest("TCS", adapters=[mca], filing_type="annual", period_end="2025-03-31")
    assert out["ok"] is True
    assert out["ingested"] is True
    assert out["ingest"]["action"] == "stored"
    assert out["ingest"]["event_emitted"] is True
    assert len(events) == 1
    prov = out["provenance"]
    for field in (
        "company_id",
        "source",
        "filing_type",
        "reporting_period",
        "filing_date",
        "document_hash",
        "download_timestamp",
        "original_filename",
        "mime_type",
        "source_url",
        "source_priority",
    ):
        assert prov.get(field) not in (None, ""), field
    stored = load_provenance(prov["document_hash"])
    assert stored is not None
    assert stored["source"] == "mca_xbrl"


def test_duplicate_detection_records_alternate_sources(fse_tmp):
    payload = b"<xbrl>same-filing</xbrl>"
    mca = McaSourceAdapter(
        injected_rows=[
            {
                "ticker": "RELIANCE",
                "document_type": "xbrl",
                "period_type": "annual",
                "period_end": "2025-03-31",
                "source_url": "mem://mca/rel",
                "filing_date": "2025-05-10",
            }
        ],
        injected_bytes={"mem://mca/rel": payload},
    )
    nse = NseSourceAdapter(
        injected_rows=[
            {
                "ticker": "RELIANCE",
                "document_type": "xbrl",
                "period_type": "annual",
                "period_end": "2025-03-31",
                "source_url": "mem://nse/rel",
                "filing_date": "2025-05-11",
            }
        ],
        injected_bytes={"mem://nse/rel": payload},
    )
    a = collect_and_ingest("RELIANCE", adapters=[mca])
    assert a["ingest"]["action"] == "stored"
    b = collect_and_ingest("RELIANCE", adapters=[nse])
    assert b["ingest"]["action"] == "duplicate_skipped"
    digest = a["ingest"]["content_sha256"]
    prov = load_provenance(digest)
    assert prov is not None
    alts = prov.get("alternate_sources") or []
    assert any(x.get("source") == "nse_official" for x in alts)


def test_retry_on_download_failure_then_success(fse_tmp, monkeypatch):
    monkeypatch.setenv("MAX_DOWNLOAD_RETRIES", "2")
    calls = {"n": 0}

    class Flaky(NseSourceAdapter):
        def download(self, discovery_row, **kwargs):
            calls["n"] += 1
            if calls["n"] < 2:
                return {"ok": False, "bytes": None, "error": "503", "http_status": 503}
            return super().download(discovery_row, **kwargs)

    adapter = Flaky(
        injected_rows=[
            {
                "ticker": "HDFCBANK",
                "document_type": "xbrl",
                "period_end": "2025-03-31",
                "period_type": "annual",
                "source_url": "mem://nse/hdfc",
            }
        ],
        injected_bytes={"mem://nse/hdfc": b"<xbrl>ok</xbrl>"},
    )
    result = collect_with_fallback("HDFCBANK", adapters=[adapter])
    assert result["ok"] is True
    assert calls["n"] == 2


def test_existing_hierarchy_still_holds():
    xbrl = {"source": "nse_xbrl", "document_type": "xbrl"}
    ir = {"source": "company_ir", "document_type": "pdf"}
    assert is_higher_priority(xbrl, ir) is True


def test_source_coverage_dashboard(fse_tmp):
    mca = McaSourceAdapter(
        injected_rows=[
            {
                "ticker": "TCS",
                "document_type": "xbrl",
                "period_end": "2024-03-31",
                "period_type": "annual",
                "source_url": "mem://mca/tcs3",
            }
        ],
        injected_bytes={"mem://mca/tcs3": b"<xbrl>dash</xbrl>"},
    )
    collect_and_ingest("TCS", adapters=[mca])
    dash = source_coverage_dashboard()
    assert dash["workstream_id"] == "FSE-02.3"
    assert dash["parses_financials"] is False
    assert dash["writes_warehouse"] is False
    assert any(h["source_id"] == "mca_xbrl" for h in dash["source_health"])
    health = source_registry_health()
    assert health["changes_parser"] is False
    assert health["changes_orchestrator"] is False


def test_bse_and_ir_adapters_normalize(fse_tmp):
    bse = BseSourceAdapter(
        injected_rows=[{"ticker": "TCS", "period_end": "2025-03-31", "source_url": "mem://bse", "document_type": "pdf"}]
    )
    ir = IrSourceAdapter(
        injected_rows=[{"ticker": "TCS", "period_end": "2025-03-31", "source_url": "mem://ir", "document_type": "pdf"}]
    )
    assert bse.discover("TCS")[0]["source_priority"] == 3
    assert ir.discover("TCS")[0]["source_priority"] == 4
