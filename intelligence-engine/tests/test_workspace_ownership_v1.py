"""Workspace ownership — Decision Engine confidence breakdown soft-wire."""

from __future__ import annotations

from decision_engine.production import package_for_ask_agi


def test_confidence_breakdown_comes_from_ide_layers():
    out = package_for_ask_agi(
        "Should I buy Eternal?",
        ticker="ETERNAL.NS",
        company_analysis={
            "ticker": "ETERNAL.NS",
            "identity": {"company_name": "Eternal", "business_model": "Consumer internet."},
            "business_quality": {"business_quality_score": 74, "grade": "B+"},
            "financial_intelligence": {"coverage_pct": 50, "narrative": "Returns improving.", "what_improved": ["growth"]},
            "valuation_intelligence": {"current_pe": 40, "premium_discount_vs_history_pct": 10},
            "risks": ["Competition"],
            "catalysts": ["Earnings"],
        },
        force=True,
    )
    bd = (out.get("summary") or {}).get("confidence_breakdown") or {}
    assert bd.get("business") is not None
    assert bd.get("financial") is not None
    assert bd.get("valuation") is not None
    assert bd.get("risk") is not None
    # Breakdown must mirror layer scores — not UI-invented offsets
    scores = (out.get("summary") or {}).get("layer_scores") or {}
    assert bd["business"] == scores.get("company_quality")
    assert bd["financial"] == scores.get("financial_quality")
