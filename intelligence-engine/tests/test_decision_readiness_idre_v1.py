"""RQ2 Sprint 9 — Institutional Decision Readiness Engine regression tests."""

from decision_readiness.production import (
    _scenario,
    build_readiness,
    generate_for_question,
    quality_gates,
    soft_slice_for_ask_agi,
)
from decision_readiness.readiness_engine import classify_readiness
from decision_readiness.schema import READINESS_STATES, READINESS_WEIGHTS, RESEARCH_TYPES


def test_hdfc_decision_package():
    row = generate_for_question(
        "Should I buy HDFC Bank?",
        {
            "falsification_complete": True,
            "evidence_metrics": {
                "coverage": 0.92,
                "authority": 0.94,
                "freshness": 0.9,
                "independence": 0.88,
            },
        },
    )
    assert row["ok"] is True
    assert row["decision_status"] in READINESS_STATES
    assert 0 <= row["readiness_score"] <= 1
    assert len(row["decision_heat_map"]) == 7
    assert row["decision_package"]["executive_summary"]
    assert row["decision_package"]["decision_readiness"]["status"] == row["decision_status"]
    assert row["monitoring_plan"]["review_frequency"]
    assert row["required_follow_up"] is not None


def test_weighted_readiness_score_reconciles():
    _, payload, _ = _scenario(0)
    result = build_readiness(
        question="Ready scenario",
        thesis=payload["thesis"],
        debate=payload["debate"],
        payload=payload,
    )
    expected = sum(
        READINESS_WEIGHTS[name] * result["dimensions"][name]["score"]
        for name in READINESS_WEIGHTS
    )
    assert abs(expected - result["readiness_score"]) < 0.001


def test_all_readiness_states_classified():
    for seed, expected in enumerate(READINESS_STATES):
        _, payload, scenario_expected = _scenario(seed)
        assert scenario_expected == expected
        result = build_readiness(
            question=f"Scenario {seed}",
            thesis=payload["thesis"],
            debate=payload["debate"],
            payload=payload,
        )
        assert result["decision_status"] == expected


def test_decision_heat_map_exposes_weak_dimension():
    _, payload, _ = _scenario(2)
    result = build_readiness(
        question="Research required",
        thesis=payload["thesis"],
        debate=payload["debate"],
        payload=payload,
    )
    heat = {row["dimension"]: row for row in result["decision_heat_map"]}
    assert set(heat) == {
        "Evidence",
        "Reasoning",
        "Debate",
        "Portfolio",
        "Monitoring",
        "Policy",
        "Confidence",
    }
    assert heat["Evidence"]["score_pct"] < 80
    assert heat["Evidence"]["state"] in ("Weak", "Blocked")


def test_go_no_go_conditions_and_monitoring():
    _, payload, _ = _scenario(1)
    result = build_readiness(
        question="Conditional scenario",
        thesis=payload["thesis"],
        debate=payload["debate"],
        payload=payload,
    )
    assert len(result["decision_conditions"]) >= 3
    for condition in result["decision_conditions"]:
        assert condition["result"] in ("GO", "NO-GO")
        assert condition["current"] is not None
        assert condition["threshold"] is not None
        assert condition["distance"] is not None
        assert condition["failure_action"] == "Automatic Committee Review"
    assert len(result["monitoring_plan"]["active_triggers"]) >= 3


def test_capital_readiness_separate_from_decision_readiness():
    _, payload, _ = _scenario(1)
    payload["portfolio_context"] = {
        "position_suitability": 0.65,
        "sector_concentration": 0.36,
        "factor_exposure": 0.48,
        "risk_budget_used": 0.88,
        "liquidity": 0.9,
        "diversification": 0.6,
    }
    result = build_readiness(
        question="Capital constraint scenario",
        thesis=payload["thesis"],
        debate=payload["debate"],
        payload=payload,
    )
    assert result["capital_allocation_readiness"] is not None
    assert result["dimensions"]["Portfolio"]["separate_from_thesis_quality"] is True
    assert result["portfolio_constraints"]
    assert result["capital_state"] in (
        "READY",
        "READY WITH LIMITS",
        "DO NOT ADD CAPITAL",
    )


def test_critical_policy_violation_blocks_decision():
    _, payload, _ = _scenario(0)
    payload["policy_context"] = {
        "violations": [
            {"id": "critical", "severity": "critical", "message": "Policy breach"}
        ]
    }
    result = build_readiness(
        question="Blocked",
        thesis=payload["thesis"],
        debate=payload["debate"],
        payload=payload,
    )
    assert result["decision_status"] == "NOT READY"
    assert result["dimensions"]["Policy"]["critical_violation_count"] == 1


def test_soft_slice_ask_agi():
    body = soft_slice_for_ask_agi(
        "Should I buy HDFC Bank?", {"falsification_complete": True}
    )["decision_readiness"]
    assert body["enabled"] is True
    assert body["not_a_top_level_intelligence_layer"] is True
    assert body["final_pre_committee_quality_gate"] is True
    assert body["executes_after"] == "Institutional Debate Engine"
    assert body["executes_before"] == "Investment Committee"
    assert body["decision_status"] in READINESS_STATES
    assert body["decision_heat_map"]
    assert body["decision_conditions"]


def test_quality_gates_meet_sprint_bar():
    gates = quality_gates()
    assert gates["total"] >= 5000
    assert gates["readiness_classification"] >= 0.99
    assert gates["evidence_completeness"] >= 1.0
    assert gates["monitoring_quality"] >= 1.0
    assert gates["conflict_resolution"] >= 1.0
    assert gates["decision_package_consistency"] >= 1.0
    assert gates["decision_heat_map"] >= 1.0
    assert gates["decision_conditions"] >= 1.0
    assert gates["capital_allocation_readiness"] >= 1.0
    assert set(RESEARCH_TYPES).issubset(gates["research_type_counts"])
    assert set(READINESS_STATES).issubset(gates["state_counts"])
    assert gates["avg_readiness_ms"] < 60
    assert gates["ok"] is True
