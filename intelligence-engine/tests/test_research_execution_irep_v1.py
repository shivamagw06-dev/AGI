"""RQ1 Sprint 10 — Institutional Research Execution Package regression tests."""

from research_execution.package_builder import build_execution_package
from research_execution.package_export import export_package
from research_execution.production import quality_gates, soft_slice_for_ask_agi
from research_execution.schema import MAX_PACKAGE_MS_TARGET, MANDATORY_PACKAGE_SECTIONS


def test_hdfc_irep_complete():
    row = build_execution_package("Should I buy HDFC Bank?", {})
    for section in MANDATORY_PACKAGE_SECTIONS:
        assert section in row
    assert row["immutable"] is True
    assert row["package_complete"] is True
    assert row["package_consistent"] is True
    assert (row["entity"] or {}).get("ticker") == "HDFCBANK"
    assert "Business" in (row["analyst_plan"] or {}).get("required_analysts", [])
    assert "FIL" in (row["layer_plan"] or {}).get("required_layers", [])
    assert (row["blueprint"] or {}).get("report_type") == "institutional_investment_report"
    assert (row["research_contract"] or {}).get("minimum_evidence") >= 12
    assert "Recommend based on momentum" in (row["research_contract"] or {}).get("must_not", [])


def test_comparison_blueprint():
    row = build_execution_package("Compare TCS vs Infosys", {})
    assert (row["blueprint"] or {}).get("report_type") == "comparison_report"
    assert row["package_complete"] is True


def test_educational_suppresses_portfolio():
    row = build_execution_package("Explain ROIC", {})
    assert (row["blueprint"] or {}).get("report_type") == "educational_guide"
    suppressed = set((row["analyst_plan"] or {}).get("suppressed_analysts") or [])
    assert "Portfolio" in suppressed or "Committee" in suppressed


def test_tata_clarification_in_validation():
    row = build_execution_package("Analyse Tata", {})
    assert (row["validation"] or {}).get("readiness_state") == "CLARIFICATION_REQUIRED"
    assert (row["execution_plan"] or {}).get("may_execute") is False


def test_no_analyst_layer_conflicts():
    row = build_execution_package("Should I buy Infosys?", {})
    req_a = set((row["analyst_plan"] or {}).get("required_analysts") or [])
    sup_a = set((row["analyst_plan"] or {}).get("suppressed_analysts") or [])
    req_l = set((row["layer_plan"] or {}).get("required_layers") or [])
    sup_l = set((row["layer_plan"] or {}).get("suppressed_layers") or [])
    assert not (req_a & sup_a)
    assert not (req_l & sup_l)


def test_export_markdown():
    row = build_execution_package("Explain ROIC", {})
    md = export_package(row, "markdown")
    assert md["format"] == "markdown"
    assert "Institutional Research Execution Package" in md["body"]


def test_soft_slice_shape():
    slice_ = soft_slice_for_ask_agi("Should I buy HDFC Bank?", {})
    assert slice_["immutable"] is True
    assert slice_["rq1_final_package"] is True
    assert "research_contract" in slice_
    assert slice_["package_complete"] is True


def test_quality_gates_meet_sprint_bar():
    gates = quality_gates()
    assert gates["checked"] >= 1000
    assert gates["package_completeness"] >= 1.0
    assert gates["package_consistency"] >= 1.0
    assert gates["no_conflicting_plans"] >= 1.0
    assert gates["correct_analyst_plan"] >= 0.99
    assert gates["correct_layer_plan"] >= 0.99
    assert gates["correct_blueprint"] >= 0.99
    assert gates["average_package_ms"] < MAX_PACKAGE_MS_TARGET
    assert gates["ok"] is True
    assert gates["rq1_complete"] is True
