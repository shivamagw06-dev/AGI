"""FDI — Thesis Impact Matrix."""

from __future__ import annotations

from filing_diff.pipeline import analyse_diff
from filing_diff.thesis_matrix.matrix import build_thesis_impact_matrix, matrix_for_change
from filing_intelligence.ingestion.store import reset_for_tests


def setup_function() -> None:
    reset_for_tests()


def test_matrix_rules_for_canonical_examples():
    nim = matrix_for_change(
        {"metric": "NIM", "change_type": "margin_compression", "domain": "statement", "materiality": "high"}
    )
    assert nim["business"] == "◐"
    assert nim["financial"] == "✅"
    assert nim["valuation"] == "✅"
    assert nim["risk"] == "◐"
    assert nim["committee"] == "Review"

    casa = matrix_for_change(
        {"metric": "CASA", "change_type": "casa_decline", "domain": "statement", "materiality": "high"}
    )
    assert casa["business"] == "✅"
    assert casa["financial"] == "✅"
    assert casa["committee"] == "Review"

    buyback = matrix_for_change(
        {"metric": "Buybacks", "change_type": "buyback", "domain": "capital", "materiality": "high"}
    )
    assert buyback["financial"] == "✅"
    assert buyback["valuation"] == "✅"
    assert buyback["risk"] == "❌"
    assert buyback["committee"] == "Note"

    reg = matrix_for_change(
        {
            "metric": "Regulatory_Risk",
            "change_type": "risk_added",
            "domain": "risks",
            "materiality": "high",
        }
    )
    assert reg["risk"] == "✅"
    assert reg["financial"] == "❌"
    assert reg["committee"] == "Escalate"


def test_hdfc_matrix_attached_and_routable():
    out = analyse_diff("HDFCBANK")
    matrix = out["thesis_impact_matrix"]
    assert matrix["count"] >= 3
    assert matrix["markdown_table"].startswith("| Filing Change")
    assert matrix["analyst_routing"]["financial_analyst"]
    assert matrix["committee_queue"]["review"] or matrix["committee_queue"]["escalate"]

    casa = next(r for r in matrix["rows"] if r["metric"] == "CASA")
    assert casa["business"] == "✅"
    assert casa["financial"] == "✅"

    # each material change carries per-change matrix cells
    sample = next(c for c in out["changes"] if c["metric"] == "CASA")
    assert sample["thesis_impact_matrix"]["committee"] == "Review"

    report = out["report"]
    assert "THESIS IMPACT MATRIX" in report["text"]
    assert report["thesis_impact_matrix"]["rows"]
