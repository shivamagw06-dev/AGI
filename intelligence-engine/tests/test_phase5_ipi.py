"""Phase 5 acceptance — Institutional Portfolio Intelligence (IPI)."""

from __future__ import annotations

from institutional_reasoning.execution_governance import govern_answer
from institutional_reasoning.ipi.decision import decide_portfolio
from institutional_reasoning.ipi.downside import compute_downside
from institutional_reasoning.ipi.exposure import compute_exposure
from institutional_reasoning.ipi.memory import recall, reset_memory, snapshot
from institutional_reasoning.ipi.pdg import build_portfolio_decision_graph
from institutional_reasoning.ipi.portfolio_book import high_it_book, reset_book, set_active_book
from institutional_reasoning.ipi.portfolio_suite import run_portfolio_suite
from institutional_reasoning.ipi.production import package_for_governance, quality_gates
from institutional_reasoning.ipi.risk import compute_risk
from institutional_reasoning.ipi.schema import PHASE5_TARGETS
from institutional_reasoning.ipi.sizing import size_position


def setup_function() -> None:
    reset_memory()
    reset_book()


# -------------------------------------------------------------- evidence pack
def test_portfolio_evidence_pack_exposes_contract_fields():
    pkg = package_for_governance("INFY", entity_name="Infosys")
    assert pkg["found"] is True
    assert pkg.get("exposure") is not None
    assert pkg.get("risk_contribution") is not None
    assert pkg.get("downside_case") is not None or pkg.get("withhold") is True
    assert pkg.get("expected_return") is not None or pkg.get("withhold") is True


# -------------------------------------------------------------------- downside
def test_missing_downside_withholds():
    d = compute_downside(entity_id="UNKNOWNX", evidence={}, risk_inputs={})
    assert d["computable"] is False
    assert d["withhold"] is True
    decision = decide_portfolio(
        entity_id="UNKNOWNX",
        research_record={"run_id": "r1", "justification_graph": {"run_id": "djg1"}},
        existing_packs={},
        persist_memory=False,
    )
    assert decision["withheld"] is True
    assert (decision.get("committee") or {}).get("action") == "Withhold"
    assert decision.get("unsupported") is False


# ------------------------------------------------------------------------ risk
def test_risk_contribution_and_budget_present():
    risk = compute_risk(entity_id="INFY", candidate_weight=0.08)
    assert risk["risk_contribution"] > 0
    assert risk["risk_budget"] > 0
    assert risk["var"] > 0
    assert risk["expected_shortfall"] > 0
    assert "risk_drivers" in risk


# ------------------------------------------------------------------- exposure
def test_high_it_sector_limit_breach():
    set_active_book(high_it_book())
    exp = compute_exposure(entity_id="INFY", proposed_weight=0.12)
    assert exp["rejected"] is True
    assert any(b["kind"] == "sector" for b in exp["breaches"])
    reset_book()


# --------------------------------------------------------------------- sizing
def test_sizing_returns_weights_not_buy_sell():
    decision = decide_portfolio(entity_id="INFY", persist_memory=False)
    sizing = decision["sizing"]
    assert sizing["action"] not in {"Buy", "Sell", "Accumulate"}
    assert "target_weight" in sizing
    assert "maximum_weight" in sizing
    assert "minimum_weight" in sizing


def test_low_liquidity_caps_weight():
    decision = decide_portfolio(entity_id="PERSISTENT", persist_memory=False)
    tw = float((decision.get("sizing") or {}).get("target_weight") or 0)
    action = (decision.get("committee") or {}).get("action")
    assert action in {"Increase", "Hold", "Reduce", "Watch", "Exit", "Replace", "Hedge", "Withhold"}
    if action not in {"Withhold", "Watch", "Exit"}:
        assert tw <= 0.025 + 1e-9


# ------------------------------------------------------------------------- PDG
def test_pdg_links_to_djg_and_is_valid():
    research = govern_answer("Should we invest £1,000,000 in Infosys?", ticker_hint="INFY")
    ipi = research.get("ipi") or {}
    pdg = research.get("portfolio_decision_graph") or ipi.get("portfolio_decision_graph") or {}
    assert pdg.get("nodes")
    assert (pdg.get("integrity") or {}).get("valid") is True
    assert pdg.get("djg_reference") or ipi.get("djg_reference")
    assert "REFERENCES_DJG" in (pdg.get("edge_kinds") or []) or any(
        e.get("kind") == "REFERENCES_DJG" for e in (pdg.get("edges") or [])
    )


