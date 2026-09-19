"""RQ2 Sprint 8 — Institutional Debate Engine regression tests."""

from debate_engine.production import (
    build_debate,
    generate_for_question,
    quality_gates,
    soft_slice_for_ask_agi,
)
from debate_engine.schema import ANALYSTS, DEBATE_STATES, POSITIONS


def test_institutional_debate_package():
    row = generate_for_question("Should I buy HDFC Bank?", {})
    assert row["ok"] is True
    assert row["not_another_committee"] is True
    debate = row["debate"]
    assert debate["investment_thesis"]
    assert len(debate["analyst_positions"]) == len(ANALYSTS)
    assert all(position["position"] in POSITIONS for position in debate["analyst_positions"])
    assert debate["audit"]["passed"] is True
    assert debate["consensus"]["state"] in DEBATE_STATES


def test_conflict_detection_and_evidence_mapping():
    debate = generate_for_question("Should I buy HDFC Bank?", {})["debate"]
    assert debate["disagreement"]["disagreement_count"] >= 2
    assert debate["disagreement"]["conflicts"]
    assert len(debate["evidence_conflicts"]) >= 2
    for conflict in debate["evidence_conflicts"]:
        assert conflict["supporting_evidence"]
        assert conflict["opposing_evidence"]
        assert conflict["required_additional_evidence"]
        assert 0 <= conflict["evidence_quality"] <= 100


def test_assumption_conflicts_and_minority_preserved():
    debate = generate_for_question("Should I buy HDFC Bank?", {})["debate"]
    assert len(debate["assumption_conflicts"]) >= 2
    assert all(conflict["challenged"] for conflict in debate["assumption_conflicts"])
    assert debate["minority_report"]
    assert all(report["preserved"] for report in debate["minority_report"])
    assert all(
        report["conditions_to_become_majority"]
        for report in debate["minority_report"]
    )


def test_challenge_tournament_revises_positions():
    debate = generate_for_question("Should I buy HDFC Bank?", {})["debate"]
    tournament = debate["challenge_tournament"]
    assert tournament["completed"] is True
    assert tournament["round_count"] >= 3
    assert tournament["revision_count"] >= 3
    for round_row in tournament["rounds"]:
        assert round_row["challenge"]
        assert round_row["response"]
        assert round_row["revision"]["from_score"] != round_row["revision"]["to_score"]
        assert round_row["consensus_recalculation_required"] is True


def test_debate_scorecard_measures_process_quality():
    scorecard = generate_for_question("Should I buy HDFC Bank?", {})["debate"][
        "debate_scorecard"
    ]
    assert 0 <= scorecard["overall"] <= 100
    assert scorecard["irs_ready"] is True
    assert {
        "evidence_quality",
        "assumption_testing",
        "contradiction_coverage",
        "minority_preservation",
        "consensus_strength",
        "debate_completeness",
    } == set(scorecard["metrics"])


def test_moderator_and_committee_handoff():
    debate = generate_for_question("Should I buy HDFC Bank?", {})["debate"]
    assert debate["moderator"]["agreement_summary"]
    assert debate["moderator"]["disagreement_summary"]
    assert debate["moderator"]["critical_issues"]
    handoff = debate["committee_handoff"]
    assert handoff["thesis"]
    assert handoff["strongest_arguments_against"]
    assert handoff["minority_position"]
    assert handoff["evidence_to_settle"]


def test_soft_slice_ask_agi():
    body = soft_slice_for_ask_agi("Should I buy HDFC Bank?", {})[
        "debate_engine"
    ]
    assert body["enabled"] is True
    assert body["not_a_top_level_intelligence_layer"] is True
    assert body["not_another_committee"] is True
    assert body["executes_after"] == "Institutional Thesis Construction Engine"
    assert body["executes_before"] == "Investment Committee"
    assert body["challenge_tournament"]["round_count"] >= 3
    assert body["debate_scorecard"]["metrics"]


def test_quality_gates_meet_sprint_bar():
    gates = quality_gates()
    assert gates["total"] >= 2000
    assert gates["analyst_disagreements"] >= 20_000
    assert gates["correct_conflict_detection"] >= 1.0
    assert gates["agreement_quality"] >= 1.0
    assert gates["minority_preservation"] >= 1.0
    assert gates["evidence_conflict_mapping"] >= 1.0
    assert gates["consensus_accuracy"] >= 1.0
    assert gates["moderator_quality"] >= 1.0
    assert gates["challenge_tournament"] >= 1.0
    assert gates["debate_scorecard"] >= 1.0
    assert gates["avg_debate_ms"] < 60
    assert gates["ok"] is True
