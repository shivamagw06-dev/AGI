"""RQ2 Sprint 7 — Institutional Thesis Construction Engine regression tests."""

from thesis_engine.conviction_engine import thesis_state
from thesis_engine.production import (
    build_thesis,
    generate_for_question,
    quality_gates,
    soft_slice_for_ask_agi,
)
from thesis_engine.schema import (
    MIN_CATALYSTS,
    MIN_MAJOR_CONTRADICTIONS,
    MIN_SUPPORTING_PILLARS,
    PILLARS,
    THESIS_STATES,
)


def test_hdfc_thesis_construction():
    row = generate_for_question("Should I buy HDFC Bank?", {})
    assert row["ok"] is True
    t = row["thesis"]
    assert t["core_thesis"]["statement"]
    assert len(t["supporting_pillars"]) == len(PILLARS)
    assert t["status"] in THESIS_STATES
    assert t["conviction"]["overall"] is not None
    assert t["audit"]["passed"] is True
    counts = t["audit"]["counts"]
    assert counts["supporting_pillars"] >= MIN_SUPPORTING_PILLARS
    assert counts["major_contradictions"] >= MIN_MAJOR_CONTRADICTIONS
    assert counts["catalysts"] >= MIN_CATALYSTS
    assert counts["thesis_breaking_conditions"] >= 1


def test_output_contract_fields():
    row = generate_for_question("Is Nifty IT expensive versus history?", {})
    t = row["thesis"]
    for key in (
        "core_thesis",
        "supporting_pillars",
        "contradictions",
        "catalysts",
        "timeline",
        "confidence",
        "conviction",
        "missing_evidence",
        "status",
    ):
        assert key in t


def test_catalysts_have_polarity_timing_probability():
    row = generate_for_question("Should I buy HDFC Bank?", {})
    catalysts = row["thesis"]["catalysts"]
    polarities = {c["polarity"] for c in catalysts}
    assert polarities & {"Positive", "Negative"}
    for c in catalysts:
        assert c["expected_timing"] in ("Near Term", "Medium Term", "Long Term")
        assert 0 < float(c["probability"]) < 1
        assert c["evidence_required"]


def test_pillar_dependency_chain_present():
    row = generate_for_question("Should I buy HDFC Bank?", {})
    graph = row["thesis"]["dependency_graph"]
    edges = {(e["from"], e["to"]) for e in graph["edges"]}
    assert ("Business Quality", "Financial Quality") in edges
    assert ("Financial Quality", "Valuation") in edges
    assert ("Valuation", "Portfolio Fit") in edges


def test_weak_pillars_produce_weaker_thesis():
    weak_beliefs = [
        {
            "hypothesis_id": f"W{i}",
            "hypothesis": f"Weak hypothesis {i}",
            "type": t,
            "posterior_belief": 0.2,
            "confidence": 0.4,
            "supporting_evidence": [{"text": "thin support", "support_score": 40}],
            "contradicting_evidence": [
                {"text": "strong challenge", "contradiction_score": 88},
                {"text": "second challenge", "contradiction_score": 80},
            ],
            "missing_evidence": ["large gap"],
            "uncertainty": {"known_unknowns": ["unknown"], "missing_evidence": ["large gap"]},
        }
        for i, t in enumerate(["Business", "Financial", "Valuation", "Macro", "Portfolio"])
    ]
    thesis = build_thesis(weak_beliefs, question="Should I buy X?", payload={})
    assert thesis["conviction"]["overall"] < 0.55
    assert thesis["status"] in ("Emerging", "Developing", "Weakening", "Broken", "Rejected")


def test_thesis_state_bands():
    assert thesis_state(0.8, supported_pillars=6, major_contradictions=1) == "Very Strong"
    assert thesis_state(0.2, supported_pillars=1, major_contradictions=5) == "Rejected"


def test_soft_slice_ask_agi():
    wrap = soft_slice_for_ask_agi("Should I buy HDFC Bank?", {})
    body = wrap["thesis_engine"]
    assert body["enabled"] is True
    assert body["not_a_top_level_intelligence_layer"] is True
    assert body["executes_after"] == "Bayesian Belief & Confidence Engine"
    assert body["executes_before"] == "Investment Committee"
    assert body["core_thesis"]["statement"]
    assert body["committee_handoff"]["debate_this"]


def test_quality_gates_meet_sprint_bar():
    gates = quality_gates()
    assert gates["total"] >= 2000
    assert gates["thesis_construction"] >= 1.0
    assert gates["logical_consistency"] >= 1.0
    assert gates["pillar_completeness"] >= 1.0
    assert gates["contradiction_handling"] >= 1.0
    assert gates["catalyst_quality"] >= 1.0
    assert gates["conviction_calibration"] >= 1.0
    assert gates["interaction_quantification"] >= 1.0
    assert gates["stability_tracking"] >= 1.0
    assert gates["quality_separation"] >= 1.0
    assert gates["pressure_monitoring"] >= 1.0
    assert gates["avg_build_ms"] < 60
    assert len(gates["state_counts"]) >= 2
    assert gates["ok"] is True


def test_world_class_thesis_extensions():
    thesis = generate_for_question("Should I buy HDFC Bank?", {})["thesis"]

    matrix = thesis["pillar_interaction_matrix"]
    assert matrix["pillars"] == list(PILLARS)
    assert len(matrix["values"]) == len(PILLARS)
    assert all(matrix["values"][i][i] == 1.0 for i in range(len(PILLARS)))
    assert any(e["influence"] == 0.6 for e in matrix["edges"])

    stability = thesis["stability"]
    assert 0 <= stability["score"] <= 1
    assert stability["trend"] in ("Stable", "Improving", "Weakening", "Volatile")

    quality = thesis["quality"]
    assert quality["separate_from_conviction"] is True
    assert {"evidence", "contradictions", "coverage", "calibration"} <= set(
        quality["dimensions"]
    )

    narratives = thesis["narratives"]
    assert narratives["one_sentence"]
    assert narratives["one_paragraph"]
    assert narratives["one_page"]["investment_case"]

    assert thesis["thesis_dna"]["fingerprint"]
    assert thesis["thesis_dna"]["persistent_traits"]


def test_waterfall_monitoring_evolution_and_pressure():
    thesis = generate_for_question("Should I buy HDFC Bank?", {})["thesis"]
    waterfall = thesis["conviction_waterfall"]
    assert waterfall["reconciles"] is True
    assert abs(
        waterfall["starting_conviction"]
        + sum(step["impact"] for step in waterfall["steps"])
        - waterfall["ending_conviction"]
    ) < 0.001

    monitoring = thesis["monitoring"]
    assert monitoring["conditions"]
    assert monitoring["next_review_at"]
    assert all(
        item["current"] is not None
        and item["threshold"] is not None
        and item["distance"] is not None
        for item in monitoring["conditions"]
    )

    evolution = thesis["evolution"]
    assert evolution["current_version"] >= 1
    assert evolution["history"][-1]["change_type"]
    assert evolution["ilm_payload"]["feed_into"] == "ILM"

    pressure = thesis["pressure_gauge"]
    assert 0 <= pressure["score"] <= 100
    assert pressure["level"] in ("Low", "Moderate", "High", "Critical")
    assert abs(sum(pressure["components"].values()) - pressure["score"]) < 0.2
    assert pressure["separate_from_confidence"] is True
