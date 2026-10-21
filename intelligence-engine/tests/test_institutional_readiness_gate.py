"""Institutional Readiness Gate — evidence vs company quality separation."""

from __future__ import annotations

from decision_engine.production import package_for_ask_agi
from decision_engine.readiness_gate import evaluate_readiness_gate


def test_gate_explains_missing_evidence_and_is_not_negative_view():
    gate = evaluate_readiness_gate(
        layers={
            "macro": {"score": 70, "status": "partial"},
            "industry": {"score": 65, "status": "complete"},
            "company_quality": {"score": 80, "status": "complete"},
            "financial_quality": {
                "score": 78,
                "company_quality_score": 84,
                "evidence_quality_score": 40,
                "status": "partial",
            },
            "management": {"score": 72, "status": "partial"},
            "valuation": {"score": 60, "status": "partial"},
            "market_expectations": {"score": 55, "status": "partial"},
            "technical": {"score": 40, "status": "incomplete"},
            "risk": {"score": 70, "status": "complete"},
        },
        company_analysis={
            "identity": {
                "company_name": "HDFC Bank",
                "business_model": "Diversified private-sector bank",
                "peers": ["ICICIBANK"],
            },
            "business_quality": {
                "business_quality_score": 80,
                "strengths": ["Strong retail franchise", "Large deposit base"],
                "weaknesses": ["Margin pressure"],
            },
            "financial_intelligence": {"coverage_pct": 35, "what_improved": ["asset quality"]},
            "valuation_intelligence": {"coverage_pct": 40, "narrative": "Peer band incomplete"},
            "recommendation_readiness": {
                "scores": {
                    "financial_intelligence": 35,
                    "valuation": 40,
                    "sector_intelligence": 70,
                    "research": 50,
                    "evidence_confidence": 45,
                },
                "overall": 48,
            },
        },
        cid={},
        live_evidence={},
        name="HDFC Bank",
    )
    assert gate["status"] == "FAILED"
    assert gate["investment_thesis_status"] == "INCONCLUSIVE"
    assert gate["not_a_negative_view"] is True
    assert gate["company_quality_10"] >= 6.0  # franchise not crushed by thin data
    assert gate["evidence_confidence_pct"] < 80
    assert gate["additional_evidence_required"]
    assert any(not c["present"] for c in gate["checklist"])
    assert "negative view" in gate["reason"].lower() or gate["not_a_negative_view"]


def test_financial_layer_separates_company_and_evidence_quality():
    out = package_for_ask_agi(
        "Should I buy HDFC Bank?",
        ticker="HDFCBANK",
        company_analysis={
            "ticker": "HDFCBANK",
            "identity": {
                "company_name": "HDFC Bank",
                "business_model": "Diversified private bank",
                "peers": ["ICICIBANK", "KOTAKBANK"],
            },
            "business_quality": {
                "business_quality_score": 82,
                "strengths": ["Retail franchise", "Deposit franchise"],
                "weaknesses": ["Near-term margin pressure"],
                "grade": "B+",
            },
            "financial_intelligence": {
                "coverage_pct": 30,
                "narrative": "Asset quality stable; statement pack incomplete.",
                "what_improved": ["asset_quality"],
                "what_deteriorated": ["nim"],
            },
            "valuation_intelligence": {
                "coverage_pct": 25,
                "current_pe": 18,
                "narrative": "Peer valuation incomplete.",
            },
            "risks": ["Execution", "Margin pressure"],
        },
        gate_blocked=True,
        force=True,
    )
    assert out["active"] is True
    gate = out["institutional_readiness_gate"]
    assert gate
    assert gate["never_conflate_data_with_quality"] is True
    fin = next(l for l in out["layers"] if l["id"] == "financial_quality")
    assert fin.get("company_quality_score") is not None
    assert fin.get("evidence_quality_score") is not None
    # Thin coverage must not fully define company quality
    assert fin["company_quality_score"] > fin["evidence_quality_score"]
    assert out["summary"]["investment_thesis_status"] == "INCONCLUSIVE"
    assert out["summary"]["not_a_negative_view"] is True
    assert "inconclusive" in str(out["decision"].get("reasoning") or "").lower()
    cq = next(l for l in out["layers"] if l["id"] == "company_quality")
    assert cq.get("strengths")


def test_high_coverage_allows_formed_thesis():
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    out = package_for_ask_agi(
        "Should I buy TCS?",
        ticker="TCS",
        company_analysis={
            "ticker": "TCS",
            "identity": {
                "company_name": "TCS",
                "business_model": "IT services",
                "peers": ["INFY", "WIPRO"],
            },
            "business_quality": {
                "business_quality_score": 88,
                "strengths": ["Franchise", "Cash generation"],
                "weaknesses": ["Deal cyclicality"],
            },
            "financial_intelligence": {
                "coverage_pct": 96,
                "narrative": "Strong FCF and returns.",
                "what_improved": ["growth", "margins", "fcf"],
                "what_deteriorated": [],
                "enabled": True,
                "as_of": now,
            },
            "valuation_intelligence": {
                "coverage_pct": 92,
                "current_pe": 28,
                "forward_pe": 25,
                "peer_pe": 26,
                "premium_discount_vs_history_pct": -5,
                "peer_comparison": {"ok": True},
                "narrative": "Near history.",
                "as_of": now,
                "price_as_of": now,
            },
            "recommendation_readiness": {
                "scores": {
                    "financial_intelligence": 96,
                    "valuation": 92,
                    "sector_intelligence": 90,
                    "research": 93,
                    "evidence_confidence": 90,
                    "knowledge": 88,
                    "prediction_history": 80,
                },
                "overall": 91,
            },
            "risks": ["Deal cyclicality"],
            "catalysts": ["Next earnings"],
            "generated_at": now,
        },
        cid={
            "shareholding": {
                "promoter": 72,
                "fii": 12,
                "dii": 10,
                "as_of": now,
                "records": [{"period": now[:10], "period_end": now[:10]}],
            },
            "filings": [{"id": "1", "as_of": now}],
            "evidence_timeline": [{"id": "e1", "as_of": now}],
            "updated_at": now,
        },
        live_evidence={
            "generated_at": now,
            "quote": {"as_of": now},
            "evidence_objects": [
                {"kind": "quarterly_results", "as_of": now},
                {"kind": "corporate_announcement", "as_of": now},
                {"kind": "annual_report", "as_of": now},
            ],
        },
        evidence_completion={"quality_panel": {"coverage_pct": 93}},
        gate_blocked=False,
        force=True,
    )
    gate = out["institutional_readiness_gate"]
    assert gate["institutional_readiness_pct"] >= 80
    assert gate["band"] in {"moderate_conviction", "high_conviction_allowed"}
    assert out["summary"]["investment_thesis_status"] in {"FORMED", "INCONCLUSIVE"}
    # With rich + fresh packs, recommendation readiness should clear watchlist floor
    assert gate["recommendation_readiness_pct"] >= 60
