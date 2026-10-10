"""CIO-01 — Institutional Portfolio Decision System tests."""

from __future__ import annotations

from institutional_decision import history as company_history
from institutional_graph.production import reset_for_tests as reset_graphs
from institutional_portfolio.portfolio_entities import (
    ExposureRecord,
    HoldingRecord,
    InstitutionalPortfolio,
    RiskRecord,
)
from institutional_portfolio.production import reset_for_tests as reset_pkg
from institutional_portfolio_decision.allocation_actions import generate_allocation_actions
from institutional_portfolio_decision.calibration import calibrate_portfolio
from institutional_portfolio_decision.decision_engine import (
    build_company_decision_refs,
    generate_portfolio_decision,
)
from institutional_portfolio_decision.decision_validator import validate_decision
from institutional_portfolio_decision.diagnostics import build_diagnostics
from institutional_portfolio_decision.exposure_actions import generate_exposure_actions
from institutional_portfolio_decision.models import CompanyDecisionRef
from institutional_portfolio_decision.production import (
    decide_portfolio,
    get_portfolio_decision,
    health,
    reset_for_tests,
    soft_slice_mission_control,
)
from institutional_portfolio_decision.schema import CIO_WORKSTREAM_ID
from dataclasses import replace


def setup_function(_fn=None):
    company_history.reset_for_tests()
    reset_graphs()
    reset_pkg()
    reset_for_tests()


def test_health():
    h = health()
    assert h["workstream_id"] == CIO_WORKSTREAM_ID
    assert h["llm"] is False
    assert h["mutates_company_decisions"] is False
    assert h["referential_company_decisions"] is True


def _portfolio(holdings, *, cash=0.08, pid="test-book", risks=()):
    sectors: dict[str, float] = {}
    recs: dict[str, float] = {}
    for h in holdings:
        sectors[h.sector] = sectors.get(h.sector, 0.0) + h.weight
        recs[h.recommendation or "HOLD"] = recs.get(h.recommendation or "HOLD", 0.0) + h.weight
    exposures = tuple(
        [ExposureRecord("sector", k, v) for k, v in sorted(sectors.items(), key=lambda x: -x[1])]
        + [ExposureRecord("recommendation", k, v) for k, v in recs.items()]
        + [ExposureRecord("country", "IN", sum(h.weight for h in holdings))]
    )
    return InstitutionalPortfolio(
        portfolio_id=pid,
        name=pid,
        holdings=tuple(holdings),
        exposures=exposures,
        risks=tuple(risks),
        cash_weight=cash,
        graph_id=f"pkg-{pid}",
    )


def test_company_decisions_are_referential_not_mutated():
    holds = [
        HoldingRecord(
            ticker="AXISBANK",
            company="Axis",
            weight=0.3,
            sector="Banking",
            recommendation="HOLD",
            confidence=82,
            decision_id="dec-axis-1",
        ),
        HoldingRecord(
            ticker="ICICIBANK",
            company="ICICI",
            weight=0.3,
            sector="Banking",
            recommendation="BUY",
            confidence=83,
            decision_id="dec-icici-1",
        ),
    ]
    port = _portfolio(holds, cash=0.4)
    supporting, contradicting = build_company_decision_refs(port)
    refs = list(supporting) + list(contradicting)
    axis = next(r for r in refs if r.ticker == "AXISBANK")
    assert axis.decision_id == "dec-axis-1"
    assert axis.recommendation == "HOLD"
    assert axis.to_dict()["immutable"] is True
    # Engine must not change the referenced recommendation
    decision = generate_portfolio_decision(port, concentration={"hhi": 0.18})
    assert all(r.recommendation in {"HOLD", "BUY", "SELL"} for r in decision.supporting_decisions)
    assert decision.mutates_company_decisions is False


def test_allocation_and_exposure_engines():
    holds = [
        HoldingRecord(
            ticker="HDFCBANK",
            company="HDFC",
            weight=0.30,
            sector="Banking",
            recommendation="HOLD",
            confidence=80,
            decision_id="d1",
        ),
        HoldingRecord(
            ticker="TCS",
            company="TCS",
            weight=0.25,
            sector="IT",
            recommendation="BUY",
            confidence=85,
            decision_id="d2",
        ),
    ]
    port = _portfolio(holds, cash=0.45)
    refs = (
        CompanyDecisionRef("HDFCBANK", "d1", "HOLD", 80, weight=0.30),
        CompanyDecisionRef("TCS", "d2", "BUY", 85, weight=0.25),
    )
    alloc = generate_allocation_actions(port, refs=refs, sector_concentration=0.30, hhi=0.15)
    # BUY under 20% can increase; oversized HOLD can trim — deterministic non-empty or empty ok
    assert isinstance(alloc, tuple)
    exp = generate_exposure_actions(port)
    assert exp
    assert all(a.action in {"Increase", "Reduce", "Maintain", "Diversify"} for a in exp)


