"""P5 Investment Operations Layer — unit tests with injected company packs."""

from __future__ import annotations

from investment_operations.alerts import build_alert_centre
from investment_operations.catalyst_calendar import build_catalyst_calendar
from investment_operations.metrics import build_operational_metrics
from investment_operations.morning import build_morning_office
from investment_operations.portfolio_ops import build_portfolio_operations
from investment_operations.production import health, run_desk
from investment_operations.research_queue import build_research_queue
from investment_operations.replay import build_decision_replay
from investment_operations.schema import ENGINE_CODE, RECOMMENDATION_POLICY, VERSION
from investment_operations.workspace import build_workspace


def _pack(
    ticker: str,
    *,
    score: float,
    priority: str,
    delta_status: str = "UNCHANGED",
    delta_n: int = 0,
    blockers: list | None = None,
    catalysts: list | None = None,
    sector: str = "it_services",
    themes: list | None = None,
) -> dict:
    entity = "TMPV" if ticker == "TATAMOTORS" else ticker
    return {
        "ok": True,
        "entity": entity,
        "display": ticker,
        "memory": {
            "ok": True,
            "entity": entity,
            "memory_version": 3,
            "compiled_at": "2026-07-28T12:00:00+00:00",
            "sector_history": {"sector_key": sector},
            "event_timeline": {
                "n": 1,
                "events": [{"date": "2026-07-18", "title": "Q1 Results"}],
            },
            "memory_delta": {
                "status": delta_status,
                "summary": "test delta" if delta_status != "UNCHANGED" else "noop",
                "n_field_changes": delta_n,
            },
        },
        "memory_delta": {
            "status": delta_status,
            "summary": "test delta" if delta_status != "UNCHANGED" else "noop",
            "n_field_changes": delta_n,
        },
        "knowledge_graph": {
            "n_nodes": 5,
            "n_edges": 6,
            "peers": ["INFY"],
            "themes": themes or (["AI"] if sector == "it_services" else []),
            "sector_key": sector,
        },
        "opportunity": {
            "ok": True,
            "entity": entity,
            "display": ticker,
            "score": score,
            "research_priority": priority,
            "why_now": f"{ticker} interesting due to score {score}",
            "strengths": ["Momentum"],
            "blockers": blockers or [],
            "catalysts": catalysts
            or [
                {
                    "name": "Quarterly results",
                    "expected_window": "near_term",
                    "importance": "High",
                    "confidence": 0.85,
                    "evidence": {"source": "event_timeline"},
                }
            ],
            "freshness": {"memory_version": 3},
            "opportunity": {
                "knowledge_delta": {
                    "status": delta_status,
                    "summary": "test delta" if delta_status != "UNCHANGED" else "noop",
                    "n_field_changes": delta_n,
                }
            },
        },
    }


def _universe_packs() -> list[dict]:
    return [
        _pack("TCS", score=72.0, priority="High", delta_status="UPDATED", delta_n=4),
        _pack("HDFCBANK", score=48.0, priority="Low", sector="banks", themes=[]),
        _pack(
            "HAL",
            score=81.0,
            priority="Critical",
            sector="defence",
            themes=["Defence"],
            blockers=[{"code": "rich_valuation", "severity": "High", "title": "Rich valuation", "detail": "premium"}],
        ),
        _pack("NTPC", score=60.0, priority="Medium", sector="power", themes=[], delta_status="UPDATED", delta_n=2),
    ]


def test_health_not_an_engine():
    h = health()
    assert h["engine"] == ENGINE_CODE
    assert h["version"] == VERSION
    assert h["not_an_intelligence_engine"] is True
    assert h["issues_recommendations"] is False
    assert h["modifies_decision_engine"] is False
    assert h["bypasses_cid"] is False
    assert "morning_office" in h["capabilities"]


def test_morning_office_deterministic():
    packs = _universe_packs()
    a = build_morning_office(packs, holdings=["TCS", "HAL"])
    b = build_morning_office(packs, holdings=["TCS", "HAL"])
    assert [r["entity"] for r in a["top_opportunities"]] == [r["entity"] for r in b["top_opportunities"]]
    assert a["top_opportunities"][0]["entity"] == "HAL"  # highest score
    assert a["overnight_changes"]
    assert a["analyst_priorities"]
    assert a["portfolio_alerts"]


def test_research_queue_ranks_consistently():
    packs = _universe_packs()
    q1 = build_research_queue(packs, holdings=["TCS"], limit=10)
    q2 = build_research_queue(packs, holdings=["TCS"], limit=10)
    assert [t["entity"] for t in q1["tasks"]] == [t["entity"] for t in q2["tasks"]]
    assert q1["tasks"][0]["company"]
    assert q1["tasks"][0]["supporting_evidence"]["opportunity_score"] is not None


def test_portfolio_ops_no_allocation():
    packs = _universe_packs()
    port = build_portfolio_operations(packs, holdings=["TCS", "HAL", "NTPC"])
    assert port["issues_recommendations"] is False
    assert port["recommendation_policy"] == "no_allocation_advice"
    assert port["expected_impact"]["qualitative"] in {"positive", "negative", "neutral"}
    assert any(h["holding"] == "HAL" for h in port["affected_holdings"])


def test_alerts_evidence_backed():
    packs = _universe_packs()
    alerts = build_alert_centre(packs)
    assert alerts["n"] >= 1
    for a in alerts["alerts"]:
        assert a["what_changed"]
        assert a["why_it_matters"]
        assert a["issues_recommendations"] is False


def test_catalyst_calendar_and_metrics():
    packs = _universe_packs()
    morning = build_morning_office(packs)
    queue = build_research_queue(packs)
    cats = build_catalyst_calendar(packs)
    alerts = build_alert_centre(packs)
    metrics = build_operational_metrics(
        packs,
        morning=morning,
        research_queue=queue,
        alerts=alerts,
        catalysts=cats,
    )
    assert cats["n"] >= 1
    assert metrics["operations_metrics"]["monitored_companies"] == 4
    assert metrics["operations_metrics"]["compilation_success_rate"] == 100.0


def test_workspace_and_replay_aggregate():
    pack = _pack("TCS", score=72.0, priority="High", delta_status="UPDATED", delta_n=3)
    ws = build_workspace("TCS", company_pack=pack)
    assert ws["unified"] is True
    assert ws["modules"]["opportunity_pack"]["score"] == 72.0
    assert ws["modules"]["knowledge_graph"]["present"] is True
    replay = build_decision_replay("TCS", company_pack=pack)
    assert replay["issues_recommendations"] is False
    assert replay["modifies_decision_engine"] is False
    assert any(s["step"] == "opportunity_pack" for s in replay["replay_chain"])


def test_run_desk_injected_no_buy_sell():
    packs = _universe_packs()
    injected = {p["display"]: p for p in packs}
    desk = run_desk(
        universe=["TCS", "HDFCBANK", "HAL", "NTPC"],
        holdings=["TCS", "HAL"],
        injected_by_ticker=injected,
        include_soft_reasoning=False,
    )
    assert desk["ok_n"] == 4
    assert desk["recommendation_policy"] == RECOMMENDATION_POLICY
    assert desk["issues_recommendations"] is False
    assert desk["modifies_decision_engine"] is False
    assert desk["morning_office"]["top_opportunities"]
    assert desk["research_queue"]["n"] >= 1
    blob = str(desk["morning_office"]).upper()
    assert "BUY " not in blob and "SELL " not in blob
