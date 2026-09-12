"""RQ1 Sprint 8 — Dynamic Research Blueprint Engine regression tests."""

from research_blueprint.dynamic_layout import build_research_blueprint
from research_blueprint.production import quality_gates, soft_slice_for_ask_agi
from research_blueprint.schema import MAX_BLUEPRINT_MS_TARGET


def test_hdfc_institutional_investment_report():
    row = build_research_blueprint(
        "Should I buy HDFC Bank?",
        {"primary_objective": "Investment Evaluation"},
    )
    assert row["report_type"] == "institutional_investment_report"
    for section in (
        "executive_summary",
        "investment_thesis",
        "business_quality",
        "financial_quality",
        "valuation",
        "risk",
        "forecast",
        "portfolio_fit",
        "committee_opinion",
        "cio_summary",
    ):
        assert section in row["section_order"]
    assert row["section_owner"]["business_quality"] == "Business"
    assert row["section_owner"]["valuation"] == "Valuation"
    assert row["section_owner"]["cio_summary"] == "CIO"
    assert row["assignment_book"]["assignment_count"] >= 5


def test_comparison_report_structure():
    row = build_research_blueprint(
        "Compare TCS vs Infosys",
        {"primary_objective": "Peer Comparison"},
    )
    assert row["report_type"] == "comparison_report"
    for section in (
        "business_comparison",
        "financial_comparison",
        "valuation_comparison",
        "conclusion",
    ):
        assert section in row["section_order"]
    assert "portfolio_fit" in row["suppressed_sections"]


def test_educational_guide_suppresses_irrelevant():
    row = build_research_blueprint("Explain ROIC", {"primary_objective": "Educational"})
    assert row["report_type"] == "educational_guide"
    for section in ("definition", "calculation", "case_study", "summary"):
        assert section in row["section_order"]
    for section in ("portfolio_fit", "committee_opinion", "forecast", "valuation"):
        assert section in row["suppressed_sections"]
        assert section not in row["mandatory_sections"]


def test_historical_valuation_blueprint():
    row = build_research_blueprint(
        "Is Nifty IT expensive versus history?",
        {"primary_objective": "Historical Analysis"},
    )
    assert row["report_type"] == "historical_valuation_report"
    assert row["section_order"][0] == "executive_summary"
    assert "historical_percentiles" in row["section_order"]


def test_macro_dynamic_order():
    row = build_research_blueprint(
        "How will RBI rate cuts affect banks?",
        {"primary_objective": "Macro Impact"},
    )
    assert row["report_type"] == "macro_intelligence_report"
    assert row["section_order"][:4] == [
        "executive_summary",
        "macro_drivers",
        "policy",
        "transmission",
    ]


def test_assignment_book_missions():
    row = build_research_blueprint(
        "Should I buy HDFC Bank?",
        {"primary_objective": "Investment Evaluation"},
    )
    by_owner = {a["owner"]: a for a in row["assignment_book"]["assignments"]}
    assert "Business" in by_owner
    assert "durable competitive advantage" in by_owner["Business"]["mission"].lower()
    assert "PE" in by_owner["Business"]["must_not_discuss"]
    assert "Valuation" in by_owner
    assert "Management quality" in by_owner["Valuation"]["must_not_discuss"]


def test_soft_slice_shape():
    slice_ = soft_slice_for_ask_agi("Explain ROIC", {"primary_objective": "Educational"})
    assert slice_["not_a_top_level_intelligence_layer"] is True
    assert slice_["report_type"] == "educational_guide"
    assert "assignment_book" in slice_


def test_quality_gates_meet_sprint_bar():
    gates = quality_gates()
    assert gates["checked"] >= 1000
    assert gates["blueprint_accuracy"] >= 0.99
    assert gates["correct_report_selection"] >= 0.99
    assert gates["correct_section_ownership"] >= 1.0
    assert gates["no_irrelevant_sections"] >= 1.0
    assert gates["average_blueprint_ms"] < MAX_BLUEPRINT_MS_TARGET
    assert gates["ok"] is True
