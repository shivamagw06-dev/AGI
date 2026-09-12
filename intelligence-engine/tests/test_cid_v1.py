"""CID v1.0 — Company Intelligence Dossier tests."""

from __future__ import annotations

from cid.production import (
    coverage,
    get_dossier,
    get_or_build,
    is_cid_enabled,
    production_dashboard,
    quality_gates,
    timeline,
)
from cid.schema import CID_VERSION
from leo.production import package_for_query as leo_package


def test_cid_enabled():
    assert is_cid_enabled() is True


def test_leo_updates_cid_hdfc():
    leo = leo_package("Should I buy HDFC Bank?", ticker="HDFCBANK", engine="cid_test")
    assert leo["evidence_count"] > 0
    d = get_dossier("HDFCBANK")
    assert d["ticker"] == "HDFCBANK"
    assert d["cid_version"] == CID_VERSION
    assert len(d.get("evidence_timeline") or []) > 0
    assert (d.get("documents") or {}).get("annual_reports")
    assert (d.get("documents") or {}).get("quarterly_results")
    assert d.get("announcements")
    assert (d.get("sector_framework") or {}).get("sector_id") == "banks"
    assert (d.get("sector_kpis") or {}).get("priority_metrics")
    assert d.get("coverage_score") is not None
    assert d.get("coverage_grade") in {
        "Institutional Grade",
        "Research Grade",
        "Partial",
        "Insufficient",
    }


def test_coverage_and_timeline_apis():
    leo_package("Should I buy Infosys?", ticker="INFY", engine="cid_test")
    cov = coverage("INFY")
    assert cov["ticker"] == "INFY"
    assert "categories" in cov
    tl = timeline("INFY", limit=20)
    assert tl["count"] > 0


def test_ask_agi_uses_dossier():
    from app.ui.service import UiService

    view = UiService().search("What are the key risks for HDFC Bank?")
    data = view.model_dump()
    dossier = data.get("company_dossier") or {}
    assert dossier.get("ticker") == "HDFCBANK"
    assert dossier.get("cid_version") == CID_VERSION
    assert (dossier.get("evidence_timeline") or dossier.get("coverage_score") is not None)
    # Must not rebuild solely from empty context — dossier present with SIF
    assert (dossier.get("sector_framework") or {}).get("sector_id") == "banks"
    why = " ".join(str(x) for x in ((data.get("answer") or {}).get("why") or data.get("why") or []))
    assert "CID" in why or dossier.get("reasoning_hint")


def test_quality_gates_tracked_universe():
    report = quality_gates()
    assert report["passed"] is True
    tickers = {p["ticker"] for p in report["packages"]}
    for t in ("HDFCBANK", "INFY", "RELIANCE", "ULTRACEMCO", "ASIANPAINT", "TATASTEEL", "SUNPHARMA", "POWERGRID"):
        assert t in tickers
        row = next(p for p in report["packages"] if p["ticker"] == t)
        assert row["sif_attached"] is True
        assert row["timeline_events"] > 0
        assert row["academy_linked"] is True


def test_dashboard_lists_dossiers():
    get_or_build("RELIANCE", query="Should I buy Reliance?")
    dash = production_dashboard()
    assert dash["programme"] == "CID"
    assert dash["dossier_count"] >= 1
    assert any(r["ticker"] == "RELIANCE" for r in dash["dossiers"])


def test_timeline_never_shrinks_on_reingest():
    leo_package("Should I buy Tata Steel?", ticker="TATASTEEL", engine="cid_test")
    d1 = get_dossier("TATASTEEL")
    n1 = len(d1.get("evidence_timeline") or [])
    leo_package("Should I buy Tata Steel?", ticker="TATASTEEL", engine="cid_test")
    d2 = get_dossier("TATASTEEL")
    n2 = len(d2.get("evidence_timeline") or [])
    assert n2 >= n1
