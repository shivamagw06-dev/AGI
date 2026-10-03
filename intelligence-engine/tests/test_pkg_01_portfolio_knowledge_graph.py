"""PKG-01 / Phase 4.1 PO-01 — Portfolio Knowledge Graph tests."""

from __future__ import annotations

from institutional_decision import history as decision_history
from institutional_graph.production import reset_for_tests as reset_graphs
from institutional_portfolio.allocation import build_allocations
from institutional_portfolio.concentration import compute_concentration, concentration_risks
from institutional_portfolio.correlations import compute_correlations, estimate_pairwise_correlation
from institutional_portfolio.diagnostics import quality_gates, validate_graph
from institutional_portfolio.exposures import compute_exposures
from institutional_portfolio.fixtures import demo_holdings
from institutional_portfolio.portfolio_entities import HoldingRecord, InstitutionalPortfolio
from institutional_portfolio.portfolio_graph import build_portfolio_graph
from institutional_portfolio.production import (
    get_institutional_portfolio,
    get_portfolio_graph,
    health,
    reset_for_tests,
    soft_slice_mission_control,
)
from institutional_portfolio.schema import PKG_SPRINT, PKG_WORKSTREAM_ID


def setup_function(_fn=None):
    decision_history.reset_for_tests()
    reset_graphs()
    reset_for_tests()


def test_health():
    h = health()
    assert h["workstream_id"] == PKG_WORKSTREAM_ID
    assert h["sprint"] == PKG_SPRINT
    assert h["llm"] is False
    assert h["optimises"] is False
    assert h["scope"] == "single_portfolio"


def test_institutional_portfolio_object():
    holds = demo_holdings()
    g = build_portfolio_graph(
        portfolio_id="agi-core-equity",
        name="AGI Core Equity",
        holdings=holds,
        cash_weight=0.08,
    )
    ip = g.institutional_portfolio
    assert isinstance(ip, InstitutionalPortfolio)
    assert len(ip.holdings) == 4
    assert ip.allocations
    assert ip.exposures
    assert ip.cash_weight == 0.08
    d = ip.to_dict()
    assert d["holding_count"] == 4
    assert d["llm"] is False


def test_portfolio_graph_structure():
    holds = [
        HoldingRecord(
            ticker="AXISBANK",
            company="Axis Bank",
            weight=0.25,
            sector="Banking",
            industry="Private Banks",
            country="IN",
            recommendation="HOLD",
            confidence=80,
        ),
        HoldingRecord(
            ticker="HDFCBANK",
            company="HDFC Bank",
            weight=0.35,
            sector="Banking",
            industry="Private Banks",
            country="IN",
            recommendation="HOLD",
            confidence=81,
        ),
        HoldingRecord(
            ticker="ICICIBANK",
            company="ICICI Bank",
            weight=0.30,
            sector="Banking",
            industry="Private Banks",
            country="IN",
            recommendation="BUY",
            confidence=83,
        ),
    ]
    g = build_portfolio_graph(
        portfolio_id="test-book",
        name="Test Book",
        holdings=holds,
        cash_weight=0.10,
    )
    assert g.nodes_by_type("Portfolio")
    assert len(g.nodes_by_type("Company")) == 3
    assert len(g.nodes_by_type("Holding")) == 3
    assert g.nodes_by_type("Sector")
    assert g.nodes_by_type("Decision")
    assert g.relationships
    assert "Portfolio Graph" in g.lineage


def test_allocation_and_exposures():
    holds = demo_holdings()
    alloc = build_allocations(holds)
    assert alloc[0].weight >= alloc[-1].weight
    assert alloc[0].target_band in {"overweight", "core", "standard", "satellite"}
    exp = compute_exposures(holds)
    sectors = [e for e in exp if e.dimension == "sector"]
    assert sectors
    assert abs(sectors[0].weight - 0.92) < 1e-9


def test_correlations_deterministic():
    a = HoldingRecord(
        ticker="AXISBANK",
        company="Axis",
        weight=0.3,
        sector="Banking",
        industry="Private Banks",
        country="IN",
    )
    b = HoldingRecord(
        ticker="HDFCBANK",
        company="HDFC",
        weight=0.3,
        sector="Banking",
        industry="Private Banks",
        country="IN",
    )
    e1 = estimate_pairwise_correlation(a, b)
    e2 = estimate_pairwise_correlation(a, b)
    assert e1.score == e2.score
    assert e1.score >= 0.7  # same sector+industry+country
    edges = compute_correlations(demo_holdings())
    assert len(edges) == 6  # C(4,2)


def test_concentration_and_risks():
    holds = demo_holdings()
    conc = compute_concentration(holds)
    assert conc["number_of_holdings"] == 4
    assert conc["largest_position"]["ticker"] == "HDFCBANK"
    assert conc["hhi"] > 0
    exp = compute_exposures(holds)
    risks = concentration_risks(holds, exp)
    kinds = {r.kind for r in risks}
    assert "sector_concentration" in kinds


def test_quality_gates():
    g = build_portfolio_graph(
        portfolio_id="agi-core-equity",
        name="AGI Core Equity",
        holdings=demo_holdings(),
        cash_weight=0.08,
    )
    gates, errors = quality_gates(g)
    assert all(gates.values())
    assert errors == []
    assert validate_graph(g) == []


def test_production_demo_banks():
    result = get_portfolio_graph("agi-core-equity", rebuild=True)
    assert result["ok"] is True
    assert result["workstream_id"] == PKG_WORKSTREAM_ID
    tickers = {h["ticker"] for h in result["holdings"]}
    assert tickers == {"AXISBANK", "KOTAKBANK", "ICICIBANK", "HDFCBANK"}
    assert result["entity_count"] >= 10
    assert result["relationship_count"] >= 10
    assert result["portfolio"]["name"] == "AGI Core Equity"
    # Decisions enriched from IDS when fixtures exist
    assert any(h.get("recommendation") for h in result["holdings"])


def test_institutional_portfolio_api():
    pack = get_institutional_portfolio("agi-core-equity")
    assert pack["ok"] is True
    assert pack["portfolio"]["holdings"]
    assert pack["concentration"]
    assert pack["correlations"]["average"] is not None


def test_mission_control_soft_slice():
    get_portfolio_graph("agi-core-equity", rebuild=True)
    board = soft_slice_mission_control()
    assert board["portfolio_intelligence"] is True
    assert board["workstream_id"] == PKG_WORKSTREAM_ID
    assert board["holding_count"] >= 4
    assert board["entity_count"] >= 10
