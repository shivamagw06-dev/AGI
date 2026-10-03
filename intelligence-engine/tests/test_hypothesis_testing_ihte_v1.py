"""RQ2 Sprint 4 — Institutional Hypothesis Testing Engine regression tests."""

from hypothesis_testing.effect_classifier import classify_effect
from hypothesis_testing.production import generate_for_question, quality_gates, soft_slice_for_ask_agi
from hypothesis_testing.schema import EVIDENCE_EFFECTS, MIN_SUPPORTING_EVIDENCE


def test_hdfc_funding_hypothesis_tested():
    row = generate_for_question("Should I buy HDFC Bank?", {})
    assert row["ok"] is True
    assert row["tested_count"] >= 2
    h = row["tested_hypotheses"][0]
    assert h["supporting_evidence"]
    assert len(h["supporting_evidence"]) >= MIN_SUPPORTING_EVIDENCE
    assert h["contradicting_evidence"]
    assert h["updated_probability"] is not None
    assert h["status"] in (
        "Supported",
        "Partially Supported",
        "Inconclusive",
        "Contradicted",
        "Rejected",
    )
    assert h["assumptions"]["explicit"]
    assert h["uncertainty"]["missing_evidence"] is not None
    assert h["reasoning_ledger"]
    assert h["reasoning_ledger"][0]["event"] == "created"
    assert h["reasoning_ledger"][-1]["event"] == "final_status"
    assert (h.get("audit") or {}).get("passed") is True


def test_qualitative_evidence_effects():
    assert classify_effect({"polarity": "support", "strength": 92}) == "Confirms"
    assert classify_effect({"polarity": "support", "strength": 75}) == "Supports"
    assert classify_effect({"polarity": "contradict", "strength": 68}) == "Contradicts"
    assert classify_effect({"polarity": "contradict", "strength": 90}) == "Refutes"
    assert classify_effect({"polarity": "contradict", "strength": 45}) == "Questions"
    row = generate_for_question("Should I buy HDFC Bank?", {})
    effects = {e["effect"] for h in row["tested_hypotheses"] for e in h.get("evidence_effects") or []}
    assert effects & {"Confirms", "Supports", "Contradicts", "Questions"}


def test_probability_moves_with_evidence():
    row = generate_for_question("Is Nifty IT expensive versus history?", {})
    h = row["tested_hypotheses"][0]
    assert h["probability_timeline"]
    assert h["initial_confidence"] != h["updated_probability"] or h["net_delta"] == 0.0
    assert "net_delta" in h


def test_output_contract_fields():
    row = generate_for_question("Compare TCS vs Infosys", {})
    h = row["tested_hypotheses"][0]
    for key in (
        "hypothesis",
        "initial_confidence",
        "support_score",
        "contradiction_score",
        "missing_evidence",
        "updated_probability",
        "status",
        "assumptions",
        "uncertainty",
        "confidence",
    ):
        assert key in h


def test_soft_slice_ask_agi():
    wrap = soft_slice_for_ask_agi("Should I buy HDFC Bank?", {})
    body = wrap["hypothesis_testing"]
    assert body["enabled"] is True
    assert body["not_a_top_level_intelligence_layer"] is True
    assert body["executes_after"] == "Evidence Planning"
    assert body["executes_before"] == "Business / Financial / Valuation Analysts"
    assert body["tested_count"] >= 1
    assert body["enhancements"]["reasoning_ledger"] is True
    assert body["evidence_effects"] == list(EVIDENCE_EFFECTS)


def test_quality_gates_meet_sprint_bar():
    gates = quality_gates()
    assert gates["total"] >= 10_000
    assert gates["evidence_attribution"] >= 1.0
    assert gates["support_scoring"] >= 1.0
    assert gates["contradiction_scoring"] >= 1.0
    assert gates["probability_updates"] >= 1.0
    assert gates["uncertainty_reporting"] >= 1.0
    assert gates["avg_testing_ms"] < 50
    for t in ("Business", "Financial", "Valuation", "Macro", "Risk", "Portfolio"):
        assert gates["type_counts"].get(t, 0) > 0
    assert gates["ok"] is True
