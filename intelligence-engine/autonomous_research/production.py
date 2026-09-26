"""P6 Autonomous Research Office — production façade (orchestration only)."""

from __future__ import annotations

from typing import Any

from autonomous_research.coverage import build_coverage
from autonomous_research.evidence_monitor import build_evidence_monitor
from autonomous_research.generator import generate_for_plans, generate_research_pack
from autonomous_research.learning import build_learning_feedback
from autonomous_research.planner import build_research_plan
from autonomous_research.portfolio_review import build_portfolio_review
from autonomous_research.publications import build_publications
from autonomous_research.qa import qa_batch, run_qa
from autonomous_research.schema import (
    CAPABILITIES,
    ENGINE_CODE,
    ENGINE_NAME,
    MILESTONE,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    VERSION,
    WORKSTREAM_ID,
)
from autonomous_research.themes import build_theme_intelligence
from autonomous_research.util import now_iso, soft_call
from autonomous_research.watchlists import build_watchlists


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "engine": ENGINE_CODE,
        "engine_name": ENGINE_NAME,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "milestone": MILESTONE,
        "role": "autonomous_research_office",
        "not_an_intelligence_engine": True,
        "does_not_replace_analysts": True,
        "does_not_make_investment_decisions": True,
        "capabilities": list(CAPABILITIES),
        "governed_by": ["constitution", "cid", "decision_engine", "committee_certification"],
        "consumes": [
            "investment_operations",
            "opportunity_intelligence",
            "company_memory",
            "knowledge_delta_engine",
            "investment_knowledge_graph",
            "research_office (soft)",
        ],
        "never_queries_raw_apis": True,
        "issues_recommendations": False,
        "modifies_decision_engine": False,
        "bypasses_cid": False,
        "recommendation_policy": RECOMMENDATION_POLICY,
    }


