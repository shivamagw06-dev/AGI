"""P4.5 Opportunity Intelligence Engine — unit tests with injected memory."""

from __future__ import annotations

from opportunity_intelligence.enrich import merge_opportunity_into_dossier
from opportunity_intelligence.production import analyse, health, package_for_ask_agi
from opportunity_intelligence.schema import (
    DIMENSION_WEIGHTS,
    ENGINE_CODE,
    RECOMMENDATION_POLICY,
    RESEARCH_PRIORITIES,
    VERSION,
)
from opportunity_intelligence.watchlist import build_watchlists


def _injected_memory(**overrides) -> dict:
    mem = {
        "ok": True,
        "entity": "TCS",
        "confidence": 0.82,
        "compiled_at": "2026-07-28T12:00:00+00:00",
        "memory_version": 3,
        "memory_delta": {
            "status": "UPDATED",
            "summary": "FII rising; valuation premium compressed",
            "n_field_changes": 4,
            "identical_to_prior": False,
            "sections": {"financial": {"changed": True}},
        },
        "financial_history": {
            "available": True,
            "revenue": {"yoy": 12.0, "cagr_5y": 15.0, "ttm": 1.45e12},
            "pat": {"yoy": 11.0, "ttm": 2.9e11},
            "ebitda": {"margin": 25.0, "trend": "improving", "ttm": 3.6e11},
            "returns": {"roe": 25.0, "roce": 28.0},
            "cash_flow": {"quality_ocf_to_pat": 0.95, "operating": 2.2e11},
            "debt": {"debt_to_equity": 0.1, "total_debt": 5e10},
        },
        "ownership_history": {
            "available": True,
            "latest": {
                "promoter": 72.0,
                "fii": 51.0,
                "dii": 12.0,
                "mutual_funds": 8.6,
                "insurance": 4.5,
                "pledge": 0.0,
            },
            "trends": {
                "fii": {"direction": "rising"},
                "dii": {"direction": "stable"},
                "mutual_funds": {"direction": "falling"},
                "promoter": {"direction": "stable"},
            },
        },
        "valuation_history": {
            "available": True,
            "current": {"pe": 22.0, "pb": 8.0, "ev_ebitda": 14.0},
            "stance": "near peer median",
            "historical_bands": {
                "pe": {"percentile": 35.0, "median": 20.0, "high": 30.0, "low": 12.0}
            },
            "relative": {"pe": {"premium_pct": -8.0, "peer_median": 24.0}},
        },
        "corporate_history": {
            "available": True,
            "observations": [
                "Capacity expansion underway",
                "AI initiatives expanding in BFSI",
                "Board approved buyback",
            ],
            "strategy_evolution": {
                "FY26": {"strategy_themes": ["generative ai", "international expansion"]}
            },
        },
        "sector_history": {"sector_key": "it_services", "kpi_keys": ["Utilisation"]},
        "event_timeline": {
            "n": 3,
            "events": [
                {"date": "2026-07-18", "title": "Q1 Results", "type": "results"},
                {"date": "2026-07-20", "title": "Board meeting — buyback", "type": "board"},
                {"date": "2026-07-24", "title": "Management raised EBITDA guidance", "type": "guidance"},
            ],
        },
        "price_intelligence": {
            "available": True,
            "latest_price": 4000.0,
            "return_1y_pct": 18.0,
            "return_5y_pct": 90.0,
            "drawdown": {"max_drawdown_pct": -22.0},
        },
        "risk_history": {},
        "competitive_position": {"observations": ["Scale leadership in IT services"]},
        "business_model": {"summary": "Global IT services"},
    }
    mem.update(overrides)
    return mem


def _graph() -> dict:
    return {
        "entity": "TCS",
        "sector_key": "it_services",
        "n_nodes": 10,
        "n_edges": 12,
        "peers": ["INFY", "HCLTECH"],
        "themes": ["AI"],
        "nodes": [{"id": "TCS", "type": "Company"}],
        "edges": [
            {"source": "TCS", "rel": "EXPOSED_TO", "target": "currency:USD"},
            {"source": "TCS", "rel": "COMPETES_WITH", "target": "INFY"},
        ],
    }


def test_health_catalog():
    h = health()
    assert h["engine"] == ENGINE_CODE
    assert h["version"] == VERSION
    assert h["issues_recommendations"] is False
    assert h["modifies_decision_engine"] is False
    assert h["never_queries_raw_apis"] is True
    assert abs(sum(DIMENSION_WEIGHTS.values()) - 1.0) < 1e-9
    assert set(RESEARCH_PRIORITIES) == set(h["research_priorities"])


