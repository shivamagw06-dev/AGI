"""Filing Diff Engine V1 — what materially changed?"""

from __future__ import annotations

from filing_diff.management_diff.diff import _is_cosmetic
from filing_diff.pipeline import analyse_diff
from filing_diff.production import (
    admin_page,
    company,
    dashboard,
    quality_gates,
    soft_slice_for_irs,
)
from filing_diff.schema import FDI_VERSION
from filing_intelligence.ingestion.store import reset_for_tests


def setup_function() -> None:
    reset_for_tests()


def test_hdfc_diff_detects_financial_and_guidance():
    out = analyse_diff("HDFCBANK")
    assert out["found"] is True
    assert out["previous_period"] == "Q4FY26"
    assert out["current_period"] == "Q1FY27"
    domains = {c["domain"] for c in out["changes"]}
    assert "statement" in domains
    assert "guidance" in domains
    assert "management" in domains
    nim = next(c for c in out["changes"] if c["metric"] == "NIM")
    assert nim["change_type"] == "margin_compression"
    assert nim["materiality"] in {"critical", "high", "medium"}
    assert nim["current_doc_id"]
    assert nim["why_changed"]
    assert nim["thesis_impact"] in {
        "weakens_thesis",
        "needs_committee_review",
        "strengthens_thesis",
        "neutral",
        "unknown",
    }


def test_cosmetic_wording_not_material():
    assert _is_cosmetic(
        "Rebuild liability franchise and calibrate loan growth",
        "Rebuild the liability franchise and calibrate loan growth",
    )


def test_report_shape_and_no_buy_sell():
    out = company("HDFCBANK")
    report = out["report"]
    assert report["top_10_material_changes"]
    assert "investment_thesis_impact" in report
    assert report["cio_brief"]
    text = (report.get("text") or "").lower()
    assert "recommendation: buy" not in text and "recommendation: sell" not in text
    assert out["evidence"]["linked_count"] >= 1


def test_quality_gates_dashboard_admin_irs():
    assert dashboard()["fdi_version"] == FDI_VERSION
    gates = quality_gates()
    assert gates["passed"] is True, gates
    assert "Filing Diff Engine" in admin_page()
    assert soft_slice_for_irs()["filing_diff"]["quality_gates_passed"] is True

    from academy.regression.production import dashboard as irs_dashboard
    from academy.regression.production import reset_for_tests as irs_reset

    irs_reset()
    dash = irs_dashboard()
    assert dash["filing_diff"]["enabled"] is True
