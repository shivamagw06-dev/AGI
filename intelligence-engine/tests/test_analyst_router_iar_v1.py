"""RQ1 Sprint 5 — Institutional Analyst Router regression tests."""

from analyst_router.production import CORE_BENCHMARKS, quality_gates
from analyst_router.router import route_question
from analyst_router.schema import ANALYST_REGISTRY, CONFIDENCE_THRESHOLD


def test_hdfc_buy_routing():
    row = route_question("Should I buy HDFC Bank?", {})
    assert row["primary_objective"] == "Investment Evaluation"
    assert row["required_analysts"] == [
        "Business",
        "Financial",
        "Valuation",
        "Risk",
        "Forecast",
        "Portfolio",
    ]
    assert "Macro" in row["optional_analysts"]
    assert "Ownership" in row["suppressed_analysts"]
    assert "Academy" in row["suppressed_analysts"]
    assert row["speaking_order"][:2] == ["Business", "Financial"]
    assert abs(row["weights"]["Business"] - 0.30) < 0.001
    assert abs(row["weights"]["Portfolio"] - 0.05) < 0.001
    assert row["executed_analysts"] == []
    assert float(row["routing_confidence"]["routing_confidence"]) >= CONFIDENCE_THRESHOLD


def test_explain_roic_academy_only_path():
    row = route_question("Explain ROIC", {})
    assert row["required_analysts"] == ["Academy", "Financial"]
    for a in ("Business", "Valuation", "Portfolio", "Committee"):
        assert a in row["suppressed_analysts"]


def test_peer_comparison():
    row = route_question("Compare TCS vs Infosys", {})
    assert set(row["required_analysts"]) == {"Business", "Financial", "Valuation", "Sector"}
    assert "Portfolio" in row["suppressed_analysts"]
    assert "Management" in row["suppressed_analysts"]


def test_historical_nifty_it():
    row = route_question("Is Nifty IT expensive versus history?", {})
    assert set(row["required_analysts"]) == {"Valuation", "Sector", "Macro", "Forecast"}
    for a in ("Business", "Management", "Portfolio"):
        assert a in row["suppressed_analysts"]


def test_research_assignments_present():
    row = route_question("Should I buy HDFC Bank?", {})
    by_name = {a["analyst"]: a for a in row["assignments"]}
    assert "Business" in by_name
    assert "durable competitive advantage" in by_name["Business"]["assignment"].lower()
    assert by_name["Valuation"]["never"]
    assert "PE" in by_name["Business"]["never"] or "DCF" in by_name["Business"]["never"]


def test_suppressed_never_in_speaking_order_as_required():
    row = route_question("Explain ROIC", {})
    assert "Committee" not in row["speaking_order"]
    assert set(row["required_analysts"]).isdisjoint(set(row["suppressed_analysts"]))


def test_registry_complete():
    assert "Business" in ANALYST_REGISTRY
    assert "Academy" in ANALYST_REGISTRY
    assert len(ANALYST_REGISTRY) >= 14


def test_core_benchmarks_required_sets():
    for b in CORE_BENCHMARKS:
        if not b.get("required"):
            continue
        row = route_question(b["q"], {})
        assert set(row["required_analysts"]) == set(b["required"])


def test_quality_gates_meet_sprint_bar():
    gates = quality_gates()
    assert gates["total"] >= 1000
    assert gates["analyst_selection_accuracy"] >= 0.98
    assert gates["exclusion_accuracy"] >= 0.98
    assert gates["speaking_order_accuracy"] >= 0.98
    assert gates["weight_accuracy"] >= 0.98
    assert gates["mandate_violations"] == 0
    assert gates["avg_routing_ms"] < 30
    assert gates["ok"] is True
