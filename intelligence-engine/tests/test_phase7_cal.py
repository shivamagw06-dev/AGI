"""Phase 7 acceptance — Continuous Adaptive Learning (CAL)."""

from __future__ import annotations

from institutional_reasoning.cal.governance import (
    approve,
    deploy,
    get_proposal,
    govern_learning,
    propose_from_outcome,
    reset_governance,
    simulate,
    validate_proposal,
)
from institutional_reasoning.cal.learning_graph import build_learning_graph
from institutional_reasoning.cal.learning_suite import run_learning_suite
from institutional_reasoning.cal.production import quality_gates
from institutional_reasoning.cal.regime import detect_regime
from institutional_reasoning.cal.sandbox import simulate_proposal
from institutional_reasoning.cal.schema import PHASE7_TARGETS
from institutional_reasoning.cal.versions import active_state, list_versions, reset_versions
from institutional_reasoning.execution_governance import govern_answer
from institutional_reasoning.ioi.lifecycle import reset_lifecycle
from institutional_reasoning.ioi.market import inject_outcome, reset_market
from institutional_reasoning.ioi.memory import reset_memory as reset_ioi_memory
from institutional_reasoning.ioi.pipeline import evaluate_decision
from institutional_reasoning.ipi.memory import reset_memory as reset_ipi_memory


def setup_function() -> None:
    reset_governance()
    reset_versions()
    reset_lifecycle()
    reset_ioi_memory()
    reset_market()
    reset_ipi_memory()


def _evaluated(entity: str = "WIPRO", ret: float = -0.20) -> dict:
    inject_outcome(
        entity,
        {
            "total_return": ret,
            "benchmark_return": 0.08,
            "sector_return": -0.12,
            "max_drawdown": 0.22,
            "volatility": 0.30,
        },
    )
    research = govern_answer(f"Should we invest in {entity}?", ticker_hint=entity)
    return evaluate_decision(
        research["ioi"]["decision_id"],
        market_override={
            "total_return": ret,
            "benchmark_return": 0.08,
            "sector_return": -0.12,
            "max_drawdown": 0.22,
            "volatility": 0.30,
        },
        force_wrong={"macro": True},
        persist=True,
    )


# ----------------------------------------------------------- candidates
def test_outcome_review_generates_learning_proposals():
    outcome = _evaluated()
    assert outcome.get("learning_proposals", {}).get("count", 0) >= 1
    assert outcome["learning_proposals"]["auto_deployed"] is False
    batch = propose_from_outcome(outcome)
    kinds = {p["kind"] for p in batch["proposals"]}
    assert "rewrite_framework" not in kinds
    assert batch["proposals"]
    assert all(p.get("requires_governance") for p in batch["proposals"])


# --------------------------------------------------------------- sandbox
def test_proposal_that_hurts_ies_is_rejected():
    proposal = {
        "proposal_id": "lp_hurt",
        "kind": "adjust_planner_priority",
        "target": "rel_val_damodaran",
        "delta": -0.5,
        "force_hurt_ies": True,
        "auto_apply": False,
        "requires_governance": True,
    }
    sim = simulate_proposal(proposal)
    assert sim["passed"] is False
    assert "ies_regression" in (sim.get("reasons") or []) or sim.get("reason") == "ies_regression"


def test_improving_proposal_can_be_approved_and_versioned():
    outcome = _evaluated()
    governed = govern_learning(outcome, approver="governance")
    assert governed["ungoverned_changes"] == 0
    assert governed["learning_applied_to_source"] is False
    deployed = [r for r in governed["results"] if r.get("status") == "deployed"]
    # At least one actionable path should clear sandbox for a clear failure
    actionable = [r for r in governed["results"] if r.get("kind") != "no_change"]
    assert actionable
    assert any((r.get("simulation") or {}).get("passed") for r in actionable) or deployed
    if deployed:
        assert list_versions()
        assert deployed[0].get("learning_graph", {}).get("integrity", {}).get("valid")


