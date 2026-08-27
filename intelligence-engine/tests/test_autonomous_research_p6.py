"""P6 Autonomous Research Office — unit tests with injected packs."""

from __future__ import annotations

from autonomous_research.coverage import build_coverage
from autonomous_research.generator import generate_research_pack
from autonomous_research.planner import build_research_plan
from autonomous_research.production import health, run_office
from autonomous_research.publications import build_publications
from autonomous_research.qa import run_qa
from autonomous_research.schema import ENGINE_CODE, RECOMMENDATION_POLICY, VERSION
from autonomous_research.themes import build_theme_intelligence
from autonomous_research.watchlists import build_watchlists


def _pack(
    ticker: str,
    *,
    score: float,
    priority: str,
    delta_status: str = "UNCHANGED",
    delta_n: int = 0,
    sector: str = "it_services",
    themes: list | None = None,
    blockers: list | None = None,
) -> dict:
    entity = "TMPV" if ticker == "TATAMOTORS" else ticker
    return {
        "ok": True,
        "entity": entity,
        "display": ticker,
        "memory": {
            "ok": True,
            "entity": entity,
            "memory_version": 5,
            "compiled_at": "2026-07-28T12:00:00+00:00",
            "sector_history": {"sector_key": sector},
            "financial_history": {
                "available": True,
                "revenue": {"yoy": 12.0},
                "pat": {"yoy": 10.0},
            },
            "ownership_history": {
                "available": True,
                "latest": {"fii": 50.0, "promoter": 70.0},
                "trends": {"fii": {"direction": "rising"}},
            },
            "valuation_history": {"stance": "near peer median", "available": True},
            "memory_delta": {
                "status": delta_status,
                "summary": "delta" if delta_status != "UNCHANGED" else "noop",
                "n_field_changes": delta_n,
            },
        },
        "memory_delta": {
            "status": delta_status,
            "summary": "delta" if delta_status != "UNCHANGED" else "noop",
            "n_field_changes": delta_n,
        },
        "knowledge_graph": {
            "n_nodes": 8,
            "n_edges": 10,
            "peers": ["INFY"],
            "themes": themes or (["AI"] if sector == "it_services" else []),
            "sector_key": sector,
        },
        "opportunity": {
            "ok": True,
            "entity": entity,
            "display": ticker,
            "score": score,
            "confidence": 72.0,
            "research_priority": priority,
            "why_now": f"{ticker} deserves attention due to score {score}",
            "blockers": blockers or [],
            "catalysts": [
                {
                    "name": "Quarterly results",
                    "importance": "High",
                    "expected_window": "near_term",
                    "confidence": 0.8,
                    "evidence": {"source": "event_timeline"},
                }
            ],
            "freshness": {"memory_version": 5},
            "dimensions": {"valuation": {"signals": ["Peer discount"], "score": 60}},
            "opportunity": {
                "knowledge_delta": {
                    "status": delta_status,
                    "summary": "delta" if delta_status != "UNCHANGED" else "noop",
                    "n_field_changes": delta_n,
                }
            },
        },
    }


def _packs() -> list[dict]:
    return [
        _pack("TCS", score=70.0, priority="High", delta_status="UPDATED", delta_n=3),
        _pack("HDFCBANK", score=45.0, priority="Low", sector="banks"),
        _pack(
            "HAL",
            score=82.0,
            priority="Critical",
            sector="defence",
            themes=["Defence"],
            blockers=[{"severity": "High", "title": "Rich valuation", "code": "rich_valuation"}],
        ),
        _pack("NTPC", score=61.0, priority="Medium", sector="power", themes=[]),
    ]


def test_health_aro_not_engine():
    h = health()
    assert h["engine"] == ENGINE_CODE
    assert h["version"] == VERSION
    assert h["not_an_intelligence_engine"] is True
    assert h["does_not_make_investment_decisions"] is True
    assert h["issues_recommendations"] is False
    assert h["modifies_decision_engine"] is False


def test_planner_deterministic():
    packs = _packs()
    a = build_research_plan(packs, holdings=["TCS", "HAL"])
    b = build_research_plan(packs, holdings=["TCS", "HAL"])
    assert [p["entity"] for p in a["plans"]] == [p["entity"] for p in b["plans"]]
    assert a["plans"][0]["research_type"] in {
        "company_update",
        "earnings_review",
        "event_analysis",
        "risk_update",
        "earnings_preview",
    }
    assert a["plans"][0]["evidence"]["opportunity_score"] is not None


def test_generator_evidence_backed_no_buy_sell():
    draft = generate_research_pack(_packs()[0], research_type="company_update")
    assert draft["ok"] is True
    assert draft["draft"] is True
    assert draft["approved_for_publication"] is False
    assert draft["issues_recommendations"] is False
    assert len(draft["sections"]) >= 5
    assert all(s.get("evidence_backed") for s in draft["sections"])
    assert "BUY" not in draft["disclaimer"].upper() or "not an investment" in draft["disclaimer"].lower()


def test_qa_blocks_incomplete():
    good = generate_research_pack(_packs()[0])
    qa_ok = run_qa(good, company_pack=_packs()[0])
    assert qa_ok["qa_pass"] is True
    assert qa_ok["approved"] is False  # still needs governance

    bad = {
        "ok": True,
        "sections": [{"id": "x", "evidence_backed": False, "evidence": []}],
        "citations": [],
        "issues_recommendations": False,
    }
    qa_bad = run_qa(bad, company_pack=_packs()[0])
    assert qa_bad["blocked"] is True


def test_watchlists_and_themes():
    packs = _packs()
    wl = build_watchlists(packs, holdings=["HAL", "TCS"])
    assert wl["counts"]["high_priority"] >= 1
    assert wl["counts"]["portfolio_critical"] >= 1
    th = build_theme_intelligence(packs)
    assert th["active_n"] >= 1
    names = [t["theme"] for t in th["themes"] if t["n"] > 0]
    assert "AI" in names or "Defence" in names or "Banking" in names


def test_publications_require_governance():
    packs = _packs()
    draft = generate_research_pack(packs[0])
    qa = {"results": [{"entity": packs[0]["entity"], "company": "TCS", "qa": run_qa(draft, company_pack=packs[0])}]}
    pubs = build_publications(drafts=[draft], qa_results=qa, governance_approved_ids=[])
    assert pubs["n"] >= 1
    assert all(not p.get("governance_approved") for p in pubs["publications"] if p.get("pub_type") == "research_note")


def test_coverage_flags_stale():
    packs = _packs()
    cov = build_coverage(packs, drafts=[])
    assert cov["coverage"]["total_companies"] == 4
    # High priority without draft should appear in upcoming or stale
    assert cov["coverage"]["upcoming_updates"] or cov["coverage"]["stale_reports"]


def test_run_office_injected():
    packs = _packs()
    injected = {p["display"]: p for p in packs}
    office = run_office(
        universe=["TCS", "HDFCBANK", "HAL", "NTPC"],
        holdings=["TCS", "HAL"],
        injected_by_ticker=injected,
        draft_limit=3,
    )
    assert office["ok_n"] == 4
    assert office["recommendation_policy"] == RECOMMENDATION_POLICY
    assert office["issues_recommendations"] is False
    assert office["planner"]["n"] >= 1
    assert office["drafts"]["n"] >= 1
    assert office["qa"]["n"] >= 1
