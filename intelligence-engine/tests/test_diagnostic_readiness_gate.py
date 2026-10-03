"""Diagnostic readiness gate — coverage vs analytical confidence + freshness."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from decision_engine.production import package_for_ask_agi
from decision_engine.readiness_gate import (
    compute_analytical_confidence,
    compute_freshness_penalties,
    evaluate_readiness_gate,
)


def test_splits_institutional_readiness_from_analytical_confidence():
    gate = evaluate_readiness_gate(
        layers={
            "macro": {"score": 72, "status": "partial"},
            "industry": {"score": 70, "status": "complete"},
            "company_quality": {"score": 84, "status": "complete"},
            "financial_quality": {
                "score": 80,
                "company_quality_score": 84,
                "evidence_quality_score": 30,
                "status": "partial",
            },
            "management": {"score": 78, "status": "partial"},
            "valuation": {"score": 58, "status": "partial"},
            "market_expectations": {"score": 55, "status": "partial"},
            "technical": {"score": 40, "status": "incomplete"},
            "risk": {"score": 72, "status": "complete"},
        },
        company_analysis={
            "identity": {
                "company_name": "HDFC Bank",
                "business_model": "Diversified private-sector bank",
                "peers": ["ICICIBANK"],
            },
            "business_quality": {
                "business_quality_score": 84,
                "strengths": ["Strong retail franchise", "Large deposit base"],
                "weaknesses": ["Margin pressure"],
            },
            "financial_intelligence": {"coverage_pct": 30, "what_improved": ["asset quality"]},
            "valuation_intelligence": {"coverage_pct": 35, "narrative": "Peer band incomplete"},
        },
        name="HDFC Bank",
    )
    assert "institutional_readiness_pct" in gate
    assert "recommendation_readiness_pct" in gate
    assert gate["analytical_confidence"]["display"]
    # Available evidence can still look consistent even when coverage is thin
    assert "conditional" in gate["analytical_confidence"]["display"].lower() or gate[
        "analytical_confidence"
    ]["conditional"]
    assert gate["company_quality_10"] >= 7.0
    assert gate["recommendation_readiness_pct"] < 80
    assert gate["investment_thesis_status"] == "INCONCLUSIVE"
    assert gate["decision_line"]
    assert gate["diagnostic_cards"]
    failed = [c for c in gate["diagnostic_cards"] if not c["present"]]
    assert failed
    assert any(c.get("required") for c in failed)
    assert any(c.get("expected_impact") for c in failed)


def test_stale_shareholding_reduces_recommendation_readiness():
    old = (datetime.now(timezone.utc) - timedelta(days=200)).date().isoformat()
    fresh = compute_freshness_penalties(
        company_analysis={
            "financial_intelligence": {"as_of": datetime.now(timezone.utc).isoformat(), "coverage_pct": 90},
            "valuation_intelligence": {"as_of": datetime.now(timezone.utc).isoformat(), "coverage_pct": 90},
        },
        cid={"shareholding": {"promoter": 26, "fii": 40, "as_of": old, "records": [{"period_end": old}]}},
        live_evidence={"quote": {"as_of": datetime.now(timezone.utc).isoformat()}},
    )
    assert any(s["dimension"] == "ownership" and s["status"] == "stale" for s in fresh["stale_items"])
    assert fresh["total_penalty_pct"] > 0

    gate = evaluate_readiness_gate(
        layers={
            "macro": {"score": 80, "status": "complete"},
            "industry": {"score": 80, "status": "complete"},
            "company_quality": {"score": 85, "status": "complete"},
            "financial_quality": {"score": 85, "company_quality_score": 85, "status": "complete"},
            "management": {"score": 80, "status": "complete"},
            "valuation": {"score": 78, "status": "complete"},
            "market_expectations": {"score": 70, "status": "complete"},
            "technical": {"score": 70, "status": "complete"},
            "risk": {"score": 75, "status": "complete"},
        },
        company_analysis={
            "identity": {"company_name": "TCS", "peers": ["INFY"]},
            "business_quality": {"business_quality_score": 85},
            "financial_intelligence": {
                "coverage_pct": 95,
                "as_of": datetime.now(timezone.utc).isoformat(),
                "what_improved": ["growth", "margins"],
            },
            "valuation_intelligence": {
                "coverage_pct": 92,
                "peer_pe": 28,
                "as_of": datetime.now(timezone.utc).isoformat(),
            },
            "recommendation_readiness": {
                "scores": {
                    "financial_intelligence": 95,
                    "valuation": 92,
                    "sector_intelligence": 90,
                    "research": 90,
                    "evidence_confidence": 90,
                }
            },
        },
        cid={"shareholding": {"promoter": 72, "fii": 12, "as_of": old, "records": [{"period_end": old}]}},
        live_evidence={
            "quote": {"as_of": datetime.now(timezone.utc).isoformat()},
            "evidence_objects": [{"kind": "quarterly_results"}, {"kind": "annual_report"}],
        },
        evidence_completion={"quality_panel": {"coverage_pct": 92}},
        name="TCS",
    )
    # Freshness penalty must pull recommendation readiness below raw institutional readiness
    assert gate["recommendation_readiness_pct"] <= gate["institutional_readiness_pct"]
    ownership_card = next(c for c in gate["diagnostic_cards"] if c["key"] == "ownership")
    assert ownership_card["present"] is False or ownership_card["status"] in {"outdated", "missing", "partial"}
    assert ownership_card.get("required")


def test_package_exposes_diagnostic_metrics():
    out = package_for_ask_agi(
        "Should I buy HDFC Bank?",
        ticker="HDFCBANK",
        company_analysis={
            "ticker": "HDFCBANK",
            "identity": {"company_name": "HDFC Bank", "peers": ["ICICIBANK"]},
            "business_quality": {"business_quality_score": 82, "strengths": ["Franchise"]},
            "financial_intelligence": {"coverage_pct": 28, "narrative": "Thin pack"},
        },
        gate_blocked=True,
        force=True,
    )
    gate = out["institutional_readiness_gate"]
    assert gate["version"].startswith("readiness-gate-v1.1")
    assert out["summary"]["recommendation_readiness_pct"] is not None
    assert out["summary"]["institutional_readiness_pct"] is not None
    assert out["summary"]["analytical_confidence"]
    assert out["summary"]["decision_line"]
    assert gate["never_recommend_on_stale_data"] is True


def test_analytical_confidence_high_conditional_when_consistent_but_thin():
    board = {"dimensions": {"financials": 30, "valuation": 35, "macro": 70}, "overall_coverage_pct": 40}
    layers = {
        "company_quality": {"score": 82, "status": "complete"},
        "financial_quality": {"score": 80, "status": "partial"},
        "management": {"score": 78, "status": "partial"},
        "valuation": {"score": 76, "status": "partial"},
        "risk": {"score": 74, "status": "complete"},
        "macro": {"score": 72, "status": "partial"},
        "industry": {"score": 70, "status": "complete"},
    }
    cards = [
        {"key": "business", "present": True, "label": "Business"},
        {"key": "financials", "present": False, "label": "Financials"},
        {"key": "macro", "present": True, "label": "Macro"},
    ]
    ac = compute_analytical_confidence(
        layers=layers,
        board=board,
        freshness={"stale_items": []},
        diagnostic_cards=cards,
    )
    assert ac["conditional"] is True
    assert "conditional" in ac["display"].lower() or ac["label"] in {"High", "Moderate"}