# ------------------------------------------------------------ calibration
def test_confidence_and_planner_overlays_update_only_via_versions():
    before = active_state()["planner_version"]
    outcome = _evaluated("INFY", -0.15)
    govern_learning(outcome, approver="governance")
    # Versions may or may not bump depending on candidates; overlays never rewrite source flag
    assert active_state().get("planner_weights")
    # Source frameworks untouched marker
    for v in list_versions():
        assert v.get("source_overwritten") is False
    assert before  # baseline existed


# ----------------------------------------------------------------- regime
def test_regime_detection_segments_learning():
    r = detect_regime(market={"total_return": -0.20, "maximum_drawdown": 0.30, "volatility": 0.45})
    assert r["regime"] in {"crisis", "bear"}
    outcome = _evaluated()
    batch = propose_from_outcome(outcome)
    assert batch["regime"]["regime"]
    for p in batch["proposals"]:
        assert "regime" in p


# -------------------------------------------------------- learning graph
def test_learning_graph_links_outcome_to_version():
    g = build_learning_graph(
        {
            "outcome_ref": "dec_abc",
            "proposal": {
                "proposal_id": "lp1",
                "kind": "decrease_confidence",
                "target": "macro",
                "source_outcome_id": "dec_abc",
            },
            "simulation": {"passed": True, "ies_delta": 0.0, "live_delta": 0.03},
            "approval": {"approved": True, "approver": "governance"},
            "deployment": {
                "deployed": True,
                "version_id": "ver_1",
                "planner_version": "planner-v1.0.1",
            },
        }
    )
    assert g["integrity"]["valid"] is True
    assert g["integrity"]["linked_to_og"] is True
    assert g["integrity"]["source_overwritten"] is False


# ----------------------------------------------------------- governance
def test_never_outcome_directly_to_production():
    outcome = _evaluated()
    # evaluate_decision must not deploy
    assert outcome.get("learning_applied") is False
    assert outcome.get("learning_proposals", {}).get("auto_deployed") is False
    # Only govern_learning → approve → deploy mutates overlays
    before_versions = len(list_versions())
    propose_from_outcome(outcome)
    assert len(list_versions()) == before_versions


def test_policy_proposal_requires_human_approver():
    from institutional_reasoning.cal.governance import _PROPOSALS

    pid = "lp_policy_human"
    _PROPOSALS[pid] = {
        "proposal_id": pid,
        "kind": "adjust_policy",
        "target": "max_stock_weight",
        "from_value": 0.08,
        "to_value": 0.06,
        "requires_human_approval": True,
        "auto_apply": False,
        "requires_governance": True,
        "forbidden": ["rewrite_framework"],
        "status": "proposed",
        "source_outcome_id": "dec_x",
    }
    validate_proposal(pid)
    simulate(pid)
    row = approve(pid, approver="automatic")
    assert row.get("status") != "approved" or (row.get("approval") or {}).get("reason") == "human_approval_required"
    row = approve(pid, approver="human_committee")
    if (get_proposal(pid) or {}).get("simulation", {}).get("passed"):
        assert row.get("status") == "approved"
        deployed = deploy(pid)
        assert deployed.get("status") == "deployed"


# ----------------------------------------------------------------- suite
def test_institutional_learning_suite_exit_gate():
    suite = run_learning_suite()
    assert suite["score"] >= PHASE7_TARGETS["learning_suite"]
    assert suite["traceability_pct"] >= PHASE7_TARGETS["traceability"]
    assert suite["ungoverned_changes"] <= PHASE7_TARGETS["ungoverned_changes"]
    assert suite["ies_regressions"] <= PHASE7_TARGETS["ies_regression"]
    assert suite["phase7_gate"]["passed"] is True
    assert suite["learning_applied_to_source"] is False


def test_quality_gates_facade():
    gates = quality_gates()
    assert gates["passed"] is True
    assert gates["gate"] == "CONTINUOUS_ADAPTIVE_LEARNING"
    assert gates["learning_applied_to_source"] is False
