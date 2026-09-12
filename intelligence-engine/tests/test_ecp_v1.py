"""ECP V1 — Evidence Completion Pipeline tests (not an engine)."""

from __future__ import annotations

import pytest

from ecp.gaps import coverage_from_gaps, identify_gaps
from ecp.merge import merge_evidence_objects, reassess_leo_package, withheld_explanation
from ecp.production import is_ecp_enabled, production_dashboard, quality_gates, soft_complete
from ecp.schema import ECP_VERSION
from ecp import store as ecp_store
from ecp.completers import _evidence_object


@pytest.fixture(autouse=True)
def _clean():
    ecp_store.reset_for_tests()
    yield
    ecp_store.reset_for_tests()


def _blocked_leo(ticker="NESTLEIND"):
    return {
        "ticker": ticker,
        "enabled": True,
        "quality_gate": {
            "blocked": True,
            "allow_recommendation": False,
            "must_have_missing": ["market_data", "valuation_metrics", "financial_statements"],
            "missing_evidence": ["market_data", "valuation_metrics", "financial_statements"],
            "present_types": [
                "annual_report",
                "quarterly_results",
                "corporate_announcement",
                "sector_kpis",
            ],
            "intent": "investment_recommendation",
        },
        "evidence_objects": [
            {"evidence_type": "annual_report", "evidence_id": "a1", "source_id": "company_ir"},
            {"evidence_type": "quarterly_results", "evidence_id": "q1", "source_id": "nse"},
            {"evidence_type": "corporate_announcement", "evidence_id": "c1", "source_id": "bse"},
            {"evidence_type": "sector_kpis", "evidence_id": "s1", "source_id": "sif"},
        ],
        "evidence_plan": {
            "intent": "investment_recommendation",
            "required_evidence": [
                "annual_report",
                "quarterly_results",
                "financial_statements",
                "market_data",
                "valuation_metrics",
                "sector_kpis",
                "corporate_announcement",
            ],
            "missing_evidence": ["financial_statements", "market_data", "valuation_metrics"],
        },
        "usage": {"external_api_contributed": True, "documents_used": True},
    }


def test_identify_gaps_for_blocked_investment():
    gaps = identify_gaps(
        ticker="NESTLEIND",
        leo_pkg=_blocked_leo(),
        cid={"ticker": "NESTLEIND", "market_data": {}, "missing_evidence": ["market_data", "valuation"]},
        sif_pkg={
            "sector_id": "fmcg",
            "priority_metrics": ["volume_growth", "roic", "gross_margin"],
            "recommendation_gate": {"blocked": True},
        },
    )
    assert gaps["blocked_before"] is True


def test_master_10y_financials_clear_generic_financial_statement_gap():
    rows = [{"fiscal_year": "FY2025", "source": "capital_iq_workbook"}]
    gaps = identify_gaps(
        ticker="INFY",
        leo_pkg={
            "quality_gate": {
                "must_have_missing": ["financial_statements", "annual_report"],
                "missing_evidence": ["financial_statements", "annual_report"],
            }
        },
        cid={
            "ticker": "INFY",
            "missing_evidence": ["financial_statements", "annual_reports"],
            "financial_statements": {
                "income_statement": {"annual": rows},
                "balance_sheet": {"annual": rows},
                "cash_flow": {"annual": rows},
            },
        },
    )

    assert "financial_statements" not in gaps["leo_missing"]
    assert "financial_statements" not in gaps["cid_missing"]
    assert "financial_statements" not in gaps["must_have_missing"]
    assert "annual_report" in gaps["leo_missing"]
    assert "market_data" in gaps["target_leo_types"]
    assert "valuation_metrics" in gaps["target_leo_types"]
    assert gaps["missing_count"] >= 1
    assert coverage_from_gaps(gaps) < 1.0


def test_merge_and_reassess_unblocks_when_must_haves_filled():
    leo = _blocked_leo()
    added = [
        _evidence_object(
            evidence_type="market_data",
            ticker="NESTLEIND",
            source_id="yahoo",
            title="md",
            facts=[{"field": "current_price", "value": 1443.5, "value_text": "1443.5"}],
        ),
        _evidence_object(
            evidence_type="valuation_metrics",
            ticker="NESTLEIND",
            source_id="yahoo",
            title="val",
            facts=[{"field": "trailing_pe", "value": 70.0, "value_text": "70"}],
        ),
        _evidence_object(
            evidence_type="financial_statements",
            ticker="NESTLEIND",
            source_id="yahoo",
            title="fs",
            facts=[{"field": "roe", "value": 0.8, "value_text": "0.8"}],
        ),
    ]
    merged = merge_evidence_objects(leo["evidence_objects"], added)
    refreshed = reassess_leo_package(leo, merged)
    gate = refreshed["quality_gate"]
    assert gate["blocked"] is False
    assert gate["allow_recommendation"] is True
    assert not gate.get("must_have_missing")


