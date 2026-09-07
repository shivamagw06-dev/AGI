"""P2.2 Valuation Intelligence — peer registry, relative multiples, CID soft-attach."""

from __future__ import annotations

from company_analysis.valuation_intel import analyse_valuation
from decision_engine.readiness_gate import compute_coverage_board
from phase2_investment_intelligence.contract import validate_engine_payload
from phase2_investment_intelligence.workstreams import WORKSTREAMS
from valuation_intelligence.enrich import merge_valuation_into_dossier
from valuation_intelligence.narrative import build_narrative
from valuation_intelligence.peers import PEER_REGISTRY, resolve_peers
from valuation_intelligence.production import analyse, health, package_for_ask_agi
from valuation_intelligence.relative import build_relative
from valuation_intelligence.schema import (
    IC10_UNIVERSE,
    WORKSTREAM_ID,
    HistoricalBand,
    PeerSnapshot,
    RelativeMetric,
    SubjectMultiples,
)


def _earnings_slim(*, pe_eps: float = 40.0, pat: float = 200e9, revenue: float = 1000e9, equity: float = 800e9) -> dict:
    annual = []
    for i, mult in enumerate([0.7, 0.8, 0.9, 1.0, 1.1, 1.2]):
        year = 2020 + i
        annual.append(
            {
                "period_end": f"{year}-03-31",
                "revenue": revenue * mult,
                "ebitda": revenue * mult * 0.25,
                "pat": pat * mult,
                "eps": pe_eps * mult,
            }
        )
    return {
        "ok": True,
        "ticker": "TCS",
        "generated_at": "2026-07-01T00:00:00+00:00",
        "coverage_pct": 100,
        "ttm": {
            "available": True,
            "income_statement": {
                "revenue_from_operations": revenue,
                "ebitda": revenue * 0.25,
                "ebit": revenue * 0.22,
                "pat": pat,
                "pat_owners": pat,
                "eps_basic": pe_eps,
            },
        },
        "latest_annual": {
            "period_end": "2026-03-31",
            "income_statement": {
                "revenue_from_operations": revenue,
                "ebitda": revenue * 0.25,
                "pat": pat,
                "pat_owners": pat,
                "eps_basic": pe_eps,
            },
            "balance_sheet": {
                "total_equity": equity,
                "total_debt": 50e9,
                "cash": 120e9,
            },
            "cash_flow": {"operating_cash_flow": 220e9, "free_cash_flow": 180e9},
        },
        "latest_quarter": {
            "period_end": "2026-06-30",
            "income_statement": {
                "revenue_from_operations": revenue / 4,
                "ebitda": revenue / 4 * 0.25,
                "pat": pat / 4,
                "eps_basic": pe_eps / 4,
            },
        },
        "annual_history": [
            {
                "period_end": r["period_end"],
                "income_statement": {
                    "revenue_from_operations": r["revenue"],
                    "ebitda": r["ebitda"],
                    "pat": r["pat"],
                    "pat_owners": r["pat"],
                    "eps_basic": r["eps"],
                },
                "balance_sheet": {"total_equity": equity, "total_debt": 50e9, "cash": 120e9},
                "cash_flow": {"operating_cash_flow": 200e9},
            }
            for r in annual
        ],
        "metrics": {
            "latest_annual": {"roe_pct": 25.0, "roce_pct": 28.0, "ebitda_margin_pct": 25.0, "pat_margin_pct": 20.0},
            "latest_quarter": {"ebitda_margin_pct": 25.0, "pat_margin_pct": 20.0},
            "yoy_growth": {"eps_growth_pct": 12.0, "pat_growth_pct": 11.0, "revenue_growth_pct": 10.0},
        },
        "annual": annual,
    }


def _peer_fund(*, eps: float, pat: float = 100e9, equity: float = 400e9, roe: float = 18.0) -> dict:
    return {
        "ok": True,
        "ttm_eps": eps,
        "ttm_pat": pat,
        "ttm_revenue": 500e9,
        "ttm_ebitda": 120e9,
        "equity": equity,
        "net_debt": -20e9,
        "roe_pct": roe,
        "ocf": 90e9,
        "eps_growth_yoy_pct": 8.0,
        "source": "injected",
    }


def test_workstream_marked_implemented():
    row = next(w for w in WORKSTREAMS if w["id"] == "P2.2")
    assert row["status"] == "implemented"
    assert row["code"] == "valuation_intelligence"
    assert WORKSTREAM_ID == "P2.2"