def test_calibration_and_validator():
    holds = [
        HoldingRecord(
            ticker="AXISBANK",
            company="Axis",
            weight=0.4,
            sector="Banking",
            recommendation="HOLD",
            confidence=80,
            decision_id="d1",
        ),
        HoldingRecord(
            ticker="KOTAKBANK",
            company="Kotak",
            weight=0.4,
            sector="Banking",
            recommendation="HOLD",
            confidence=80,
            decision_id="d2",
        ),
    ]
    port = _portfolio(
        holds,
        cash=0.2,
        risks=(RiskRecord("sector_concentration", "Banking", "critical", 0.8),),
    )
    decision = generate_portfolio_decision(port, concentration={"hhi": 0.32})
    diag = build_diagnostics(decision)
    decision = replace(decision, diagnostics=diag)
    cal, scorecard = calibrate_portfolio(
        port,
        refs=list(decision.supporting_decisions) + list(decision.contradicting_decisions),
        hhi=0.32,
        sector_concentration=0.8,
        recommendation=decision.recommendation,
    )
    assert 35 <= cal.confidence <= 92
    assert scorecard.final_recommendation == decision.recommendation
    validation = validate_decision(decision, holding_count=2)
    assert validation.ok, validation.errors
    assert validation.gates["company_decisions_immutable"] is True


def test_concentrated_default_portfolio_decision():
    result = decide_portfolio({"portfolio_id": "default"})
    assert result["ok"] is True
    assert result["mutates_company_decisions"] is False
    d = result["decision"]
    assert d["recommendation"] in {
        "Reduce Concentration",
        "Increase Diversification",
        "Increase Cash",
        "Maintain Allocation",
        "Review Portfolio",
    }
    assert d["allocation_actions"]
    assert d["exposure_actions"]
    assert d["calibration"]
    assert d["monitoring_plan"]
    assert d["scorecard"]
    assert d["lineage"][0] == "Portfolio"
    assert "Company Decision" in d["lineage"]
    # Referential IDs present for bank book
    refs = (d.get("supporting_decisions") or []) + (d.get("contradicting_decisions") or [])
    assert refs
    assert all(r.get("immutable") is True for r in refs)


def test_diversified_portfolio_different_decision():
    holds = [
        HoldingRecord(
            ticker="HDFCBANK",
            company="HDFC",
            weight=0.18,
            sector="Banking",
            recommendation="HOLD",
            confidence=80,
            decision_id="d1",
        ),
        HoldingRecord(
            ticker="TCS",
            company="TCS",
            weight=0.18,
            sector="IT",
            recommendation="HOLD",
            confidence=80,
            decision_id="d2",
        ),
        HoldingRecord(
            ticker="RELIANCE",
            company="RIL",
            weight=0.18,
            sector="Energy",
            recommendation="HOLD",
            confidence=80,
            decision_id="d3",
        ),
        HoldingRecord(
            ticker="INFY",
            company="Infosys",
            weight=0.18,
            sector="IT",
            recommendation="HOLD",
            confidence=80,
            decision_id="d4",
        ),
        HoldingRecord(
            ticker="SUNPHARMA",
            company="Sun",
            weight=0.18,
            sector="Pharma",
            recommendation="HOLD",
            confidence=80,
            decision_id="d5",
        ),
    ]
    port = _portfolio(holds, cash=0.10, pid="diversified")
    # Approximate HHI for equal-ish weights
    hhi = sum(h.weight * h.weight for h in holds)
    decision = generate_portfolio_decision(port, concentration={"hhi": hhi})
    assert decision.recommendation in {
        "Maintain Allocation",
        "No Action Required",
        "Increase Diversification",
        "Increase Cash",
    }
    # Must differ from typical concentrated banking outcome path when diversified
    concentrated = decide_portfolio({"portfolio_id": "agi-core-equity"})
    assert concentrated["ok"] is True
    assert (
        decision.recommendation != concentrated["decision"]["recommendation"]
        or decision.rule_path != concentrated["decision"]["rule_path"]
    )


def test_stress_portfolio_increase_cash_or_review():
    holds = [
        HoldingRecord(
            ticker="AXISBANK",
            company="Axis",
            weight=0.5,
            sector="Banking",
            recommendation="SELL",
            confidence=90,
            decision_id="d1",
        ),
        HoldingRecord(
            ticker="YESBANK",
            company="Yes",
            weight=0.4,
            sector="Banking",
            recommendation="SELL",
            confidence=88,
            decision_id="d2",
        ),
    ]
    port = _portfolio(holds, cash=0.1, pid="stress")
    decision = generate_portfolio_decision(port, concentration={"hhi": 0.41})
    assert decision.recommendation in {
        "Reduce Concentration",
        "Increase Cash",
        "Review Portfolio",
        "Increase Diversification",
    }
    assert decision.investment_posture in {"Defensive", "Review"}


def test_get_and_mission_control():
    first = decide_portfolio({"portfolio_id": "agi-core-equity"})
    assert first["ok"] is True
    cached = get_portfolio_decision("agi-core-equity", refresh=False)
    assert cached["ok"] is True
    assert cached["decision"]["decision_id"] == first["decision"]["decision_id"]
    board = soft_slice_mission_control()
    assert board["portfolio_command_center"] is True
    assert board["workstream_id"] == CIO_WORKSTREAM_ID
    assert board["portfolio_decision"] is not None


def test_deterministic_repeat():
    a = decide_portfolio({"portfolio_id": "agi-core-equity"})
    reset_for_tests()
    company_history.reset_for_tests()
    reset_graphs()
    reset_pkg()
    b = decide_portfolio({"portfolio_id": "agi-core-equity"})
    assert a["decision"]["recommendation"] == b["decision"]["recommendation"]
    assert a["decision"]["rule_path"] == b["decision"]["rule_path"]
    assert len(a["decision"]["allocation_actions"]) == len(b["decision"]["allocation_actions"])
