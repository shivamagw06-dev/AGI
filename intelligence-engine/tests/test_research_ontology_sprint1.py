"""RQ1 Sprint 1 — Research Ontology constitution & classify-only gates."""

from research_ontology.classifier import classify_question
from research_ontology.production import quality_gates
from research_ontology.schema import MANDATORY_OUTPUT_FIELDS


def test_benchmark_hdfc_bank_company_research():
    row = classify_question("Should I buy HDFC Bank?")
    assert row["primary_intent"] == "Company Research"
    assert row["entity"] == "HDFC Bank"
    assert row["entity_type"] == "Company"
    assert row["research_objective"] == "Investment Evaluation"
    assert row["requires_clarification"] is False
    assert "valuation" in row["secondary_intents"]
    assert row["executed_layers"] == []
    assert row["executed_analysts"] == []


def test_benchmark_nifty_it_index_research():
    row = classify_question("Is Nifty IT expensive versus history?")
    assert row["primary_intent"] == "Index Research"
    assert row["entity"] == "Nifty IT"
    assert row["entity_type"] == "Index"
    assert "historical_comparison" in row["secondary_intents"]
    assert row["executed_layers"] == []


def test_benchmark_tcs_vs_infosys():
    row = classify_question("Compare TCS vs Infosys.")
    assert row["primary_intent"] == "Company Comparison"
    assert "TCS" in (row["entity"] or "")
    assert "Infosys" in (row["entity"] or "")
    assert row["executed_layers"] == []


def test_benchmark_rbi_macro():
    row = classify_question("What happens if RBI cuts rates?")
    assert row["primary_intent"] == "Macro Research"
    assert row["executed_layers"] == []


def test_benchmark_explain_roic_educational():
    row = classify_question("Explain ROIC.")
    assert row["primary_intent"] == "Educational"
    assert row["entity"] == "ROIC"
    assert row["executed_layers"] == []


def test_benchmark_portfolio_add_reliance():
    row = classify_question("Should I add Reliance to my portfolio?")
    assert row["primary_intent"] == "Portfolio Research"
    assert row["entity"] in {"Reliance Industries", "My Portfolio"}
    assert row["executed_layers"] == []


def test_benchmark_fmcg_screening():
    row = classify_question("Best FMCG companies with high ROIC.")
    assert row["primary_intent"] == "Screening"
    assert row["executed_layers"] == []


def test_benchmark_infosys_earnings_news():
    row = classify_question("Summarise today's Infosys earnings.")
    assert row["primary_intent"] == "News"
    assert row["entity"] == "Infosys"
    assert row["executed_layers"] == []


def test_ambiguous_tata_requires_clarification():
    row = classify_question("Should I buy Tata?")
    assert row["requires_clarification"] is True
    assert row["entity"] is None
    assert row["executed_layers"] == []
    assert row["executed_analysts"] == []
    assert len(row["possible_matches"]) >= 3
    assert row["next_stage"] == "clarification_engine"


def test_mandatory_output_fields_present():
    row = classify_question("Should I buy HDFC Bank?")
    for field in MANDATORY_OUTPUT_FIELDS:
        assert field in row


def test_quality_gates_pass():
    gates = quality_gates()
    assert gates["ok"] is True
    assert gates["passed"] == gates["total"]