def test_withheld_explanation_lists_missing():
    text = withheld_explanation(
        {
            "coverage_pct": 62,
            "research_grade": "C",
            "data_grade": "C",
            "knowledge_grade": "D",
            "missing_items": ["ROIC", "Market share"],
            "must_have_missing": ["financial_statements"],
        },
        {"leo_missing": ["financial_statements"]},
    )
    assert "Institutional recommendation status" in text
    assert "62%" in text
    assert "financial_statements" not in text
    assert "knowledge gaps" in text.lower()


def test_quality_gates_offline():
    assert is_ecp_enabled() is True
    gates = quality_gates()
    assert gates["passed"] is True
    assert gates["ecp_version"] == ECP_VERSION
    assert gates["checks"]["gate_unblocked_when_must_haves_present"] is True


def test_production_dashboard_shape():
    ecp_store.save_report(
        {
            "ticker": "INFY",
            "completed_automatically": ["market_data"],
            "still_missing": ["peer_valuation"],
            "quality_improvement": 12.0,
            "providers_used": ["yahoo", "dvc"],
        }
    )
    dash = production_dashboard()
    assert dash["programme"] == "ECP"
    assert dash["not_an_engine"] is True
    assert dash["not_a_recommendation_model"] is True
    assert dash["metrics"]["runs"] >= 1


def test_soft_complete_skip_when_not_blocked():
    leo = {
        "ticker": "INFY",
        "quality_gate": {"blocked": False, "allow_recommendation": True, "must_have_missing": []},
        "evidence_objects": [{"evidence_type": "market_data", "evidence_id": "m1"}],
        "evidence_plan": {"required_evidence": ["market_data"], "missing_evidence": []},
        "usage": {"external_api_contributed": True},
    }
    out = soft_complete(
        query="What is INFY?",
        ticker="INFY",
        leo_pkg=leo,
        cid={"ticker": "INFY", "market_data": {"current_price": 1}},
        sif_pkg={"recommendation_gate": {"blocked": False}},
    )
    assert out.get("skipped") is True or out.get("enabled") is True


def test_soft_complete_fills_gaps_with_injected_objects(monkeypatch):
    """Unit-level: patch completer to avoid live HTTP."""
    leo = _blocked_leo()

    def fake_mv(ticker, *, client=None):
        return {
            "ticker": ticker,
            "providers_used": ["yahoo", "dvc"],
            "evidence_objects": [
                _evidence_object(
                    evidence_type="market_data",
                    ticker=ticker,
                    source_id="yahoo",
                    title="md",
                    facts=[{"field": "current_price", "value": 100, "value_text": "100"}],
                ),
                _evidence_object(
                    evidence_type="valuation_metrics",
                    ticker=ticker,
                    source_id="yahoo",
                    title="val",
                    facts=[{"field": "trailing_pe", "value": 20, "value_text": "20"}],
                ),
                _evidence_object(
                    evidence_type="financial_statements",
                    ticker=ticker,
                    source_id="yahoo",
                    title="fs",
                    facts=[{"field": "roe", "value": 0.2, "value_text": "0.2"}],
                ),
            ],
            "yahoo_pack": {"enabled": True, "quote": {"last": 100}, "fundamentals": {"metrics": {"roe": 0.2}}},
            "dvc_pack": {
                "enabled": True,
                "validated_fields": {
                    "last": {"value": 100, "provider": "yahoo", "confidence": 0.9},
                },
            },
            "errors": {},
            "completed_types": ["market_data", "valuation_metrics", "financial_statements"],
        }

    monkeypatch.setattr("ecp.production.complete_market_and_valuation", fake_mv)
    monkeypatch.setattr(
        "ecp.production.complete_from_kip_kf",
        lambda *a, **k: {"providers_used": [], "evidence_objects": [], "completed_types": []},
    )
    monkeypatch.setattr(
        "ecp.merge.apply_cid_enrichment",
        lambda ticker, dossier, **kw: {
            **dossier,
            "ticker": ticker,
            "market_data": {"current_price": 100},
            "missing_evidence": [],
            "coverage_score": 0.95,
            "coverage_grade": "Institutional Grade",
        },
    )

    out = soft_complete(
        query="Should I buy Nestle India?",
        ticker="NESTLEIND",
        leo_pkg=leo,
        cid={"ticker": "NESTLEIND", "market_data": {}, "missing_evidence": ["market_data"]},
        sif_pkg={
            "sector_id": "fmcg",
            "priority_metrics": ["volume_growth"],
            "recommendation_gate": {"blocked": True},
        },
        force=True,
    )
    assert out["enabled"] is True
    assert "market_data" in (out.get("completed_automatically") or [])
    assert out.get("leo_delta", {}).get("quality_gate", {}).get("blocked") is False
    assert ecp_store.get_report("NESTLEIND") is not None
    assert out.get("withheld_explanation") in (None, "") or out.get("gate_blocked_after") is False
