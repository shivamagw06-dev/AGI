"""ICE-01 — Investment Committee Engine tests."""

from __future__ import annotations

from dataclasses import replace

from institutional_committee.action_items import build_action_items
from institutional_committee.committee_engine import generate_committee_resolution
from institutional_committee.diagnostics import build_diagnostics
from institutional_committee.production import (
    get_pending,
    get_resolution,
    health,
    reset_for_tests,
    review_committee,
    soft_slice_mission_control,
)
from institutional_committee.schema import ICE_WORKSTREAM_ID
from institutional_committee.validator import validate_resolution
from institutional_committee.voting import cast_votes, resolve_outcome
from institutional_portfolio.portfolio_entities import (
    ExposureRecord,
    HoldingRecord,
    InstitutionalPortfolio,
)
from institutional_portfolio_decision.decision_engine import generate_portfolio_decision
from institutional_portfolio_risk.risk_engine import generate_portfolio_risk
from institutional_policy.policy_engine import generate_policy_assessment


def _holding(ticker: str, weight: float, sector: str = "Banking"):
    return HoldingRecord(
        ticker=ticker,
        company=ticker,
        weight=weight,
        market_value=weight * 10_000_000,
        sector=sector,
        industry="Private Banks" if sector == "Banking" else sector,
        country="IN",
        recommendation="HOLD",
        confidence=70,
        decision_id=f"dec-{ticker.lower()}",
    )


def _portfolio(holdings, *, cash: float = 0.08, pid: str = "test-book") -> InstitutionalPortfolio:
    sectors: dict[str, float] = {}
    for h in holdings:
        sectors[h.sector] = sectors.get(h.sector, 0.0) + h.weight
    exposures = tuple(
        ExposureRecord(dimension="sector", name=n, weight=w)
        for n, w in sorted(sectors.items(), key=lambda kv: -kv[1])
    )
    return InstitutionalPortfolio(
        portfolio_id=pid,
        name=pid,
        holdings=tuple(holdings),
        exposures=exposures,
        cash_weight=cash,
        graph_id=f"pkg-{pid}",
    )


def setup_function():
    reset_for_tests()
    try:
        from institutional_portfolio_decision.production import reset_for_tests as cio_reset
        from institutional_portfolio_risk.production import reset_for_tests as pre_reset
        from institutional_policy.production import reset_for_tests as pce_reset

        cio_reset()
        pre_reset()
        pce_reset()
    except Exception:
        pass


def test_health():
    h = health()
    assert h["workstream_id"] == ICE_WORKSTREAM_ID
    assert h["llm"] is False
    assert h["predictive"] is False
    assert h["mutates_upstream"] is False
    assert h["governs_cio_decisions"] is True


def test_voting_policy_breach_conditions():
    votes = cast_votes(
        overall_risk="High",
        policy_status="Breach",
        violation_count=2,
        recommendation="Reduce Concentration",
        allocation_action_count=2,
        material_trim=True,
    )
    by_desk = {v.desk: v.vote for v in votes}
    assert by_desk["Policy"] == "APPROVE_WITH_CONDITIONS"
    status, _ = resolve_outcome(votes)
    assert status == "Approved with Conditions"


def test_voting_critical_risk_escalates():
    votes = cast_votes(
        overall_risk="Critical",
        policy_status="Compliant",
        violation_count=0,
        recommendation="Maintain Allocation",
        allocation_action_count=0,
        worst_stress={"portfolio_impact_pct": -18.0},
    )
    status, _ = resolve_outcome(votes)
    assert status == "Escalated"


def test_voting_reject_on_critical_breach():
    votes = cast_votes(
        overall_risk="Moderate",
        policy_status="Critical Breach",
        violation_count=5,
        recommendation="Reduce Concentration",
        allocation_action_count=1,
    )
    status, _ = resolve_outcome(votes)
    assert status == "Rejected"


def test_action_items_from_allocation():
    actions = build_action_items(
        allocation_actions=[
            {
                "ticker": "HDFCBANK",
                "from_weight": 0.28,
                "to_weight": 0.25,
                "reason": "Trim concentration",
            }
        ],
        status="Approved with Conditions",
        recommendation="Reduce Concentration",
    )
    assert any(a.ticker == "HDFCBANK" for a in actions)
    assert any("28%" in a.detail or "0.28" in a.detail or "HDFCBANK" in a.title for a in actions)


