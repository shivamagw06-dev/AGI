"""Phase 6 acceptance — Institutional Outcome Intelligence (IOI)."""

from __future__ import annotations

from institutional_reasoning.execution_governance import govern_answer
from institutional_reasoning.ioi.attribution import attribute_outcome
from institutional_reasoning.ioi.calibration import reset_calibration
from institutional_reasoning.ioi.evaluator import evaluate_prediction
from institutional_reasoning.ioi.lifecycle import get_decision, reset_lifecycle
from institutional_reasoning.ioi.market import collect_outcome, inject_outcome, reset_market
from institutional_reasoning.ioi.memory import recall, reset_memory, snapshot
from institutional_reasoning.ioi.outcome_graph import build_outcome_graph
from institutional_reasoning.ioi.outcome_suite import run_outcome_suite
from institutional_reasoning.ioi.pipeline import evaluate_decision, track_decision
from institutional_reasoning.ioi.production import quality_gates
from institutional_reasoning.ioi.schema import PHASE6_TARGETS
from institutional_reasoning.ioi.scoreboard import reset_scoreboard
from institutional_reasoning.ipi.memory import reset_memory as reset_ipi_memory


def setup_function() -> None:
    reset_lifecycle()
    reset_memory()
    reset_market()
    reset_calibration()
    reset_scoreboard()
    reset_ipi_memory()


# -------------------------------------------------------------- lifecycle
def test_decision_lifecycle_links_djg_and_pdg():
    record = govern_answer("Should we invest £1,000,000 in Infosys?", ticker_hint="INFY")
    assert record.get("ioi", {}).get("decision_id")
    life = get_decision(record["ioi"]["decision_id"])
    assert life
    assert life["research_djg"]
    assert life["portfolio_djg"]
    assert life["ticker"] == "INFY"
    assert life["expected_return"] is not None or life["withheld"]


# ------------------------------------------------------------------ market
def test_market_outcome_engine_versioned():
    inject_outcome("INFY", {"total_return": 0.16, "benchmark_return": 0.10, "sector_return": 0.12, "max_drawdown": 0.08})
    m = collect_outcome("INFY")
    assert m["found"] is True
    assert m["versioned"] is True
    assert m["alpha"] == 0.06
    assert m["total_return"] == 0.16


# --------------------------------------------------------------- evaluator
def test_prediction_evaluator_small_error():
    life = {
        "expected_return": 0.18,
        "expected_downside": 0.10,
        "decision": {"action": "Increase", "confidence": 0.85},
        "scenarios": {"base": {"expected_return": 0.18}, "bear": {"expected_return": -0.12}},
    }
    market = collect_outcome("INFY", override={"total_return": 0.16, "benchmark_return": 0.10, "max_drawdown": 0.08})
    ev = evaluate_prediction(life, market)
    assert ev["small_error"] is True
    assert abs(ev["return_error"]) <= 0.05
    assert ev["score"] is not None


# ------------------------------------------------------------- attribution
def test_attribution_identifies_macro_not_valuation():
    life = {
        "expected_return": 0.15,
        "expected_downside": 0.10,
        "position_weight": 0.05,
        "research_djg": "djg1",
        "frameworks": [
            {"framework_id": "rel_val_damodaran", "name": "Relative Valuation", "status": "executed"},
            {"framework_id": "business_quality_roic", "name": "Business Quality", "status": "executed"},
        ],
        "risk": {"risk_contribution": 0.05},
        "policy": {},
        "scenarios": {},
        "decision": {"action": "Increase", "confidence": 0.8},
    }
    market = {"found": True, "total_return": -0.20, "sector_return": -0.18, "benchmark_return": 0.10, "alpha": -0.30, "maximum_drawdown": 0.25}
    ev = evaluate_prediction(life, market)
    attr = attribute_outcome(life, market, ev, force_wrong={"macro": True, "scenario": True})
    assert attr["unattributed"] is False
    primary = attr["primary_failure"] or {}
    assert primary.get("kind") == "macro" or primary.get("component") == "macro"
    assert primary.get("kind") != "valuation"