def test_pdg_builder_integrity_on_minimal_decision():
    decision = {
        "run_id": "pdg_test",
        "entity_id": "INFY",
        "djg_reference": "djg_abc",
        "research_run_id": "fer_x",
        "portfolio_evidence": {"expected_return": 0.1, "expected_downside": 0.08, "evidence_coverage": 0.8},
        "risk": {"risk_contribution": 0.05, "risk_budget": 0.12, "var": 0.02},
        "exposure": {"rejected": False, "breaches": []},
        "scenarios": {"shocks": [{"id": "x"}], "scenarios": {"base": {}}},
        "policy": {"allowed": True, "reasons": []},
        "sizing": {"action": "Increase", "target_weight": 0.054, "conviction": "High"},
        "committee": {
            "action": "Increase",
            "can_recommend": True,
            "target_weight": 0.054,
            "conclusion": "Increase to 5.4%",
        },
        "withheld": False,
    }
    pdg = build_portfolio_decision_graph(decision)
    assert pdg["integrity"]["valid"] is True
    assert pdg["integrity"]["linked_to_djg"] is True


# ------------------------------------------------------------------- governance
def test_govern_answer_attaches_ipi_for_investment_decision():
    record = govern_answer("Should we invest £1,000,000 in Infosys?", ticker_hint="INFY")
    assert record.get("question_type") == "investment_decision"
    assert record.get("ipi")
    assert record.get("portfolio_decision_graph")
    assert (record["portfolio_decision_graph"].get("integrity") or {}).get("valid") is True
    rec = record.get("portfolio_recommendation") or {}
    assert rec.get("action") not in {"Buy", "Sell"}


def test_portfolio_contract_fields_filled_via_ipi_pack():
    record = govern_answer("What is the portfolio exposure impact of Infosys?", ticker_hint="INFY")
    assert record.get("question_type") == "portfolio"
    validation = record.get("validation") or {}
    # exposure + risk_contribution should be present via institutional_portfolio pack
    missing = set(validation.get("missing") or [])
    assert "exposure" not in missing
    assert "risk_contribution" not in missing


def test_phase1_isolation_still_skips_ipi_when_disabled():
    record = govern_answer(
        "Is Infosys expensive?",
        ticker_hint="INFY",
        build_institutional_evidence=False,
        build_portfolio_intelligence=False,
    )
    assert not record.get("ipi")
    assert not record.get("institutional_portfolio")


# --------------------------------------------------------------------- memory
def test_portfolio_memory_stores_snapshot_without_learning():
    decide_portfolio(entity_id="INFY", persist_memory=True)
    snap = snapshot()
    assert snap["count"] >= 1
    rows = recall("INFY")
    assert rows
    assert "decision" in rows[-1]
    assert "position_size" in rows[-1]


# -------------------------------------------------------------- correlated IT
def test_correlated_it_elevates_risk_contribution():
    # INFY with peers in book should show elevated contribution vs tiny weight alone
    risk = compute_risk(entity_id="INFY", candidate_weight=0.10)
    assert risk["risk_contribution"] > 0.05
    assert "sector_correlation" in (risk.get("risk_drivers") or []) or risk["sector_risk"] >= 0.15


# --------------------------------------------------------------- phase 5 gate
def test_institutional_portfolio_suite_exit_gate():
    suite = run_portfolio_suite()
    assert suite["score"] >= PHASE5_TARGETS["portfolio_suite"]
    assert suite["pdg_coverage_pct"] >= PHASE5_TARGETS["pdg_coverage"]
    assert suite["unsupported_recommendations"] <= PHASE5_TARGETS["unsupported_recommendations"]
    assert suite["phase5_gate"]["passed"] is True


def test_quality_gates_facade():
    gates = quality_gates()
    assert gates["passed"] is True
    assert gates["gate"] == "INSTITUTIONAL_PORTFOLIO_INTELLIGENCE"
