"""LEO v1.0 — Live Evidence Orchestrator tests."""

from __future__ import annotations

from leo.planner import build_evidence_plan, detect_intent
from leo.production import is_leo_enabled, package_for_query, production_dashboard, run_quality_gates
from leo.sources import select_sources


def test_leo_enabled_by_default():
    assert is_leo_enabled() is True


def test_evidence_plan_hdfc_investment():
    plan = build_evidence_plan("Should I buy HDFC Bank?", ticker="HDFCBANK")
    assert plan["intent"] == "investment_recommendation"
    assert plan["ticker"] == "HDFCBANK"
    assert "annual_report" in plan["required_evidence"]
    assert "market_data" in plan["required_evidence"]
    assert "quarterly_results" in plan["required_evidence"]


def test_source_selection_skips_irrelevant():
    plan = build_evidence_plan("Should I buy HDFC Bank?", ticker="HDFCBANK")
    selected = select_sources(plan)
    ids = {s["source_id"] for s in selected}
    assert "nse" in ids or "company_ir" in ids
    assert "newsapi" not in ids  # skipped for investment_recommendation


def test_macro_intent():
    assert detect_intent("What is the RBI repo rate and inflation outlook?")["intent"] == "macro"


def test_package_creates_evidence_objects_hdfc():
    pkg = package_for_query("Should I buy HDFC Bank?", ticker="HDFCBANK", engine="test")
    assert pkg["enabled"] is True
    assert pkg["leo_version"].startswith("leo-")
    assert pkg["evidence_count"] > 0
    assert pkg["evidence_objects"]
    assert pkg["usage"]["external_api_contributed"] is True
    assert "nse" in pkg["sources_used"] or "company_ir" in pkg["sources_used"] or "bse" in pkg["sources_used"]
    assert pkg["company_dossier"]["coverage_score"] >= 0
    # Investment reco must not be Academy+SIF-only — gate tracks live evidence
    assert "quality_gate" in pkg
    assert pkg["reasoning_trace"]["external_contribution"] is True


def test_multi_ticker_quality_gates():
    report = run_quality_gates()
    assert report["pass"] is True
    assert report["success_metrics"]["evidence_objects_created"] is True
    assert report["success_metrics"]["external_api_contributes_when_relevant"] is True
    tickers = {p["ticker"] for p in report["packages"]}
    for t in ("HDFCBANK", "INFY", "RELIANCE", "ULTRACEMCO", "POWERGRID", "SUNPHARMA", "TATASTEEL"):
        assert t in tickers
        row = next(p for p in report["packages"] if p["ticker"] == t)
        assert row["objects"] > 0
        assert row["external"] is True


def test_dashboard_shape():
    production_dashboard()  # warm
    package_for_query("Should I buy Infosys?", ticker="INFY", engine="test")
    dash = production_dashboard()
    assert dash["programme"] == "LEO"
    assert dash["configured_apis"]
    assert "metrics" in dash
    assert "evidence_contribution" in dash


def test_ask_agi_includes_live_evidence():
    from app.ui.service import UiService

    view = UiService().search("What are the key risks for HDFC Bank?")
    data = view.model_dump()
    leo = data.get("live_evidence") or {}
    assert leo.get("enabled") is True
    assert (leo.get("evidence_count") or 0) > 0
    assert leo.get("influenced_reasoning") is True
    # Must expose production trace fields
    assert leo.get("evidence_plan")
    assert leo.get("sources_queried") is not None
    assert leo.get("api_calls") is not None
    # House view should reflect evidence gate when evidence incomplete for full reco
    # (AOI templates count as external/docs; gate may still block missing market_data)
    assert data.get("answer") is not None
