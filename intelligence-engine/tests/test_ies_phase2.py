"""Institutional Evaluation Suite (IES) tests — Phase 2 exit criteria."""

from __future__ import annotations

from institutional_reasoning.evidence_contracts import classify_question, resolve_entities
from institutional_reasoning.ies.production import dashboard, inventory, quality_gates, run_ies
from institutional_reasoning.ies.schema import IES_VERSION, PHASE2_TARGETS, SUITES


def test_inventory_700_cases():
    inv = inventory()
    assert inv["version"] == IES_VERSION
    assert inv["total"] == 700
    for s in SUITES:
        assert inv["counts"][s] == 100


def test_left_to_right_entity_resolution_for_comparisons():
    assert resolve_entities("Compare Wipro vs HCL Tech.")["primary"]["entity_id"] == "WIPRO"
    assert resolve_entities("Compare ITC vs Dabur.")["primary"]["entity_id"] == "ITC"
    assert resolve_entities("Infosys vs TCS")["primary"]["entity_id"] == "INFY"


def test_education_does_not_trigger_evidence_contracts():
    assert classify_question("What is ROIC?")["question_type"] == "education"
    assert classify_question("Explain WACC.")["question_type"] == "education"


def test_sampled_ies_phase2_gate():
    """CI-speed sample (20/suite = 140). Full 700 is run offline / full gate."""
    report = run_ies(limit_per_suite=20)
    assert report["n"] == 140
    assert report["failed"] == 0, report["failures"][:5]
    m = report["metrics"]
    assert m["overall_score"] >= PHASE2_TARGETS["overall"]
    assert m["governance"]["unsupported_conclusions"] == 0
    assert m["governance"]["editorial_violations"] == 0
    assert m["governance"]["wrong_entity_execution"] == 0
    assert (m["suite_scores"]["insufficient"]["score"]) == 100.0
    assert (m["suite_scores"]["education"]["score"]) == 100.0


def test_quality_gates_inventory():
    gates = quality_gates(full=False, limit_per_suite=10)
    assert gates["gate"] == "INSTITUTIONAL_EVALUATION_SUITE"
    assert gates["inventory_ok"] is True
    assert gates["overall_score"] >= 90.0


def test_dashboard_shape():
    dash = dashboard(limit_per_suite=5)
    assert dash["overall_score"] is not None
    assert "dashboard_text" in dash
    assert "Institutional Evaluation Suite" in dash["dashboard_text"]
    assert dash["editorial_violations"] == 0
    assert dash["unsupported_conclusions"] == 0
