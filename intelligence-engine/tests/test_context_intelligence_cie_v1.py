"""RQ1 Sprint 4 — Context Intelligence Engine regression tests."""

from context_intelligence.enricher import enrich_question
from context_intelligence.production import quality_gates
from context_intelligence.schema import CONFIDENCE_THRESHOLD


def test_hdfc_buy_context_card():
    row = enrich_question(
        "Should I buy HDFC Bank?",
        {
            "primary_objective": "Investment Evaluation",
            "question_type": "Should I Buy?",
            "decision_type": "Investment",
            "research_depth": "Institutional",
            "expected_output": "Institutional Report",
            "skip_iar": True,
        },
    )
    assert row["time_context"]["time_horizon"] == "Long Term"
    assert row["portfolio_context"]["required"] is True
    assert "Peers" in row["comparison_context"]["lenses"]
    assert "History" in row["comparison_context"]["lenses"]
    assert row["scenario_context"]["scenario"] == "Normal"
    assert "priced in" in (row["expectation_context"]["summary"] or "").lower()
    card = row["research_context_card"]
    assert card["entity"]
    assert "Business Quality" in card["priority_areas"]
    assert card["yaml_preview"]
    assert row["executed_layers"] == []
    assert float(row["confidence"]["overall"]) >= CONFIDENCE_THRESHOLD


def test_nifty_it_historical():
    row = enrich_question(
        "Is Nifty IT expensive versus history?",
        {"primary_objective": "Historical Analysis", "skip_iar": True},
    )
    assert row["historical_context"]["required"] is True
    assert row["portfolio_context"]["required"] is False
    assert "History" in row["comparison_context"]["lenses"]
    assert "Nifty IT" in str(row["entity_context"].get("entity") or "")


def test_ten_year_horizon():
    row = enrich_question("Should I invest for 10 years?", {"skip_iar": True})
    assert row["time_context"]["time_horizon"] == "10 Years"


def test_today_horizon():
    row = enrich_question("What happened today in markets?", {"skip_iar": True})
    assert row["time_context"]["time_horizon"] == "Today"


def test_rate_cut_macro_event():
    row = enrich_question(
        "How will RBI rate cuts affect banks?",
        {"primary_objective": "Macro Impact", "skip_iar": True},
    )
    assert row["scenario_context"]["scenario"] == "Rate Cuts"
    assert "Rate Decision" in row["event_context"]["events"]


def test_educational_no_portfolio():
    row = enrich_question(
        "Explain ROIC",
        {"primary_objective": "Educational", "question_type": "Explain", "skip_iar": True},
    )
    assert row["portfolio_context"]["required"] is False
    assert row["user_context"]["mode"] == "Learning"


def test_quality_gates_meet_sprint_bar():
    gates = quality_gates()
    assert gates["total"] >= 1000
    assert gates["context_accuracy"] >= 0.98
    assert gates["time_horizon_detection"] >= 0.99
    assert gates["market_context_detection"] >= 0.95
    assert gates["comparison_context_accuracy"] >= 0.98
    assert gates["portfolio_context_accuracy"] >= 0.99
    assert gates["avg_runtime_ms"] < 25
    assert gates["ok"] is True
