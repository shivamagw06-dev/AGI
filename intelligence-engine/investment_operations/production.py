"""P5 Investment Operations Layer — production façade (orchestration only)."""

from __future__ import annotations

from typing import Any

from investment_operations.alerts import build_alert_centre
from investment_operations.catalyst_calendar import build_catalyst_calendar
from investment_operations.collect import collect_company, collect_universe
from investment_operations.daily_brief import build_daily_brief
from investment_operations.metrics import build_operational_metrics
from investment_operations.morning import build_morning_office
from investment_operations.monitoring import build_monitoring_office
from investment_operations.portfolio_ops import build_portfolio_operations
from investment_operations.replay import build_decision_replay
from investment_operations.research_queue import build_research_queue
from investment_operations.schema import (
    CAPABILITIES,
    ENGINE_CODE,
    ENGINE_NAME,
    MILESTONE,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    VERSION,
    WORKSTREAM_ID,
)
from investment_operations.util import default_universe, now_iso
from investment_operations.workspace import build_workspace


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "engine": ENGINE_CODE,
        "engine_name": ENGINE_NAME,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "milestone": MILESTONE,
        "role": "investment_operations_orchestration",
        "not_an_intelligence_engine": True,
        "capabilities": list(CAPABILITIES),
        "default_universe": list(default_universe()),
        "orchestrates": [
            "company_memory",
            "knowledge_delta_engine",
            "investment_knowledge_graph",
            "opportunity_intelligence",
            "institutional_scenario_intelligence",
            "hypothesis_engine",
            "contradiction_reasoning",
            "causal_graph",
            "investment_office",
            "cid",
            "decision_engine (read-only)",
        ],
        "never_queries_raw_apis": True,
        "issues_recommendations": False,
        "modifies_decision_engine": False,
        "bypasses_cid": False,
        "recommendation_policy": RECOMMENDATION_POLICY,
    }


def run_desk(
    *,
    universe: list[str] | tuple[str, ...] | None = None,
    holdings: list[str] | None = None,
    injected_by_ticker: dict[str, dict[str, Any]] | None = None,
    persist_memory: bool = False,
    include_soft_reasoning: bool = False,
    portfolio_id: str = "default",
) -> dict[str, Any]:
    """Full Investment Operations desk for a universe (default IC-10)."""
    packs = collect_universe(
        universe,
        injected_by_ticker=injected_by_ticker,
        persist_memory=persist_memory,
        include_soft_reasoning=include_soft_reasoning,
    )
    morning = build_morning_office(packs, holdings=holdings)
    queue = build_research_queue(packs, holdings=holdings)
    portfolio = build_portfolio_operations(packs, holdings=holdings, portfolio_id=portfolio_id)
    monitoring = build_monitoring_office(packs)
    catalysts = build_catalyst_calendar(packs)
    alerts = build_alert_centre(packs, monitoring=monitoring, portfolio=portfolio)
    brief = build_daily_brief(morning, queue, portfolio, alerts, brief_type="morning")
    metrics = build_operational_metrics(
        packs,
        morning=morning,
        research_queue=queue,
        alerts=alerts,
        catalysts=catalysts,
        portfolio=portfolio,
    )
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "programme": PROGRAMME,
        "as_of": now_iso(),
        "morning_office": morning,
        "research_queue": queue,
        "portfolio": portfolio,
        "monitoring_office": monitoring,
        "alerts": alerts,
        "catalysts": catalysts,
        "daily_brief": brief,
        "metrics": metrics,
        "universe_n": len(packs),
        "ok_n": sum(1 for p in packs if p.get("ok")),
        "recommendation_policy": RECOMMENDATION_POLICY,
        "issues_recommendations": False,
        "modifies_decision_engine": False,
        "_packs": packs,  # internal for workspace/replay helpers
    }


def morning_office(**kwargs: Any) -> dict[str, Any]:
    desk = run_desk(**kwargs)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "morning_office": desk["morning_office"],
        "daily_brief": desk["daily_brief"],
        "recommendation_policy": RECOMMENDATION_POLICY,
        "issues_recommendations": False,
    }


def research_queue(**kwargs: Any) -> dict[str, Any]:
    limit = int(kwargs.pop("limit", 25) or 25)
    holdings = kwargs.get("holdings")
    desk = run_desk(**kwargs)
    # Re-rank with explicit limit from already-collected packs
    queue = build_research_queue(desk.get("_packs") or [], holdings=holdings, limit=limit)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        **queue,
        "recommendation_policy": RECOMMENDATION_POLICY,
    }


def portfolio(**kwargs: Any) -> dict[str, Any]:
    desk = run_desk(**kwargs)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        **desk["portfolio"],
    }


def alerts(**kwargs: Any) -> dict[str, Any]:
    desk = run_desk(**kwargs)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        **desk["alerts"],
    }


def catalysts(**kwargs: Any) -> dict[str, Any]:
    desk = run_desk(**kwargs)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        **desk["catalysts"],
    }