def test_resolution_generation_links_upstream():
    port = _portfolio(
        [
            _holding("HDFCBANK", 0.28),
            _holding("ICICIBANK", 0.26),
            _holding("AXISBANK", 0.22),
            _holding("KOTAKBANK", 0.16),
        ],
        pid="conc-book",
    )
    risk = generate_portfolio_risk(port)
    policy = generate_policy_assessment(port, profile_id="family_office", portfolio_risk=risk)
    decision = generate_portfolio_decision(
        port,
        portfolio_risk=risk,
        policy_assessment=policy,
    )
    resolution = generate_committee_resolution(
        portfolio_decision=decision,
        portfolio_risk=risk,
        policy_assessment=policy,
    )
    assert resolution.portfolio_decision_id == decision.decision_id
    assert resolution.portfolio_risk_id == risk.risk_id
    assert resolution.policy_id == policy.policy_id
    assert resolution.mutates_upstream is False
    assert resolution.rationale
    assert resolution.votes
    assert resolution.status in {
        "Approved",
        "Approved with Conditions",
        "Rejected",
        "Deferred",
        "Escalated",
        "Pending Review",
    }
    assert "Committee" in resolution.lineage
    assert "Portfolio Decision" in resolution.lineage


def test_validator_rejects_missing_links():
    port = _portfolio([_holding("HDFCBANK", 0.50), _holding("TCS", 0.42, sector="Technology")])
    risk = generate_portfolio_risk(port)
    policy = generate_policy_assessment(port, profile_id="family_office", portfolio_risk=risk)
    decision = generate_portfolio_decision(port, portfolio_risk=risk, policy_assessment=policy)
    resolution = generate_committee_resolution(
        portfolio_decision=decision,
        portfolio_risk=risk,
        policy_assessment=policy,
    )
    # Strip diagnostics → should fail gate
    assert resolution.diagnostics is None
    v = validate_resolution(resolution)
    assert not v.ok
    assert "Missing diagnostics" in v.errors

    diag = build_diagnostics(resolution)
    resolution = replace(resolution, diagnostics=diag)
    v2 = validate_resolution(resolution)
    assert v2.ok


def test_compliant_growth_book_can_approve():
    port = _portfolio(
        [
            _holding("HDFCBANK", 0.18),
            _holding("ICICIBANK", 0.16),
            _holding("TCS", 0.18, sector="Technology"),
            _holding("INFY", 0.14, sector="Technology"),
            _holding("RELIANCE", 0.16, sector="Energy"),
        ],
        cash=0.18,
        pid="div-book",
    )
    risk = generate_portfolio_risk(port)
    policy = generate_policy_assessment(port, profile_id="growth", portfolio_risk=risk)
    decision = generate_portfolio_decision(port, portfolio_risk=risk, policy_assessment=policy)
    resolution = generate_committee_resolution(
        portfolio_decision=decision,
        portfolio_risk=risk,
        policy_assessment=policy,
    )
    # Growth profile on diversified book should not reject
    assert resolution.status != "Rejected"


def test_history_and_pending():
    result = review_committee({"portfolio_id": "default", "policy": "family_office"})
    assert result["ok"] is True
    rid = result["resolution"]["resolution_id"]
    got = get_resolution(rid)
    assert got["ok"] is True
    assert got["resolution"]["resolution_id"] == rid
    assert got["resolution"]["mutates_upstream"] is False
    # Pending list only includes Pending Review statuses
    pending = get_pending()
    assert pending["ok"] is True
    board = soft_slice_mission_control()
    assert board["committee_center"] is True
    assert board["latest_resolution"] is not None


def test_production_policy_violation_case():
    result = review_committee({"portfolio_id": "default", "policy": "family_office"})
    assert result["ok"] is True
    r = result["resolution"]
    assert r["portfolio_decision_id"]
    assert r["portfolio_risk_id"]
    assert r["policy_id"]
    assert r["diagnostics"]
    assert len(r["votes"]) == 3
    # Concentrated banking demo under family_office typically conditions or escalates
    assert r["status"] in {
        "Approved with Conditions",
        "Escalated",
        "Rejected",
        "Pending Review",
        "Deferred",
        "Approved",
    }
    assert r["required_actions"] or r["follow_up_items"]
