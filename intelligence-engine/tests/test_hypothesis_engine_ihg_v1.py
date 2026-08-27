"""RQ2 Sprint 1 — Institutional Hypothesis Generation Engine regression tests."""

from hypothesis_engine.production import generate_for_question, quality_gates, soft_slice_for_ask_agi
from hypothesis_engine.quality_rules import evaluate_quality_rules
from hypothesis_engine.schema import HYPOTHESIS_TYPES, QUALITY_RULES


def test_hdfc_buy_hypotheses():
    row = generate_for_question("Should I buy HDFC Bank?", {})
    assert row["ok"] is True
    assert row["hypothesis_count"] >= 4
    types = {h["type"] for h in row["hypotheses"]}
    assert "Business" in types or "Valuation" in types
    assert "Financial" in types or "Competitive" in types
    for h in row["hypotheses"]:
        assert h["quality_compliant"] is True
        assert h["required_evidence"]
        assert h["responsible_analysts"]
        assert h["status"]
        assert len(h["hypothesis"]) >= 60


def test_nifty_it_historical():
    row = generate_for_question("Is Nifty IT expensive versus history?", {})
    types = {h["type"] for h in row["hypotheses"]}
    assert "Valuation" in types
    assert row["hypothesis_count"] >= 3


def test_rejects_generic_hypothesis():
    bad = evaluate_quality_rules("Apple is a good company.", required_evidence=[])
    assert bad["passed"] is False
    assert bad["generic_rejected"] is True

    good = evaluate_quality_rules(
        (
            "Apple's ecosystem allows it to sustain gross margins above industry averages "
            "despite premium pricing because switching costs and services attachment reduce customer churn."
        ),
        required_evidence=["Gross margin vs peers", "Churn / services attachment"],
        falsification_test="False if gross margins compress to industry average for 2+ years.",
    )
    assert good["passed"] is True


def test_output_contract_fields():
    row = generate_for_question("Compare TCS vs Infosys", {})
    assert row["ranking"]
    assert row["evidence_map"]["evidence_count"] >= 1
    assert "overall_confidence" in row
    h0 = row["hypotheses"][0]
    for key in ("hypothesis", "confidence", "required_evidence", "responsible_analysts", "status"):
        assert key in h0


def test_ranking_priorities_unique():
    row = generate_for_question("Should I buy HDFC Bank?", {})
    priorities = [h["priority"] for h in row["hypotheses"]]
    assert priorities == list(range(1, len(priorities) + 1))


def test_soft_slice_ask_agi():
    wrap = soft_slice_for_ask_agi("Should I buy HDFC Bank?", {})
    body = wrap["hypothesis_engine"]
    assert body["enabled"] is True
    assert body["not_a_top_level_intelligence_layer"] is True
    assert body["executes_after"] == "IREP"
    assert body["hypothesis_count"] >= 1
    assert body["five_quality_rules"] == list(QUALITY_RULES)


def test_taxonomy_covers_sprint_types():
    for t in (
        "Business",
        "Financial",
        "Valuation",
        "Macro",
        "Risk",
        "Portfolio",
        "Competitive",
        "Forecast",
    ):
        assert t in HYPOTHESIS_TYPES


def test_quality_gates_meet_sprint_bar():
    gates = quality_gates()
    assert gates["total"] >= 1000
    assert gates["hypothesis_generation_coverage"] >= 1.0
    assert gates["quality_rule_compliance"] >= 1.0
    assert gates["no_generic_hypotheses"] >= 1.0
    assert gates["ranking_consistency"] >= 0.99
    assert gates["avg_generation_ms"] < 30
    assert gates["ok"] is True
