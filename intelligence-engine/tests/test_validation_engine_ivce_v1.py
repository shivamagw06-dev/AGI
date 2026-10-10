"""RQ1 Sprint 9 — Institutional Validation & Clarification Engine regression tests."""

from validation_engine.production import quality_gates, soft_slice_for_ask_agi, validate
from validation_engine.readiness_gate import validate_request
from validation_engine.schema import MAX_VALIDATION_MS_TARGET


def test_hdfc_ready_with_memo():
    row = validate_request("Should I buy HDFC Bank?", {})
    assert row["readiness_state"] in {"READY", "READY_WITH_WARNINGS"}
    assert row["execution_allowed"] is True
    assert row["overall_readiness"] >= 0.7
    memo = row["readiness_memo"]
    assert memo["status"] in {"READY", "READY_WITH_WARNINGS"}
    assert "Clear entity" in memo["strengths"] or memo["entity"]


def test_tata_requires_clarification():
    row = validate_request("Analyse Tata", {})
    assert row["readiness_state"] == "CLARIFICATION_REQUIRED"
    assert row["execution_allowed"] is False
    types = {c["type"] for c in row["clarifications"]}
    assert "entity_disambiguation" in types


def test_compare_missing_target():
    row = validate_request("Compare Infosys", {})
    assert row["readiness_state"] == "CLARIFICATION_REQUIRED"
    assert row["execution_allowed"] is False
    types = {c["type"] for c in row["clarifications"]}
    assert "comparison_target" in types


def test_compare_pair_ready():
    row = validate_request("Compare TCS vs Infosys", {})
    assert row["execution_allowed"] is True
    assert row["readiness_state"] in {"READY", "READY_WITH_WARNINGS"}


def test_portfolio_clarification():
    row = validate_request("Build portfolio", {})
    assert row["readiness_state"] in {"CLARIFICATION_REQUIRED", "READY_WITH_WARNINGS"}
    if row["readiness_state"] == "CLARIFICATION_REQUIRED":
        types = {c["type"] for c in row["clarifications"]}
        assert "portfolio_inputs" in types


def test_policy_blocks_guaranteed_returns():
    row = validate_request("guaranteed returns on Infosys", {})
    assert row["readiness_state"] == "BLOCKED"
    assert row["execution_allowed"] is False


def test_educational_ready():
    row = validate_request("Explain ROIC", {})
    assert row["execution_allowed"] is True
    assert row["readiness_state"] in {"READY", "READY_WITH_WARNINGS"}


def test_soft_slice_shape():
    slice_ = soft_slice_for_ask_agi("Should I buy HDFC Bank?", {})
    assert slice_["not_a_top_level_intelligence_layer"] is True
    assert "readiness_memo" in slice_
    assert "overall_readiness" in slice_


def test_api_validate_alias():
    row = validate({"question": "Explain ROIC"})
    assert row["ok"] is True
    assert row["execution_allowed"] is True


def test_quality_gates_meet_sprint_bar():
    gates = quality_gates()
    assert gates["checked"] >= 1000
    assert gates["validation_accuracy"] >= 0.99
    assert gates["clarification_accuracy"] >= 0.99
    assert gates["false_ready_rate"] <= 0.01
    assert gates["false_block_rate"] <= 0.01
    assert gates["average_runtime_ms"] < MAX_VALIDATION_MS_TARGET
    assert gates["ok"] is True