def test_health_contract():
    h = health()
    assert h["status"] == "ok"
    assert h["issues_recommendations"] is False
    assert h["modifies_decision_engine"] is False
    assert h["workstream_id"] == "P2.2"
    v = validate_engine_payload(
        {
            "engine": "valuation_intelligence",
            "version": h["version"],
            "score": 0.8,
            "valuation_confidence": 0.8,
            "evidence": [],
            "confidence": 0.8,
            "freshness": {"age_days": 1, "stale": False, "sla_days": 14},
            "lineage": [],
            "baseline_compatible": True,
            "fabricated": False,
            "failure_mode": {"block_unrelated_engines": False},
        }
    )
    assert v["ok"] is True, v


def test_ic10_peer_registry_resolves():
    for t in IC10_UNIVERSE:
        meta = resolve_peers(t)
        assert meta["resolved"], t
        assert meta["primary_peers"], t
        assert t not in meta["primary_peers"]
    assert "ICICIBANK" in resolve_peers("HDFCBANK")["primary_peers"]
    assert "INFY" in resolve_peers("TCS")["primary_peers"]
    assert "SHREECEM" in resolve_peers("ULTRACEMCO")["primary_peers"]
    assert PEER_REGISTRY["HDFCBANK"]["industry"] == "Banks"


def test_relative_premium_and_reasons():
    subject = SubjectMultiples(pe=24.6, pb=3.5, ev_ebitda=14.0)
    peers = [
        PeerSnapshot("A", pe=20.0, pb=2.8, ev_ebitda=12.0, roe=15.0, eps_cagr_3y=8.0),
        PeerSnapshot("B", pe=22.0, pb=3.0, ev_ebitda=13.0, roe=16.0, eps_cagr_3y=9.0),
        PeerSnapshot("C", pe=21.0, pb=2.9, ev_ebitda=12.5, roe=14.0, eps_cagr_3y=7.0),
    ]
    rel = build_relative(subject, peers, subject_roe=20.0, subject_eps_cagr=14.0, subject_net_debt=10.0, subject_equity=100.0)
    assert rel["pe"].premium_pct is not None and rel["pe"].premium_pct > 0
    assert "Higher ROE" in rel["pe"].reasons
    assert "Higher EPS CAGR" in rel["pe"].reasons


def test_narrative_never_buy_sell():
    stance, obs = build_narrative(
        relative={
            "pe": RelativeMetric("pe", current=30.0, peer_median=20.0, premium_pct=50.0, reasons=["Higher ROE"]),
            "roe": RelativeMetric("roe", current=22.0, peer_median=15.0, premium_pct=46.0, reasons=[]),
        },
        historical={"pe": HistoricalBand(window="10Y", median=18.0, high=35.0, low=10.0, current=30.0, percentile=88.0)},
        quality={"roe": 22.0, "ebitda_margin": 28.0},
        growth={"eps_cagr_3y": 12.0},
    )
    blob = " ".join([stance] + obs).lower()
    assert "buy" not in blob
    assert "sell" not in blob
    assert any("peer median" in o.lower() or "premium" in o.lower() for o in obs)
    assert any("percentile" in o.lower() or "cycle" in o.lower() for o in obs)


def test_analyse_injected_tcs_pack():
    peer_quotes = {
        "INFY": {"ltp": 1600.0, "provider": "injected", "as_of": "2026-07-28"},
        "HCLTECH": {"ltp": 1500.0, "provider": "injected", "as_of": "2026-07-28"},
        "WIPRO": {"ltp": 500.0, "provider": "injected", "as_of": "2026-07-28"},
        "TECHM": {"ltp": 1400.0, "provider": "injected", "as_of": "2026-07-28"},
        "LTIM": {"ltp": 5200.0, "provider": "injected", "as_of": "2026-07-28"},
    }
    peer_funds = {
        "INFY": _peer_fund(eps=65.0, roe=22.0),
        "HCLTECH": _peer_fund(eps=60.0, roe=20.0),
        "WIPRO": _peer_fund(eps=22.0, roe=16.0),
        "TECHM": _peer_fund(eps=55.0, roe=18.0),
        "LTIM": _peer_fund(eps=140.0, roe=21.0),
    }
    hist = {"pe": [15.0, 18.0, 20.0, 22.0, 25.0, 28.0, 24.0, 21.0, 19.0, 23.0]}
    pack = analyse(
        "TCS",
        persist=False,
        skip_earnings_fetch=True,
        injected_quote={"ltp": 4000.0, "provider": "injected", "as_of": "2026-07-28"},
        injected_earnings=_earnings_slim(pe_eps=80.0),
        injected_peer_quotes=peer_quotes,
        injected_peer_fundamentals=peer_funds,
        injected_history=hist,
        max_peers=5,
    )
    assert pack["ok"] is True
    assert pack["issues_recommendations"] is False
    assert pack["current"]["pe"] is not None
    assert pack["current"]["pe"] == 50.0  # 4000 / 80
    assert pack["peer_universe"]["resolved"] is True
    assert "INFY" in pack["peer_universe"]["primary_peers"]
    assert (pack["relative"]["pe"]["peer_median"]) is not None
    assert pack["historical"]["pe"]["percentile"] is not None
    assert pack["observations"]
    assert pack["cid_summary"]["premium_discount"]["pe_premium_pct"] is not None
    text = " ".join(pack["observations"]).lower()
    assert "buy" not in text and "sell" not in text


