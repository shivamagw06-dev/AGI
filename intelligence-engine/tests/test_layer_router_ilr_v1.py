"""RQ1 Sprint 6 — Intelligence Layer Router regression tests."""

from layer_router.planner import plan_pipeline
from layer_router.production import quality_gates
from layer_router.schema import CONFIDENCE_THRESHOLD, REGISTERED_LAYERS


def test_hdfc_buy_execution_plan():
    row = plan_pipeline(
        "Should I buy HDFC Bank?",
        {"primary_objective": "Investment Evaluation", "skip_iar": True},
    )
    req = set(row["required_layers"])
    for layer in ("FIL", "EIL", "PIL", "Business", "Financial", "Valuation", "Committee", "Portfolio", "IDE V2", "CIO"):
        assert layer in req
    assert "Ownership" in row["suppressed_layers"]
    assert "SSL" in row["suppressed_layers"]
    order = row["execution_graph"]["order"]
    assert order.index("FIL") < order.index("EIL")
    assert order.index("Business") < order.index("Committee")
    assert order.index("IDE V2") < order.index("CIO")
    assert row["executed_layers"] == []
    assert row["runtime_reduction"] >= 0.25
    assert float(row["confidence_plan"]["planned_confidence"]) >= CONFIDENCE_THRESHOLD
    assert row["expected_contribution_by_layer"]["FIL"] > 0


def test_educational_minimal():
    row = plan_pipeline("Explain ROIC", {"primary_objective": "Educational", "skip_iar": True})
    assert set(row["required_layers"]) == {"ILM", "Research Writer"}
    for layer in ("SSL", "Committee", "Portfolio"):
        assert layer in row["suppressed_layers"]


def test_historical_suppresses_business_portfolio():
    row = plan_pipeline(
        "Is Nifty IT expensive versus history?",
        {"primary_objective": "Historical Analysis", "skip_iar": True},
    )
    for layer in ("Business", "Portfolio", "Management"):
        assert layer in row["suppressed_layers"]
    assert "PIL" in row["required_layers"]


def test_parallel_groups_present():
    row = plan_pipeline(
        "Should I buy HDFC Bank?",
        {"primary_objective": "Investment Evaluation", "skip_iar": True},
    )
    assert len(row["parallel_groups"]) >= 2
    assert any(g.get("parallel") for g in row["parallel_groups"])


def test_expected_contribution_table():
    row = plan_pipeline(
        "Should I buy HDFC Bank?",
        {"primary_objective": "Investment Evaluation", "skip_iar": True},
    )
    running = [r for r in row["expected_contributions"] if r["required"]]
    total = sum(r["expected_contribution"] for r in running)
    assert abs(total - 1.0) < 0.02
    assert row["learning_hook"]["feed_into"] == "ILM"


def test_registry_covers_sprint_layers():
    for layer in ("FIL", "EIL", "PIL", "ILM", "SSL", "IDE V2", "CIO", "Research Writer"):
        assert layer in REGISTERED_LAYERS


def test_quality_gates_meet_sprint_bar():
    gates = quality_gates()
    assert gates["total"] >= 1000
    assert gates["layer_routing_accuracy"] >= 0.99
    assert gates["dependency_accuracy"] >= 1.0
    assert gates["parallel_execution_accuracy"] >= 0.95
    assert gates["suppressed_layer_accuracy"] >= 0.98
    assert gates["avg_planning_ms"] < 30
    assert gates["avg_runtime_reduction"] >= 0.25
    assert gates["ok"] is True
