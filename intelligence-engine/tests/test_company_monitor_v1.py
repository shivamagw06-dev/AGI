"""Company Monitoring System V1 — continuous change detection (not an engine)."""

from __future__ import annotations

from company_monitor.detect import detect_changes
from company_monitor.pipeline import monitor_company
from company_monitor.production import (
    health,
    package_for_ask_agi,
    quality_gates,
    research_writer_slice,
    reset_for_tests,
)
from company_monitor.schema import CMS_VERSION
from company_monitor.significance import annotate
from company_monitor import store as cms_store


def setup_function() -> None:
    reset_for_tests()


def test_health():
    h = health()
    assert h["status"] == "ok"
    assert h["version"] == CMS_VERSION
    assert h["never_auto_changes_house_view"] is True


def test_detect_revenue_margin_debt_valuation():
    prev = {
        "ticker": "HDFCBANK",
        "metrics": {
            "revenue_growth": 0.11,
            "operating_margin": 0.20,
            "roe": 0.15,
            "debt": 100.0,
            "cash_flow": 50.0,
            "pe": 16.0,
            "historical_pe": 18.0,
        },
        "leo_evidence_count": 1,
    }
    curr = {
        "ticker": "HDFCBANK",
        "metrics": {
            "revenue_growth": 0.18,
            "operating_margin": 0.223,
            "roe": 0.17,
            "debt": 88.0,
            "cash_flow": 60.0,
            "pe": 20.0,
            "historical_pe": 18.0,
        },
        "leo_evidence_count": 4,
    }
    changes = annotate(detect_changes(curr, prev, ticker="HDFCBANK"))
    types = {c["change_type"] for c in changes}
    assert "revenue_acceleration" in types
    assert "margin_expansion" in types
    assert "debt_reduction" in types
    assert any(c.get("significance") for c in changes)


def test_monitor_never_auto_changes_house_view_and_ask_agi_package():
    cms_store.put_snapshot(
        "HDFCBANK",
        {
            "ticker": "HDFCBANK",
            "captured_at": "2026-01-01T00:00:00+00:00",
            "metrics": {
                "revenue_growth": 0.11,
                "operating_margin": 0.20,
                "roe": 0.15,
                "debt": 100.0,
                "pe": 16.0,
                "historical_pe": 18.0,
            },
            "leo_evidence_count": 1,
            "house_view_label": "Hold",
        },
    )
    report = monitor_company(
        "HDFCBANK",
        force_pipeline=False,
        layers={
            "cid": {
                "ticker": "HDFCBANK",
                "identity": {"company_name": "HDFC Bank", "sector_id": "banks"},
                "financials": {
                    "revenue_growth": 0.18,
                    "operating_margin": 0.223,
                    "roe": 0.17,
                    "debt": 88.0,
                },
                "valuation": {"pe": 20.0, "historical_pe": 18.0},
            },
            "leo_pkg": {"evidence_objects": [{"type": "earnings"}, {"type": "news"}]},
            "house_view": {"stance": "Hold"},
        },
    )
    assert report["ok"] is True
    assert report["auto_house_view_changed"] is False
    assert (report.get("what_changed") or {}).get("change_count", 0) >= 2

    pkg = package_for_ask_agi("Should I invest in HDFC?", ticker="HDFCBANK", run_monitor=False)
    assert pkg.get("ask_agi_hints")
    assert "what_changed" in pkg
    assert pkg.get("never_auto_changes_house_view") is True


def test_research_writer_slice_preloads_what_changed():
    cms_store.put_snapshot(
        "NESTLEIND",
        {
            "ticker": "NESTLEIND",
            "metrics": {"revenue_growth": 0.08, "operating_margin": 0.20, "pe": 60.0, "historical_pe": 55.0},
            "leo_evidence_count": 0,
        },
    )
    monitor_company(
        "NESTLEIND",
        force_pipeline=False,
        layers={
            "cid": {
                "ticker": "NESTLEIND",
                "financials": {"revenue_growth": 0.12, "operating_margin": 0.22},
                "valuation": {"pe": 70.0, "historical_pe": 55.0},
            },
            "leo_pkg": {"evidence_objects": []},
        },
    )
    slice_ = research_writer_slice("Write initiation on Nestle", ticker="NESTLEIND")
    assert slice_.get("enabled") is True
    assert "what_changed" in slice_
    assert "historical_timeline" in slice_
    assert "financial_changes" in slice_
    assert "valuation_changes" in slice_


def test_quality_gates_pass():
    gates = quality_gates()
    assert gates["passed"] is True
