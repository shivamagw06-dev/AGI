"""RQ2 Sprint 6 — Bayesian Belief & Confidence Engine regression tests."""

from belief_engine.posterior_engine import belief_state_from_posterior, update_posterior
from belief_engine.production import generate_for_question, quality_gates, soft_slice_for_ask_agi, update_belief
from belief_engine.schema import BELIEF_STATES


def test_hdfc_belief_update():
    row = generate_for_question("Should I buy HDFC Bank?", {})
    assert row["ok"] is True
    assert row["belief_count"] >= 2
    b = row["beliefs"][0]
    assert b["prior_belief"] is not None
    assert b["posterior_belief"] is not None
    assert b["belief_state"] in BELIEF_STATES
    assert b["confidence"] is not None
    assert b["uncertainty"]["overall_uncertainty"] is not None
    assert b["history"]
    assert b["history"][0]["step"] == "prior"
    assert b["history"][-1]["step"] == "posterior"
    assert b["drift"]["drift_level"] in ("stable", "material", "major")


def test_bayesian_log_odds_moves_with_evidence():
    prior = 0.6
    strong = update_posterior(prior, 2.0)
    weak = update_posterior(prior, -2.0)
    assert strong["posterior_belief"] > prior
    assert weak["posterior_belief"] < prior
    assert strong["belief_state"] in BELIEF_STATES


def test_belief_states_cover_spectrum():
    assert belief_state_from_posterior(0.9) == "Strongly Supported"
    assert belief_state_from_posterior(0.7) == "Supported"
    assert belief_state_from_posterior(0.5) == "Neutral"
    assert belief_state_from_posterior(0.2) == "Contradicted"
    assert belief_state_from_posterior(0.1) == "Rejected"


def test_update_belief_contract():
    belief = update_belief(
        {
            "id": "H1",
            "type": "Business",
            "hypothesis": "Durable funding advantage",
            "initial_confidence": 0.75,
            "support_score": 85,
            "contradiction_score": 60,
            "supporting_evidence": [{"id": "s1"}, {"id": "s2"}, {"id": "s3"}, {"id": "s4"}, {"id": "s5"}],
            "contradicting_evidence": [{"id": "c1"}, {"id": "c2"}],
            "missing_evidence": ["gap"],
            "evidence_effects": [
                {"id": "e1", "effect": "Confirms", "text": "CASA above peers"},
                {"id": "e2", "effect": "Contradicts", "text": "Deposit growth slowed"},
            ],
            "uncertainty": {"conflict_intensity": 0.4, "known_unknowns": ["x"], "missing_evidence": ["gap"]},
        },
        falsification={"severity": "stressed", "summary": "Survived stress with pressure"},
    )
    for key in (
        "prior_belief",
        "supporting_evidence",
        "contradicting_evidence",
        "posterior_belief",
        "belief_state",
        "confidence",
        "uncertainty",
        "calibration",
        "history",
    ):
        assert key in belief
    assert belief["falsification_applied"] is True


def test_soft_slice_ask_agi():
    wrap = soft_slice_for_ask_agi("Should I buy HDFC Bank?", {})
    body = wrap["belief_engine"]
    assert body["enabled"] is True
    assert body["not_a_top_level_intelligence_layer"] is True
    assert body["executes_after"] == "Institutional Falsification Engine"
    assert body["executes_before"] == "Business / Financial / Valuation opinions"
    assert body["belief_count"] >= 1
    assert body["belief_states"] == list(BELIEF_STATES)


def test_quality_gates_meet_sprint_bar():
    gates = quality_gates()
    assert gates["total"] >= 5000
    assert gates["prior_posterior_consistency"] >= 1.0
    assert gates["belief_state_coverage"] >= 1.0
    assert gates["calibration_reporting"] >= 1.0
    assert gates["history_tracking"] >= 1.0
    assert gates["drift_detection"] >= 1.0
    assert gates["avg_update_ms"] < 40
    assert len(gates["state_counts"]) >= 3
    assert gates["ok"] is True
