"""PRE-01 — Institutional Portfolio Risk Engine tests."""

from __future__ import annotations

from institutional_portfolio.portfolio_entities import (
    ExposureRecord,
    HoldingRecord,
    InstitutionalPortfolio,
)
from institutional_portfolio_risk.concentration import evaluate_concentration
from institutional_portfolio_risk.correlation import evaluate_correlation
from institutional_portfolio_risk.diagnostics import build_diagnostics
from institutional_portfolio_risk.liquidity import evaluate_liquidity
from institutional_portfolio_risk.production import (
    evaluate_portfolio_risk,
    get_portfolio_risk,
    health,
    reset_for_tests,
    soft_slice_mission_control,
)
from institutional_portfolio_risk.risk_engine import generate_portfolio_risk, risk_summary_for_cio
from institutional_portfolio_risk.schema import PRE_WORKSTREAM_ID
from institutional_portfolio_risk.stress import evaluate_stress
from institutional_portfolio_risk.validator import validate_risk


def _holding(ticker: str, weight: float, sector: str = "Banking", industry: str = "Private Banks", mv: float = 0.0):
    return HoldingRecord(
        ticker=ticker,
        company=ticker,
        weight=weight,
        market_value=mv or weight * 10_000_000,
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
    assert h["workstream_id"] == PRE_WORKSTREAM_ID
    assert h["llm"] is False
    assert h["monte_carlo"] is False
    assert h["authoritative_for_cio"] is True


def test_concentration_critical_on_concentrated_book():
    port = _portfolio(
        [
            _holding("HDFCBANK", 0.40),
            _holding("ICICIBANK", 0.30),
            _holding("AXISBANK", 0.22),
        ],
        cash=0.08,
    )
    conc = evaluate_concentration(port.holdings, port.exposures, cash_weight=port.cash_weight)
    assert conc.level in {"High", "Critical"}
    assert conc.sector_concentration >= 0.90
    assert conc.hhi > 0.25


def test_liquidity_cash_heavy_is_low():
    port = _portfolio(
        [
            _holding("HDFCBANK", 0.20, mv=2_000_000),
            _holding("TCS", 0.15, sector="Technology", industry="IT Services", mv=1_500_000),
        ],
        cash=0.65,
    )
    liq = evaluate_liquidity(port.holdings, cash_weight=port.cash_weight)
    assert liq.level == "Low"
    assert liq.cash_weight >= 0.60


def test_correlation_same_sector_elevated():
    holds = [
        _holding("HDFCBANK", 0.30),
        _holding("ICICIBANK", 0.30),
        _holding("AXISBANK", 0.25),
        _holding("KOTAKBANK", 0.15),
    ]
    corr = evaluate_correlation(holds)
    assert corr.average_correlation >= 0.70
    assert corr.level in {"High", "Critical"}
    assert corr.provider == "proxy_v1"


def test_stress_banking_book_negative_on_banking_stress():
    holds = [
        _holding("HDFCBANK", 0.28),
        _holding("ICICIBANK", 0.26),
        _holding("AXISBANK", 0.22),
        _holding("KOTAKBANK", 0.16),
    ]
    results = evaluate_stress(holds, cash_weight=0.08)
    by_key = {r.scenario: r for r in results}
    assert "banking_stress" in by_key
    assert by_key["banking_stress"].portfolio_impact_pct < -10
    assert "market_minus_10" in by_key
    assert abs(by_key["market_minus_10"].portfolio_impact_pct + 9.6) < 1.0  # dampened by cash


def test_validator_rejects_missing_diagnostics():
    port = _portfolio([_holding("HDFCBANK", 0.50), _holding("TCS", 0.42, sector="Technology")], cash=0.08)
    risk = generate_portfolio_risk(port)
    # diagnostics intentionally None
    assert risk.diagnostics is None
    v = validate_risk(risk, holding_count=2)
    assert not v.ok
    assert "Missing diagnostics" in v.errors


def test_generate_risk_scorecard_and_lineage():
    port = _portfolio(
        [
            _holding("HDFCBANK", 0.28),
            _holding("ICICIBANK", 0.26),
            _holding("AXISBANK", 0.22),
            _holding("KOTAKBANK", 0.16),
        ]
    )
    risk = generate_portfolio_risk(port)
    diag = build_diagnostics(risk, holding_count=4)
    from dataclasses import replace

    risk = replace(risk, diagnostics=diag)
    v = validate_risk(risk, holding_count=4)
    assert v.ok
    assert risk.overall_risk in {"Moderate", "High", "Critical"}
    assert risk.scorecard is not None
    assert "Portfolio" in risk.lineage
    assert "Risk Dimension" in risk.lineage
    summary = risk_summary_for_cio(risk)
    assert summary["authoritative"] is True
    assert summary["source"] == "PRE-01"
    assert summary["hhi"] == risk.hhi


def test_diversified_portfolio_lower_risk_than_concentrated():
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
            _holding("HDFCBANK", 0.18, sector="Banking"),
            _holding("TCS", 0.18, sector="Technology", industry="IT"),
            _holding("RELIANCE", 0.18, sector="Energy", industry="Oil"),
            _holding("INFY", 0.16, sector="Technology", industry="IT"),
            _holding("SBIN", 0.14, sector="Banking"),
        ],
        cash=0.16,
        pid="div",
    )
    r_c = generate_portfolio_risk(concentrated)
    r_d = generate_portfolio_risk(diversified)
    rank = {"Low": 0, "Moderate": 1, "High": 2, "Critical": 3}
    assert rank[r_c.overall_risk] >= rank[r_d.overall_risk]
    assert r_c.concentration.hhi > r_d.concentration.hhi


def test_production_default_portfolio():
    result = evaluate_portfolio_risk({"portfolio_id": "default"})
    assert result["ok"] is True
    assert result["workstream_id"] == PRE_WORKSTREAM_ID
    risk = result["risk"]
    assert risk["overall_risk"] in {"Moderate", "High", "Critical"}
    assert risk["concentration"]["top_sector"]
    assert len(risk["stress_results"]) >= 5
    assert risk["diagnostics"]
    cached = get_portfolio_risk("agi-core-equity", refresh=False)
    assert cached["ok"] is True
    board = soft_slice_mission_control()
    assert board["risk_center"] is True
    assert board["portfolio_risk"] is not None


def test_cio_consumes_pre01():
    """CIO-01 should attach portfolio_risk_id when PRE-01 is available."""
    from institutional_portfolio_decision.production import decide_portfolio, reset_for_tests as cio_reset

    cio_reset()
    reset_for_tests()
    result = decide_portfolio({"portfolio_id": "default"})
    assert result["ok"] is True
    d = result["decision"]
    assert d.get("consumes_pre01") is True
    assert d.get("portfolio_risk_id")
    assert d.get("overall_risk")
    assert d.get("portfolio_risk_summary", {}).get("source") == "PRE-01"
    assert "Portfolio Risk" in (d.get("lineage") or [])