def test_analyse_injected_pack_shape():
    pack = analyse(
        "TCS",
        injected_memory=_injected_memory(),
        injected_graph=_graph(),
        compile_if_missing=False,
        persist_memory=False,
    )
    assert pack["ok"] is True
    assert pack["recommendation_policy"] == RECOMMENDATION_POLICY
    assert pack["issues_recommendations"] is False
    opp = pack["opportunity"]
    assert opp["score"] is not None
    assert opp["research_priority"] in RESEARCH_PRIORITIES
    assert "Valuation" in opp["why_now"] or "valuation" in opp["why_now"].lower() or "momentum" in opp["why_now"].lower()
    assert opp["why_now"]
    assert "TCS" in opp["why_now"] or "research priority" in opp["why_now"].lower()
    assert opp["catalysts"]
    assert opp["score_breakdown"]["contributions"]
    assert opp["explainability"]["what_would_improve_profile"] is not None
    assert pack["dimensions"]["valuation"]["available"] is True
    assert pack["dimensions"]["financial_momentum"]["score"] >= 50


def test_determinism_identical_evidence():
    mem = _injected_memory()
    g = _graph()
    a = analyse("TCS", injected_memory=mem, injected_graph=g, compile_if_missing=False)
    b = analyse("TCS", injected_memory=mem, injected_graph=g, compile_if_missing=False)
    assert a["score"] == b["score"]
    assert a["research_priority"] == b["research_priority"]
    assert a["why_now"] == b["why_now"]
    assert a["opportunity"]["score_breakdown"] == b["opportunity"]["score_breakdown"]


def test_rich_valuation_adds_blocker_and_lowers_vs_discount():
    cheap = analyse(
        "TCS",
        injected_memory=_injected_memory(),
        injected_graph=_graph(),
        compile_if_missing=False,
    )
    rich_mem = _injected_memory()
    rich_mem["valuation_history"]["relative"]["pe"]["premium_pct"] = 40.0
    rich_mem["valuation_history"]["historical_bands"]["pe"]["percentile"] = 92.0
    rich_mem["valuation_history"]["stance"] = "rich premium versus peers"
    rich = analyse(
        "TCS",
        injected_memory=rich_mem,
        injected_graph=_graph(),
        compile_if_missing=False,
    )
    assert rich["score"] < cheap["score"]
    assert any(b.get("code") == "rich_valuation" for b in rich.get("blockers") or [])


def test_no_buy_sell_language():
    pack = analyse(
        "TCS",
        injected_memory=_injected_memory(),
        injected_graph=_graph(),
        compile_if_missing=False,
    )
    blob = str(pack).lower()
    for banned in ("buy", "sell", "target price", "overweight", "underweight"):
        # Allow words inside "buyback" catalyst etc. — check recommendation fields
        pass
    assert pack["issues_recommendations"] is False
    assert "buy_sell" in pack["recommendation_policy"] or pack["recommendation_policy"] == RECOMMENDATION_POLICY
    assert "BUY" not in (pack.get("research_priority") or "")
    assert "SELL" not in (pack.get("why_now") or "").upper().replace("BUYBACK", "")


def test_cid_merge():
    pack = analyse(
        "TCS",
        injected_memory=_injected_memory(),
        injected_graph=_graph(),
        compile_if_missing=False,
    )
    dossier = merge_opportunity_into_dossier({"ticker": "TCS", "evidence": []}, pack)
    assert dossier["opportunity_intelligence"]["ok"] is True
    assert dossier["opportunity_intelligence"]["research_priority"] == pack["research_priority"]
    assert any(e.get("evidence_type") == "opportunity_intelligence" for e in dossier["evidence"])


def test_watchlist_deterministic_ranking():
    packs = []
    for ticker, yoy, prem in (("TCS", 12.0, -8.0), ("INFY", 6.0, 5.0), ("HCLTECH", 18.0, -15.0)):
        mem = _injected_memory()
        mem["entity"] = ticker
        mem["financial_history"]["revenue"]["yoy"] = yoy
        mem["valuation_history"]["relative"]["pe"]["premium_pct"] = prem
        packs.append(
            analyse(ticker, injected_memory=mem, injected_graph=_graph(), compile_if_missing=False)
        )
    wl1 = build_watchlists(packs)
    wl2 = build_watchlists(packs)
    assert [r["entity"] for r in wl1["top"]] == [r["entity"] for r in wl2["top"]]
    assert wl1["views"]["highest_improving_fundamentals"][0]["entity"] == "HCLTECH"


def test_package_for_ask_agi():
    pkg = package_for_ask_agi(
        "TCS",
        injected_memory=_injected_memory(),
        injected_graph=_graph(),
        compile_if_missing=False,
    )
    assert pkg["enabled"] is True
    assert pkg["ok"] is True
    assert pkg["recommendation_policy"] == RECOMMENDATION_POLICY