def daily_brief(brief_type: str = "morning", **kwargs: Any) -> dict[str, Any]:
    desk = run_desk(**kwargs)
    brief = build_daily_brief(
        desk["morning_office"],
        desk["research_queue"],
        desk["portfolio"],
        desk["alerts"],
        brief_type=brief_type,
    )
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        **brief,
    }


def metrics(**kwargs: Any) -> dict[str, Any]:
    desk = run_desk(**kwargs)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        **desk["metrics"],
    }


def workspace(ticker: str, **kwargs: Any) -> dict[str, Any]:
    pack = collect_company(
        ticker,
        persist_memory=kwargs.pop("persist_memory", False),
        include_soft_reasoning=kwargs.pop("include_soft_reasoning", True),
        injected=kwargs.pop("injected", None),
    )
    ws = build_workspace(ticker, company_pack=pack)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        **ws,
    }


def decision_replay(ticker: str, version: int | None = None, **kwargs: Any) -> dict[str, Any]:
    pack = None
    if kwargs.get("injected"):
        pack = kwargs["injected"]
    else:
        pack = collect_company(
            ticker,
            persist_memory=False,
            include_soft_reasoning=False,
        )
    replay = build_decision_replay(ticker, version=version, company_pack=pack)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        **replay,
    }


def monitoring(**kwargs: Any) -> dict[str, Any]:
    desk = run_desk(**kwargs)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        **desk["monitoring_office"],
    }


def package_for_ask_agi(query: str = "", *, ticker: str | None = None, **kwargs: Any) -> dict[str, Any]:
    if ticker:
        ws = workspace(ticker, include_soft_reasoning=False)
        return {
            "enabled": True,
            "engine": ENGINE_CODE,
            "version": VERSION,
            "query": query,
            "ticker": ws.get("entity"),
            "opportunity": (ws.get("modules") or {}).get("opportunity_pack"),
            "research_priority": ((ws.get("modules") or {}).get("opportunity_pack") or {}).get("research_priority"),
            "recommendation_policy": RECOMMENDATION_POLICY,
        }
    desk = morning_office(**kwargs)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "query": query,
        "top_opportunities": (desk.get("morning_office") or {}).get("top_opportunities"),
        "analyst_priorities": (desk.get("morning_office") or {}).get("analyst_priorities"),
        "recommendation_policy": RECOMMENDATION_POLICY,
    }


def ic10_smoke(
    *,
    holdings: list[str] | None = None,
) -> dict[str, Any]:
    holdings = holdings or ["TCS", "HDFCBANK", "HAL", "NTPC"]
    # Single collect pass — determinism verified by re-orchestrating identical packs
    packs = collect_universe(include_soft_reasoning=False, persist_memory=False)
    m1 = build_morning_office(packs, holdings=holdings)
    m2 = build_morning_office(packs, holdings=holdings)
    q1 = build_research_queue(packs, holdings=holdings)
    q2 = build_research_queue(packs, holdings=holdings)
    portfolio = build_portfolio_operations(packs, holdings=holdings)
    monitoring = build_monitoring_office(packs)
    catalysts = build_catalyst_calendar(packs)
    alerts = build_alert_centre(packs, monitoring=monitoring, portfolio=portfolio)
    metrics_pack = build_operational_metrics(
        packs,
        morning=m1,
        research_queue=q1,
        alerts=alerts,
        catalysts=catalysts,
        portfolio=portfolio,
    )
    det = {
        "top_opportunities_match": [r.get("entity") for r in m1.get("top_opportunities") or []]
        == [r.get("entity") for r in m2.get("top_opportunities") or []],
        "queue_match": [t.get("entity") for t in q1.get("tasks") or []]
        == [t.get("entity") for t in q2.get("tasks") or []],
        "why_now_stable": all(
            (a.get("why_now") == b.get("why_now"))
            for a, b in zip(m1.get("top_opportunities") or [], m2.get("top_opportunities") or [])
        ),
    }
    tcs = next((p for p in packs if p.get("entity") in {"TCS"} or p.get("display") == "TCS"), None)
    ws = build_workspace("TCS", company_pack=tcs) if tcs else {"ok": False}
    replay = build_decision_replay("TCS", company_pack=tcs) if tcs else {"reproducible": False}
    ok_n = sum(1 for p in packs if p.get("ok"))
    return {
        "universe": "IC-10",
        "ok_n": ok_n,
        "universe_n": len(packs),
        "determinism": det,
        "morning_top": (m1.get("top_opportunities") or [])[:5],
        "research_queue_n": q1.get("n"),
        "alerts_n": alerts.get("n"),
        "catalysts_n": catalysts.get("n"),
        "portfolio_urgency": portfolio.get("urgency"),
        "metrics": metrics_pack.get("operations_metrics"),
        "workspace_ok": ws.get("ok"),
        "replay_reproducible": replay.get("reproducible"),
        "recommendation_policy": RECOMMENDATION_POLICY,
        "issues_recommendations": False,
        "modifies_decision_engine": False,
    }
