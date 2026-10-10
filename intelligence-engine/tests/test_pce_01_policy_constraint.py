"""PCE-01 — Institutional Policy & Constraint Engine tests."""

from __future__ import annotations

from dataclasses import replace

from institutional_portfolio.portfolio_entities import (
    ExposureRecord,
    HoldingRecord,
    InstitutionalPortfolio,
)
from institutional_portfolio_risk.risk_engine import generate_portfolio_risk
from institutional_policy.constraints import evaluate_constraint, evaluate_all_constraints
from institutional_policy.diagnostics import build_diagnostics
from institutional_policy.mandates import get_mandate
from institutional_policy.policy_engine import generate_policy_assessment, policy_summary_for_cio
from institutional_policy.production import (
    check_policy,
    get_policy_assessment,
    health,
    reset_for_tests,
    soft_slice_mission_control,
)
from institutional_policy.schema import PCE_WORKSTREAM_ID
from institutional_policy.validator import validate_assessment


def _holding(ticker: str, weight: float, sector: str = "Banking", industry: str = "Private Banks"):
    return HoldingRecord(
        ticker=ticker,
        company=ticker,
        weight=weight,
        market_value=weight * 10_000_000,
        sector=sector,
        industry=industry,
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


def test_health():
    h = health()
    assert h["workstream_id"] == PCE_WORKSTREAM_ID
    assert h["llm"] is False
    assert h["governs_allocations"] is True
    assert any(p["profile_id"] == "family_office" for p in h["profiles"])


def test_position_limit_violation():
    port = _portfolio([_holding("HDFCBANK", 0.28), _holding("ICICIBANK", 0.26), _holding("AXISBANK", 0.22), _holding("KOTAKBANK", 0.16)])
    mandate = get_mandate("family_office")
    c = next(x for x in mandate.constraints if x.constraint_id == "pos_max_holding")
    result = evaluate_constraint(c, port)
    assert result.status == "Violation"
    assert result.actual >= 0.28
    assert "Reduce HDFCBANK" in result.action
    assert "25%" in result.action or "0.25" in result.action or "25" in result.action


def test_cash_limit_pass():
    port = _portfolio([_holding("HDFCBANK", 0.50), _holding("TCS", 0.42, sector="Technology")], cash=0.08)
    mandate = get_mandate("family_office")
    c = next(x for x in mandate.constraints if x.constraint_id == "cash_min")
    result = evaluate_constraint(c, port)
    assert result.status == "Pass"
    assert result.actual >= 0.05


def test_sector_limit_financials():
    port = _portfolio(
        [
            _holding("HDFCBANK", 0.28),
            _holding("ICICIBANK", 0.26),
            _holding("AXISBANK", 0.22),
            _holding("KOTAKBANK", 0.16),
        ],
        cash=0.08,
    )
    mandate = get_mandate("family_office")
    c = next(x for x in mandate.constraints if x.constraint_id == "sec_max_financials")
    result = evaluate_constraint(c, port)
    assert result.status == "Violation"
    assert result.actual >= 0.90


def test_liquidity_uses_pre01():
    port = _portfolio(
        [
            _holding("HDFCBANK", 0.28),
            _holding("ICICIBANK", 0.26),
            _holding("AXISBANK", 0.22),
            _holding("KOTAKBANK", 0.16),
        ]
    )
    risk = generate_portfolio_risk(port)
    mandate = get_mandate("conservative")
    results = evaluate_all_constraints(mandate, port, risk)
    by_id = {r.constraint_id: r for r in results}
    assert "liq_max_exit_days" in by_id
    assert by_id["liq_max_illiquid"].actual == risk.liquidity.illiquid_weight


def test_validator_rejects_missing_diagnostics():
    port = _portfolio([_holding("HDFCBANK", 0.40), _holding("ICICIBANK", 0.35), _holding("AXISBANK", 0.17)])
    assessment = generate_policy_assessment(port, profile_id="family_office")
    assert assessment.diagnostics is None
    v = validate_assessment(assessment, holding_count=3)
    assert not v.ok
    assert "Missing diagnostics" in v.errors


def test_concentrated_portfolio_breach():
    port = _portfolio(
        [
            _holding("HDFCBANK", 0.28),
            _holding("ICICIBANK", 0.26),
            _holding("AXISBANK", 0.22),
            _holding("KOTAKBANK", 0.16),
        ],
        cash=0.08,
        pid="conc",
    )
    risk = generate_portfolio_risk(port)
    assessment = generate_policy_assessment(port, profile_id="family_office", portfolio_risk=risk)
    diag = build_diagnostics(assessment, holding_count=4)
    assessment = replace(assessment, diagnostics=diag)
    v = validate_assessment(assessment, holding_count=4)
    assert v.ok
    assert assessment.has_breach
    assert assessment.overall_status in {"Breach", "Critical Breach"}
    assert any(x.constraint_id == "pos_max_holding" for x in assessment.failed_constraints)
    assert assessment.required_actions
    summary = policy_summary_for_cio(assessment)
    assert summary["source"] == "PCE-01"
    assert summary["has_breach"] is True


def test_diversified_portfolio_better_compliance():
    concentrated = _portfolio(
        [
            _holding("HDFCBANK", 0.40),
            _holding("ICICIBANK", 0.35),
            _holding("AXISBANK", 0.17),
        ],
        cash=0.08,
        pid="conc",
    )
    diversified = _portfolio(
        [
            _holding("HDFCBANK", 0.12, sector="Banking"),
            _holding("ICICIBANK", 0.10, sector="Banking"),
            _holding("TCS", 0.12, sector="Technology", industry="IT"),
            _holding("INFY", 0.10, sector="Technology", industry="IT"),
            _holding("RELIANCE", 0.12, sector="Energy", industry="Oil"),
            _holding("SBIN", 0.10, sector="Banking"),
            _holding("AXISBANK", 0.08, sector="Banking"),
            _holding("KOTAKBANK", 0.08, sector="Banking"),
        ],
        cash=0.18,
        pid="div",
    )
    # Use growth profile so diversified can pass more constraints
    a_c = generate_policy_assessment(concentrated, profile_id="growth")
    a_d = generate_policy_assessment(diversified, profile_id="growth")
    assert a_d.compliance_score >= a_c.compliance_score
    assert len(a_d.failed_constraints) <= len(a_c.failed_constraints)


def test_cash_heavy_portfolio_cash_max():
    port = _portfolio(
        [_holding("HDFCBANK", 0.20), _holding("TCS", 0.15, sector="Technology")],
        cash=0.65,
        pid="cash",
    )
    assessment = generate_policy_assessment(port, profile_id="family_office")
    failed_ids = {c.constraint_id for c in assessment.failed_constraints}
    assert "cash_max" in failed_ids


def test_production_default_policy_check():
    result = check_policy({"portfolio_id": "default", "policy": "family_office"})
    assert result["ok"] is True
    assert result["workstream_id"] == PCE_WORKSTREAM_ID
    a = result["assessment"]
    assert a["overall_status"] in {"Breach", "Critical Breach", "Warning", "Compliant"}
    assert a["diagnostics"]
    assert a["mandate"]
    cached = get_policy_assessment("agi-core-equity", profile_id="family_office", refresh=False)
    assert cached["ok"] is True
    board = soft_slice_mission_control()
    assert board["policy_center"] is True
    assert board["policy_assessment"] is not None


def test_cio_consumes_pce01():
    from institutional_portfolio_decision.production import (
        decide_portfolio,
        reset_for_tests as cio_reset,
    )
    from institutional_portfolio_risk.production import reset_for_tests as pre_reset

    cio_reset()
    pre_reset()
    reset_for_tests()
    result = decide_portfolio({"portfolio_id": "default", "policy": "family_office"})
    assert result["ok"] is True
    d = result["decision"]
    assert d.get("consumes_pce01") is True
    assert d.get("policy_id")
    assert d.get("policy_status")
    assert d.get("policy_summary", {}).get("source") == "PCE-01"
    assert "Policy Constraint" in (d.get("lineage") or [])
    # Concentrated banking demo should surface policy-driven reduce concentration
    assert d.get("recommendation") in {
        "Reduce Concentration",
        "Increase Diversification",
        "Increase Cash",
        "Review Portfolio",
    }
    assert str(d.get("rule_path") or "").startswith("policy:")