def run_office(
    *,
    universe: list[str] | tuple[str, ...] | None = None,
    holdings: list[str] | None = None,
    injected_by_ticker: dict[str, dict[str, Any]] | None = None,
    persist_memory: bool = False,
    draft_limit: int = 8,
    governance_approved_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Full ARO cycle over IOL-collected packs."""
    from investment_operations.collect import collect_universe
    from investment_operations.daily_brief import build_daily_brief
    from investment_operations.morning import build_morning_office
    from investment_operations.portfolio_ops import build_portfolio_operations
    from investment_operations.research_queue import build_research_queue
    from investment_operations.alerts import build_alert_centre
    from investment_operations.monitoring import build_monitoring_office
    from investment_operations.catalyst_calendar import build_catalyst_calendar

    packs = collect_universe(
        universe,
        injected_by_ticker=injected_by_ticker,
        persist_memory=persist_memory,
        include_soft_reasoning=False,
    )
    morning = build_morning_office(packs, holdings=holdings)
    iol_queue = build_research_queue(packs, holdings=holdings)
    portfolio_ops = build_portfolio_operations(packs, holdings=holdings)
    monitoring = build_monitoring_office(packs)
    catalysts = build_catalyst_calendar(packs)
    alerts = build_alert_centre(packs, monitoring=monitoring, portfolio=portfolio_ops)
    brief = build_daily_brief(morning, iol_queue, portfolio_ops, alerts, brief_type="morning")

    plan = build_research_plan(packs, holdings=holdings, catalysts=catalysts)
    drafts_pack = generate_for_plans(packs, plan.get("plans") or [], limit=draft_limit)
    qa = qa_batch(drafts_pack.get("drafts") or [], packs)
    coverage = build_coverage(packs, drafts=drafts_pack.get("drafts"))
    watchlists = build_watchlists(packs, holdings=holdings)
    themes = build_theme_intelligence(packs)
    evidence = build_evidence_monitor(packs)
    port_review = build_portfolio_review(packs, holdings=holdings, portfolio_ops=portfolio_ops)
    publications = build_publications(
        morning_brief=brief,
        drafts=drafts_pack.get("drafts"),
        qa_results=qa,
        themes=themes,
        portfolio_review=port_review,
        governance_approved_ids=governance_approved_ids,
    )
    learning = build_learning_feedback(
        company_packs=packs,
        qa_results=qa,
        coverage=coverage,
        evidence_monitor=evidence,
        publications=publications,
    )

    # Soft research_office presence
    ro = soft_call("research_office", _research_office_health)

    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "programme": PROGRAMME,
        "as_of": now_iso(),
        "planner": plan,
        "tasks": plan,  # alias — planner output is the task board
        "drafts": drafts_pack,
        "coverage": coverage,
        "watchlists": watchlists,
        "themes": themes,
        "evidence_monitor": evidence,
        "portfolio_review": port_review,
        "publications": publications,
        "qa": qa,
        "learning": learning,
        "iol_morning": {
            "top_opportunities": (morning.get("top_opportunities") or [])[:5],
            "analyst_priorities_n": len(morning.get("analyst_priorities") or []),
        },
        "research_office_soft": ro,
        "universe_n": len(packs),
        "ok_n": sum(1 for p in packs if p.get("ok")),
        "recommendation_policy": RECOMMENDATION_POLICY,
        "issues_recommendations": False,
        "modifies_decision_engine": False,
        "_packs": packs,
    }


def status(**kwargs: Any) -> dict[str, Any]:
    office = run_office(**kwargs)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "ok_n": office.get("ok_n"),
        "universe_n": office.get("universe_n"),
        "planner_n": (office.get("planner") or {}).get("n"),
        "drafts_n": (office.get("drafts") or {}).get("n"),
        "qa_passed_n": (office.get("qa") or {}).get("passed_n"),
        "qa_blocked_n": (office.get("qa") or {}).get("blocked_n"),
        "publications_n": (office.get("publications") or {}).get("n"),
        "watchlist_counts": (office.get("watchlists") or {}).get("counts"),
        "themes_active": (office.get("themes") or {}).get("active_n"),
        "learning_findings": (office.get("learning") or {}).get("n_findings"),
        "recommendation_policy": RECOMMENDATION_POLICY,
        "issues_recommendations": False,
    }


def planner(**kwargs: Any) -> dict[str, Any]:
    office = run_office(**kwargs)
    return {"enabled": True, "engine": ENGINE_CODE, "version": VERSION, **office["planner"]}


def tasks(**kwargs: Any) -> dict[str, Any]:
    return planner(**kwargs)


def watchlists(**kwargs: Any) -> dict[str, Any]:
    office = run_office(**kwargs)
    return {"enabled": True, "engine": ENGINE_CODE, "version": VERSION, **office["watchlists"]}


def themes(**kwargs: Any) -> dict[str, Any]:
    office = run_office(**kwargs)
    return {"enabled": True, "engine": ENGINE_CODE, "version": VERSION, **office["themes"]}


def coverage(**kwargs: Any) -> dict[str, Any]:
    office = run_office(**kwargs)
    return {"enabled": True, "engine": ENGINE_CODE, "version": VERSION, **office["coverage"]}


def research(ticker: str, **kwargs: Any) -> dict[str, Any]:
    from investment_operations.collect import collect_company

    injected = kwargs.pop("injected", None)
    pack = collect_company(
        ticker,
        injected=injected,
        persist_memory=kwargs.pop("persist_memory", False),
        include_soft_reasoning=False,
    )
    plan = None
    plans = build_research_plan([pack], holdings=kwargs.get("holdings"))
    if plans.get("plans"):
        plan = plans["plans"][0]
    draft = generate_research_pack(pack, plan=plan)
    qa = run_qa(draft, company_pack=pack)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "ticker": pack.get("display") or pack.get("entity"),
        "entity": pack.get("entity"),
        "plan": plan,
        "draft": draft,
        "qa": qa,
        "issues_recommendations": False,
        "recommendation_policy": RECOMMENDATION_POLICY,
    }


def publications(**kwargs: Any) -> dict[str, Any]:
    office = run_office(**kwargs)
    return {"enabled": True, "engine": ENGINE_CODE, "version": VERSION, **office["publications"]}


def qa(**kwargs: Any) -> dict[str, Any]:
    office = run_office(**kwargs)
    return {"enabled": True, "engine": ENGINE_CODE, "version": VERSION, **office["qa"]}


def learning(**kwargs: Any) -> dict[str, Any]:
    office = run_office(**kwargs)
    return {"enabled": True, "engine": ENGINE_CODE, "version": VERSION, **office["learning"]}


def ic10_smoke(*, holdings: list[str] | None = None) -> dict[str, Any]:
    holdings = holdings or ["TCS", "HDFCBANK", "HAL", "NTPC"]
    from investment_operations.collect import collect_universe

    packs = collect_universe(include_soft_reasoning=False, persist_memory=False)
    plan1 = build_research_plan(packs, holdings=holdings)
    plan2 = build_research_plan(packs, holdings=holdings)
    drafts = generate_for_plans(packs, plan1.get("plans") or [], limit=5)
    qa = qa_batch(drafts.get("drafts") or [], packs)
    wl = build_watchlists(packs, holdings=holdings)
    th = build_theme_intelligence(packs)
    cov = build_coverage(packs, drafts=drafts.get("drafts"))
    pubs = build_publications(
        drafts=drafts.get("drafts"),
        qa_results=qa,
        themes=th,
        governance_approved_ids=[],  # none auto-approved
    )
    # Decision replay soft for first draft
    replay_ok = False
    if drafts.get("drafts"):
        ent = drafts["drafts"][0].get("entity")
        from investment_operations.replay import build_decision_replay

        pack = next((p for p in packs if p.get("entity") == ent), None)
        replay = build_decision_replay(ent, company_pack=pack) if pack else {}
        replay_ok = bool(replay.get("reproducible"))

    det = {
        "planner_match": [p.get("entity") for p in plan1.get("plans") or []]
        == [p.get("entity") for p in plan2.get("plans") or []],
        "priority_match": [p.get("priority") for p in plan1.get("plans") or []]
        == [p.get("priority") for p in plan2.get("plans") or []],
    }
    return {
        "universe": "IC-10",
        "ok_n": sum(1 for p in packs if p.get("ok")),
        "universe_n": len(packs),
        "determinism": det,
        "planner_n": plan1.get("n"),
        "drafts_n": drafts.get("n"),
        "qa_passed_n": qa.get("passed_n"),
        "qa_blocked_n": qa.get("blocked_n"),
        "publications_n": pubs.get("n"),
        "publications_auto_approved_n": sum(
            1 for p in pubs.get("publications") or [] if p.get("governance_approved")
        ),
        "watchlist_counts": wl.get("counts"),
        "themes_active": th.get("active_n"),
        "stale_n": len((cov.get("coverage") or {}).get("stale_reports") or []),
        "replay_reproducible": replay_ok,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "issues_recommendations": False,
        "modifies_decision_engine": False,
    }


def _research_office_health() -> dict[str, Any]:
    from research_office.production import health as ro_health

    return ro_health()
