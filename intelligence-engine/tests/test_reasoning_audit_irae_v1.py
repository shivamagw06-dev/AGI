"""RQ2 Sprint 10 — Institutional Reasoning Audit Engine regression tests."""

from reasoning_audit.production import (
    _scenario,
    audit_reasoning,
    generate_for_question,
    quality_gates,
    soft_slice_for_ask_agi,
)
from reasoning_audit.schema import AUDIT_STATES, CHAIN_TYPES, REASONING_STAGES


def test_full_reasoning_chain_audited():
    row = generate_for_question("Should I buy HDFC Bank?", {})
    assert row["ok"] is True
    assert row["audit_status"] in AUDIT_STATES
    assert row["reasoning_score"] > 0
    assert row["traceability"]["traceability"] == 1.0
    assert row["traceability"]["orphan_count"] == 0
    assert row["reasoning_completeness"] == 1.0
    assert len(row["reasoning_trace"]["nodes"]) == len(REASONING_STAGES) - 1
    assert row["registry"]["audit_id"].startswith("IRAE-")


def test_evidence_trace_has_unbroken_conclusion_paths():
    payload, _ = _scenario(0)
    audit = audit_reasoning("Equity chain", payload)
    traceability = audit["traceability"]
    assert traceability["passed"] is True
    assert traceability["orphan_count"] == 0
    assert traceability["conclusion_traces"]
    for trace in traceability["conclusion_traces"]:
        assert trace["hypothesis_id"]
        assert trace["research_question_ids"]
        assert trace["evidence"]
        assert all(item["source"] for item in trace["evidence"])
        assert trace["reasoning_steps"]
        assert trace["complete"] is True


def test_logic_validator_and_scope():
    payload, _ = _scenario(0)
    audit = audit_reasoning("Portfolio chain", payload)
    assert audit["logic"]["passed"] is True
    assert all(audit["logic"]["checks"].values())
    assert audit["logic"]["unsupported_inferences"] == []
    assert audit["scope"]["passed"] is True
    assert audit["scope"]["violation_count"] == 0
    assert all(row["in_scope"] for row in audit["scope"]["validations"])


def test_assumptions_contradictions_and_calibration():
    payload, _ = _scenario(0)
    audit = audit_reasoning("Macro chain", payload)
    assert audit["assumptions"]["passed"] is True
    assert audit["assumptions"]["assumption_count"] >= 1
    assert all(
        assumption["explicit"]
        and assumption["tested"]
        and assumption["still_valid"]
        and assumption["linked_to_evidence"]
        for assumption in audit["assumptions"]["assumptions"]
    )
    assert audit["contradictions"]["passed"] is True
    assert audit["contradictions"]["all_contradictions_disclosed"] is True
    assert audit["calibration"]["passed"] is True
    assert audit["calibration"]["calibrated_count"] == audit["calibration"]["belief_count"]


def test_all_audit_states_and_hard_policy_failure():
    for seed, expected in enumerate(AUDIT_STATES):
        payload, scenario_expected = _scenario(seed)
        assert scenario_expected == expected
        audit = audit_reasoning(f"Scenario {seed}", payload)
        assert audit["audit_status"] == expected
    failed_payload, _ = _scenario(3)
    failed = audit_reasoning("Policy failure", failed_payload)
    assert failed["hard_failures"]["critical_policy_violations"] == 1
    assert failed["may_proceed"] is False


def test_reasoning_replay_engine():
    payload, _ = _scenario(0)
    replay = audit_reasoning("Comparative chain", payload)["reasoning_replay"]
    assert replay["replayable"] is True
    assert replay["event_count"] == 11
    assert [event["stage"] for event in replay["events"]] == list(REASONING_STAGES)
    assert replay["events"][0]["stage"] == "Question"
    assert replay["events"][-1]["stage"] == "Reasoning Audit"
    assert replay["controls"]["play"] is True
    assert replay["controls"]["step_forward"] is True
    assert replay["replay_id"]
    assert "analyst training" in replay["training_uses"]


def test_reasoning_scorecard_dimensions():
    payload, _ = _scenario(0)
    audit = audit_reasoning("Forecast chain", payload)
    scorecard = audit["reasoning_scorecard"]
    assert {
        "evidence_traceability",
        "logic",
        "calibration",
        "assumptions",
        "contradictions",
        "explainability",
        "policy",
        "analyst_scope",
        "reasoning_completeness",
        "overall_institutional_reasoning_score",
    } == set(scorecard)
    assert all(0 <= score <= 100 for score in scorecard.values())


def test_soft_slice_ask_agi():
    payload, _ = _scenario(0)
    body = soft_slice_for_ask_agi("Should I buy HDFC Bank?", payload)[
        "reasoning_audit"
    ]
    assert body["enabled"] is True
    assert body["not_a_top_level_intelligence_layer"] is True
    assert body["final_reasoning_certification_gate"] is True
    assert body["executes_after"] == "Institutional Decision Readiness Engine"
    assert body["executes_before"] == "Investment Committee"
    assert body["audit_status"] == "PASS"
    assert body["traceability"]["traceability"] == 1.0
    assert body["reasoning_replay"]["event_count"] == 11
    assert body["may_proceed"] is True


def test_quality_gates_meet_final_rq2_bar():
    gates = quality_gates()
    assert gates["total"] >= 10_000
    assert gates["traceability"] >= 1.0
    assert gates["logic"] >= 1.0
    assert gates["calibration"] >= 1.0
    assert gates["scope"] >= 1.0
    assert gates["policy"] >= 1.0
    assert gates["reasoning_completeness"] >= 1.0
    assert gates["reasoning_replay"] >= 1.0
    assert set(AUDIT_STATES).issubset(gates["state_counts"])
    assert set(CHAIN_TYPES).issubset(gates["chain_type_counts"])
    assert gates["avg_audit_ms"] < 75
    assert gates["ok"] is True
