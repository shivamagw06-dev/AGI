"""FSE-FDO Phase 1 — Financial Data Operations tests."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from financial_statements_engine.collection.event_bus import reset_bus_for_tests
from financial_statements_engine.fdo.alerts import generate_alerts
from financial_statements_engine.fdo.calendar import (
    fy_annual_period_end,
    fy_for_period_end,
    period_status,
    quarter_period_end,
)
from financial_statements_engine.fdo.coverage import company_completeness, company_coverage, universe_coverage
from financial_statements_engine.fdo.metrics import live_ingestion_metrics, source_health_metrics
from financial_statements_engine.fdo.production import dashboard, health
from financial_statements_engine.fdo.scheduler import gap_priority_score, plan_gap_schedule
from financial_statements_engine.fdo.schema import WORKSTREAM_ID
from financial_statements_engine.raw_evidence import store_raw
from financial_statements_engine.store import ensure_dirs


@pytest.fixture()
def fse_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("FSE_STORE_ROOT", str(tmp_path / "fse"))
    reset_bus_for_tests()
    return tmp_path / "fse"


def _seed_raw(ticker: str, period_end: str, period_type: str, content: bytes) -> None:
    store_raw(
        ticker=ticker,
        data=content,
        source="nse_xbrl",
        document_type="xbrl",
        period_type=period_type,
        period_end=period_end,
    )


def test_fdo_health(fse_tmp):
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["redesigns_engines"] is False
    assert h["bypasses_fse"] is False


def test_calendar_fy_and_quarters():
    assert fy_for_period_end(date(2025, 3, 31)) == "FY25"
    assert fy_for_period_end(date(2025, 6, 30)) == "FY26"
    assert fy_annual_period_end("FY25") == date(2025, 3, 31)
    assert quarter_period_end("FY26", 1) == date(2025, 6, 30)
    assert quarter_period_end("FY26", 4) == date(2026, 3, 31)
    assert period_status(period_end=date(2099, 3, 31), have=False) == "not_released"
    assert period_status(period_end=date(2020, 3, 31), have=False, as_of=date(2026, 1, 1), period_type="annual") == "missing"
    assert period_status(period_end=date(2020, 3, 31), have=True) == "present"


def test_company_coverage_and_completeness(fse_tmp):
    _seed_raw("TCS", "2025-03-31", "annual", b"<xbrl>a</xbrl>")
    _seed_raw("TCS", "2025-06-30", "quarterly", b"<xbrl>q1</xbrl>")
    # Mid-Q3 FY26: Q2 overdue/missing, Q3 in expected window, Q4 not released.
    as_of = date(2025, 11, 15)
    cov = company_coverage("TCS", as_of=as_of)
    assert cov["latest_annual"] == "2025-03-31"
    assert cov["latest_quarterly"] == "2025-06-30"
    assert cov["years_of_history"] >= 1
    assert cov["coverage_pct"] > 0
    assert cov["raw_evidence_n"] == 2
    assert cov["expected_next_filing"]
    assert "2025-09-30" in (cov["missing_periods"].get("quarterly") or [])

    comp = company_completeness("TCS", as_of=as_of)
    by_label = {c["label"]: c for c in comp["checklist"]}
    assert by_label["Annual FY25"]["status"] == "present"
    assert by_label["Q1 FY26"]["status"] == "present"
    assert by_label["Q2 FY26"]["status"] == "missing"
    assert by_label["Q3 FY26"]["status"] == "expected"
    assert by_label["Q4 FY26"]["status"] == "not_released"
    assert 0.0 < comp["overall_completeness_pct"] < 100.0


def test_gap_scheduler_orders_low_coverage_first(fse_tmp):
    # INFY has data; RELIANCE empty → RELIANCE higher priority
    _seed_raw("INFY", "2025-03-31", "annual", b"<xbrl>infy</xbrl>")
    _seed_raw("INFY", "2025-06-30", "quarterly", b"<xbrl>infyq</xbrl>")
    a = gap_priority_score("RELIANCE")
    b = gap_priority_score("INFY")
    assert a["score"] > b["score"]
    plan = plan_gap_schedule(["RELIANCE", "INFY", "TCS"], limit=10)
    assert plan["queue"][0]["ticker"] in {"RELIANCE", "TCS"}
    assert plan["policy"] == "largest_evidence_gaps_first"


def test_metrics_and_dashboard_aggregation(fse_tmp):
    # seed ingest metrics
    root = ensure_dirs()
    metrics = root / "collection" / "ingest_metrics.jsonl"
    metrics.parent.mkdir(parents=True, exist_ok=True)
    from financial_statements_engine.util import now_iso

    metrics.write_text(
        json.dumps({"ts": now_iso(), "ticker": "TCS", "action": "stored", "latency_ms": 12.0, "source": "nse_xbrl"})
        + "\n"
        + json.dumps({"ts": now_iso(), "ticker": "TCS", "action": "duplicate_skipped", "latency_ms": 3.0})
        + "\n"
        + json.dumps({"ts": now_iso(), "ticker": "INFY", "action": "download_failed", "latency_ms": 5.0})
        + "\n",
        encoding="utf-8",
    )
    src = root / "collection" / "source_metrics.jsonl"
    src.write_text(
        json.dumps(
            {
                "ts": now_iso(),
                "source_id": "nse_official",
                "ok": True,
                "phase": "download",
                "latency_ms": 40.0,
                "ticker": "TCS",
            }
        )
        + "\n"
        + json.dumps(
            {
                "ts": now_iso(),
                "source_id": "mca_xbrl",
                "ok": False,
                "phase": "discover",
                "error": "no_discoveries",
                "fallback": False,
                "ticker": "TCS",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _seed_raw("TCS", "2025-03-31", "annual", b"<xbrl>z</xbrl>")

    ing = live_ingestion_metrics()
    assert ing["collected_today"] >= 1
    assert ing["duplicate_filings"] >= 1
    assert ing["failed_downloads"] >= 1

    src_h = source_health_metrics()
    assert src_h["n"] >= 1
    assert any(s["source_id"] == "nse_official" for s in src_h["sources"])

    dash = dashboard("gold")
    assert dash["workstream_id"] == WORKSTREAM_ID
    assert "coverage_pct" in dash
    assert "completeness_pct" in dash
    assert "queue_depth" in dash
    assert "raw_evidence_growth" in dash
    assert "source_health" in dash
    assert "alerts" in dash
    assert dash["raw_evidence_growth"]["files"] >= 1


def test_alert_generation(fse_tmp):
    # empty universe → no filings today + low coverage warnings likely
    out = generate_alerts(coverage=universe_coverage(["ZZZZ"]))
    codes = {a["code"] for a in out["alerts"]}
    assert "NO_NEW_FILINGS" in codes or "COVERAGE_LOW" in codes or "OPS_HEALTHY" in codes


def test_universe_coverage_rows(fse_tmp):
    _seed_raw("TCS", "2025-03-31", "annual", b"<xbrl>t</xbrl>")
    uni = universe_coverage(["TCS", "INFY"])
    assert uni["n"] == 2
    assert uni["average_coverage_pct"] >= 0
    assert any(r["ticker"] == "TCS" for r in uni["rows"])
