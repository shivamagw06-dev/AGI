"""RQ1 Sprint 3 — Research Objective Engine regression tests."""

from research_objective.production import CORE_BENCHMARKS, plan_question, quality_gates
from research_objective.schema import CONFIDENCE_THRESHOLD, PRIMARY_OBJECTIVES


def _plan(q: str):
    return plan_question(q, {"skip_ere": True, "entity_resolution": {}})


def test_investment_evaluation_hdfc():
    row = _plan("Should I buy HDFC Bank?")
    assert row["primary_objective"] == "Investment Evaluation"
    assert row["question_type"] == "Should I Buy?"
    assert row["expected_output"] == "Institutional Report"
    assert row["research_depth"] == "Institutional"
    assert "Committee" in row["analysts"]
    assert row["blueprint_sections"][0] == "Executive Summary"
    assert "Investment Thesis" in row["blueprint_sections"]
    assert row["executed_layers"] == []
    assert row["executed_analysts"] == []
    assert float(row["objective_confidence"]) >= CONFIDENCE_THRESHOLD


def test_peer_comparison():
    row = _plan("Compare TCS vs Infosys")
    assert row["primary_objective"] == "Peer Comparison"
    assert row["expected_output"] == "Comparison Report"
    assert "Peer" in row["analysts"]


def test_educational_roic():
    row = _plan("Explain ROIC")
    assert row["primary_objective"] == "Educational"
    assert row["expected_output"] == "Educational Guide"
    assert row["analysts"] == ["Academy"]
    assert row["layers"] == []


def test_macro_impact_rbi():
    row = _plan("How will RBI rate cuts affect banks?")
    assert row["primary_objective"] == "Macro Impact"
    assert row["expected_output"] == "Macro Report"
    assert "RBI" in row["apis"]
    assert "Forecast" in row["secondary_objectives"]


def test_historical_valuation_nifty_it():
    row = _plan("Is Nifty IT expensive versus history?")
    assert row["primary_objective"] == "Historical Analysis"
    assert row["expected_output"] == "Valuation Report"
    for layer in ("FIL", "EIL", "PIL", "CIG", "FIE"):
        assert layer in row["layers"]
    for skip in ("Management", "Portfolio", "Accounting"):
        assert skip in row["layers_skip"]
    assert "Historical multiples" in row["apis"]


def test_portfolio_construction():
    row = _plan("Build a ₹500,000 portfolio")
    assert row["primary_objective"] == "Portfolio Decision"
    assert row["expected_output"] == "Portfolio Memo"


def test_exactly_one_primary_from_locked_set():
    for b in CORE_BENCHMARKS:
        row = _plan(b["q"])
        assert row["primary_objective"] in PRIMARY_OBJECTIVES
        assert row["primary_objective"] == b["objective"]


def test_low_confidence_blocks_execution():
    row = _plan("?")
    assert row["requires_clarification"] is True
    assert row["block_execution"] is True


def test_quality_gates_meet_sprint_bar():
    gates = quality_gates()
    assert gates["total"] >= 1000
    assert gates["primary_objective_accuracy"] >= 0.99
    assert gates["question_type_accuracy"] >= 0.98
    assert gates["blueprint_accuracy"] >= 0.98
    assert gates["analyst_routing_accuracy"] >= 0.98
    assert gates["layer_routing_accuracy"] >= 0.98
    assert gates["avg_planning_ms"] < 30
    assert gates["ok"] is True