def test_sizing_failure_attributed():
    life = {
        "expected_return": 0.10,
        "expected_downside": 0.08,
        "position_weight": 0.07,
        "research_djg": "djg1",
        "frameworks": [{"framework_id": "rel_val_damodaran", "name": "RV", "status": "executed"}],
        "risk": {"risk_contribution": 0.15},
        "policy": {"violates_concentration": True},
        "scenarios": {},
        "decision": {"action": "Increase", "confidence": 0.9},
    }
    market = {"found": True, "total_return": -0.15, "sector_return": 0.0, "benchmark_return": 0.08, "alpha": -0.23, "maximum_drawdown": 0.22}
    ev = evaluate_prediction(life, market)
    attr = attribute_outcome(life, market, ev, force_wrong={"sizing": True, "policy": True})
    assert "sizing" in attr["wrong"] or "policy" in attr["wrong"]
    assert attr["unattributed"] is False


# ------------------------------------------------------------------- review
def test_full_pipeline_review_and_og():
    record = govern_answer("Should we invest in Infosys?", ticker_hint="INFY")
    decision_id = record["ioi"]["decision_id"]
    result = evaluate_decision(
        decision_id,
        market_override={"total_return": 0.14, "benchmark_return": 0.10, "sector_return": 0.12, "max_drawdown": 0.07},
    )
    assert result["found"] is True
    assert result["learning_applied"] is False
    review = result["review"]
    for key in ("decision_quality", "research_quality", "risk_quality", "portfolio_quality", "overall_quality"):
        assert key in review
    og = result["outcome_graph"]
    assert og["integrity"]["valid"] is True
    assert og["integrity"]["linked_to_djg"] is True
    assert og["integrity"]["linked_to_pdg"] is True
    cal = result["calibration"]["frameworks"]
    assert cal
    assert cal[0]["ies_confidence"] is not None
    assert cal[0]["live_outcome_confidence"] is not None


def test_outcome_graph_builder_integrity():
    record = {
        "decision_id": "dec_x",
        "lifecycle": {
            "ticker": "INFY",
            "research_djg": "djg1",
            "portfolio_djg": "pdg1",
            "research_djg_integrity": True,
            "portfolio_djg_integrity": True,
        },
        "market": {"found": True, "total_return": 0.1, "alpha": 0.02},
        "evaluation": {"score": 80, "grade": "B", "return_error": -0.02},
        "attribution": {"wrong": [], "unattributed": False, "primary_failure": None},
        "review": {"overall_quality": {"grade": "B", "score": 80}},
    }
    og = build_outcome_graph(record)
    assert og["integrity"]["valid"] is True
    assert og["integrity"]["complete_lifecycle"] is True


# ------------------------------------------------------------------- memory
def test_outcome_memory_persists_chain():
    record = govern_answer("Should we invest in Infosys?", ticker_hint="INFY")
    evaluate_decision(record["ioi"]["decision_id"], market_override={"total_return": 0.1, "benchmark_return": 0.09, "max_drawdown": 0.05})
    snap = snapshot()
    assert snap["count"] >= 1
    assert snap["learning_applied"] is False
    rows = recall("INFY")
    assert rows
    assert rows[-1]["djg"]
    assert rows[-1]["pdg"]
    assert "attribution" in rows[-1]


# --------------------------------------------------------------- isolation
def test_phase1_can_skip_outcome_tracking():
    record = govern_answer(
        "Should we invest in Infosys?",
        ticker_hint="INFY",
        build_portfolio_intelligence=True,
        build_outcome_intelligence=False,
    )
    # IPI may exist but IOI tracking disabled
    assert not (record.get("ioi") or {}).get("decision_id")


# -------------------------------------------------------------------- suite
def test_institutional_outcome_suite_exit_gate():
    suite = run_outcome_suite()
    assert suite["score"] >= PHASE6_TARGETS["outcome_suite"]
    assert suite["traceability_pct"] >= PHASE6_TARGETS["traceability"]
    assert suite["unattributed_failures"] <= PHASE6_TARGETS["unattributed_failures"]
    assert suite["phase6_gate"]["passed"] is True
    assert suite["learning_applied"] is False


def test_quality_gates_facade():
    gates = quality_gates()
    assert gates["passed"] is True
    assert gates["gate"] == "INSTITUTIONAL_OUTCOME_INTELLIGENCE"
    assert gates["learning_applied"] is False