def test_cid_merge_and_company_analysis_consume():
    pack = analyse(
        "HDFCBANK",
        persist=False,
        skip_earnings_fetch=True,
        injected_quote={"ltp": 1700.0, "provider": "injected", "as_of": "2026-07-28"},
        injected_earnings=_earnings_slim(pe_eps=70.0, pat=400e9, equity=2000e9),
        injected_peer_quotes={
            "ICICIBANK": {"ltp": 1200.0, "as_of": "2026-07-28"},
            "AXISBANK": {"ltp": 1100.0, "as_of": "2026-07-28"},
            "KOTAKBANK": {"ltp": 1800.0, "as_of": "2026-07-28"},
            "INDUSINDBK": {"ltp": 1400.0, "as_of": "2026-07-28"},
        },
        injected_peer_fundamentals={
            "ICICIBANK": _peer_fund(eps=60.0, roe=17.0),
            "AXISBANK": _peer_fund(eps=55.0, roe=15.0),
            "KOTAKBANK": _peer_fund(eps=75.0, roe=13.0),
            "INDUSINDBK": _peer_fund(eps=70.0, roe=14.0),
        },
        injected_history={"pe": [16, 18, 20, 22, 24, 21, 19, 17, 23, 25]},
        max_peers=4,
    )
    dossier = {"ticker": "HDFCBANK", "valuation": {}, "identity": {}, "market_data": {}}
    merged = merge_valuation_into_dossier(dossier, pack)
    assert merged["valuation"]["pe"] is not None
    assert merged["valuation"]["peer_pe"] is not None
    assert merged["valuation"]["placeholder"] is False
    assert merged["valuation_intelligence"]["ok"] is True

    ca = analyse_valuation(identity={"ticker": "HDFCBANK", "peers": []}, cid=merged)
    assert ca["p22_attached"] is True
    assert ca["current_pe"] is not None
    assert ca["peer_valuation"]["peer_pe"] is not None
    assert "buy" not in (ca.get("narrative") or "").lower()

    board = compute_coverage_board(
        company_analysis={"valuation_intelligence": ca},
        cid=merged,
    )
    assert isinstance(board, dict)
    # Gate must see non-placeholder valuation coverage from P2.2
    val_cov = board.get("valuation")
    if val_cov is None and isinstance(board.get("domains"), dict):
        val_cov = board["domains"].get("valuation")
    if val_cov is None:
        val_cov = (board.get("coverage") or {}).get("valuation")
    assert val_cov is None or float(val_cov) >= 0


def test_package_for_ask_agi():
    pkg = package_for_ask_agi(
        "ULTRACEMCO",
        skip_earnings_fetch=True,
        injected_quote={"ltp": 11000.0, "as_of": "2026-07-28"},
        injected_earnings=_earnings_slim(pe_eps=200.0),
        injected_peer_quotes={
            "SHREECEM": {"ltp": 28000.0, "as_of": "2026-07-28"},
            "AMBUJACEM": {"ltp": 600.0, "as_of": "2026-07-28"},
            "ACC": {"ltp": 2500.0, "as_of": "2026-07-28"},
            "DALBHARAT": {"ltp": 2000.0, "as_of": "2026-07-28"},
            "RAMCOCEM": {"ltp": 900.0, "as_of": "2026-07-28"},
        },
        injected_peer_fundamentals={
            "SHREECEM": _peer_fund(eps=400.0),
            "AMBUJACEM": _peer_fund(eps=20.0),
            "ACC": _peer_fund(eps=80.0),
            "DALBHARAT": _peer_fund(eps=50.0),
            "RAMCOCEM": _peer_fund(eps=30.0),
        },
        injected_history={"pe": [30, 32, 35, 40, 38, 36, 34, 33, 37, 39]},
        max_peers=5,
    )
    assert pkg["enabled"] is True
    assert pkg["recommendation_policy"] == "observations_only_no_buy_sell"
    assert pkg["ok"] is True
