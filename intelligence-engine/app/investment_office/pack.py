"""Assemble InvestmentOfficePackage — operational layer over existing AGI desks."""

from __future__ import annotations

from typing import Any

from app.investment_office.calendar import build_calendar
from app.investment_office.graph import build_knowledge_graph
from app.investment_office.journal import build_decision_journal, research_timeline_from_journal
from app.investment_office.playbooks import list_playbooks
from app.investment_office.queue import build_research_queue
from app.portfolio.pack import build_portfolio_package, evaluate_scenario
from app.schemas.models import (
    InvestmentOfficePackage,
    InvestmentOfficeRequest,
    ResearchRun,
)

WORKSPACE_TABS = [
    "Today's Brief",
    "Research Queue",
    "Investment Calendar",
    "Scenario Center",
    "Decision Journal",
    "Knowledge Graph",
    "Playbooks",
    "Portfolio Office",
    "CIO Summary",
]

COMPONENTS_REUSED = [
    "Intelligence Core",
    "Research Director",
    "Memory (RAG)",
    "Evidence Engine",
    "Confidence Engine",
    "Debate Engine",
    "Citation Engine",
    "Market Intelligence",
    "Equity Research",
    "Forecast Intelligence",
    "Portfolio Office",
    "Institutional Screener",
    "Watchlist Intelligence",
    "Company Comparison",
    "AGI Copilot",
    "Validation Analytics",
    "Research Visualization",
    "CIO Committee",
]


def _scenario_center() -> dict[str, Any]:
    return {
        "status": "scaffold",
        "allowed_questions": [
            "What happens if oil reaches $100?",
            "What if RBI cuts rates?",
            "What if inflation rises?",
            "What if China slows?",
        ],
        "policy": (
            "Reuse Forecast, Portfolio, Macro, and Research. "
            "Never invent assumptions. Explain assumptions. Withhold if engines unavailable."
        ),
        "engines": {
            "forecast": "reuse_when_available",
            "portfolio": "portfolio_office",
            "macro": "cio_morning_macro_cache",
            "research": "equity_and_memory",
        },
    }


def evaluate_office_scenario(
    question: str,
    *,
    portfolio_req: dict[str, Any] | None = None,
    package: InvestmentOfficePackage | None = None,
) -> dict[str, Any]:
    """Scenario Center — prefer Portfolio Office scenario helper; never invent outcomes."""
    port_pack = None
    if portfolio_req:
        from app.schemas.models import PortfolioIngestRequest

        port_pack = build_portfolio_package(req=PortfolioIngestRequest(**portfolio_req))
    elif package and package.portfolio_office_link.get("package"):
        # link may hold a dumped package without full PortfolioPackage type
        pass

    result = evaluate_scenario(question, port_pack)
    # Enrich with office context notes
    result["office"] = {
        "reused": ["Forecast", "Portfolio", "Macro", "Research"],
        "playbooks_in_scope": [p.get("id") for p in (package.playbooks if package else [])][:5],
    }
    return result


def build_daily_brief(
    *,
    macro: dict[str, Any] | None,
    market: dict[str, Any] | None,
    pre_market: dict[str, Any] | None,
    queue: list[Any],
    calendar: list[Any],
    portfolio_link: dict[str, Any],
    withheld: list[str],
) -> dict[str, Any]:
    economist = (macro or {}).get("chiefEconomistBrief") or {}
    morning = (pre_market or {}).get("morningNote") or {}
    market_story = (
        morning.get("executiveThesis")
        or morning.get("narrative")
        or (market or {}).get("summary")
        or economist.get("executiveThesis")
    )
    outlook = economist.get("outlook") or (market or {}).get("outlook")

    high = [i for i in queue if (getattr(i, "priority", None) or i.get("priority")) == "high"]
    medium = [i for i in queue if (getattr(i, "priority", None) or i.get("priority")) == "medium"]

    def _dump(x: Any) -> dict[str, Any]:
        return x.model_dump() if hasattr(x, "model_dump") else dict(x)

    opportunities = [_dump(i) for i in (high + medium)[:5]]
    risks = []
    for r in (economist.get("keyRisks") or [])[:5]:
        risks.append(
            {
                "title": r.get("label"),
                "level": r.get("level"),
                "reason": r.get("why"),
                "evidence": ["agib:macro-briefing"],
                "confidence": 60,
            }
        )
    if not risks:
        risks = [
            {
                "title": "Macro risk feed incomplete",
                "reason": "Key risks withheld until macro briefing is available — not fabricated.",
                "evidence": [],
                "confidence": 30,
            }
        ]

    earnings = [
        _dump(e)
        for e in calendar
        if (getattr(e, "category", None) or e.get("category")) == "earnings"
        and (getattr(e, "status", None) or e.get("status")) != "withheld"
    ]
    macro_events = [
        _dump(e)
        for e in calendar
        if (getattr(e, "category", None) or e.get("category")) in {"rbi", "fed", "inflation", "gdp", "policy"}
        and (getattr(e, "status", None) or e.get("status")) != "withheld"
    ]

    return {
        "executive_summary": (
            f"Investment Office daily brief. Market story "
            f"{'available from AGIB caches' if market_story else 'withheld (cache miss)'}. "
            f"{len(high)} high-priority research items. "
            "Stance is Neutral / Review — no trade execution."
        ),
        "todays_market_story": market_story
        or {
            "status": "withheld",
            "note": "Market / pre-market briefing unavailable — story not invented.",
        },
        "outlook": outlook,
        "top_opportunities": opportunities
        or [
            {
                "title": "No prioritised opportunities yet",
                "reason": "Attach watchlist / portfolio / prior research to surface opportunities.",
                "evidence": [],
                "confidence": 40,
            }
        ],
        "top_risks": risks,
        "important_earnings": earnings
        or {"status": "withheld", "note": "Earnings dates require calendar feed evidence."},
        "macro_events": macro_events
        or {"status": "withheld", "note": "Macro event dates withheld without briefing evidence."},
        "forecast_changes": {
            "status": "withheld",
            "note": "Forecast Intelligence changes require Forecast Layer — not fabricated.",
        },
        "portfolio_review": portfolio_link
        or {"status": "scaffold", "note": "Link Portfolio Office for holdings review."},
        "watchlist_review": {
            "status": "packaged",
            "high_priority": len(high),
            "note": "Watchlist Intelligence reused via research queue symbols.",
        },
        "companies_to_research": [
            getattr(i, "symbol", None) or (i.get("symbol") if isinstance(i, dict) else None)
            for i in (high + medium)[:8]
        ],
        "research_priorities": [
            getattr(i, "title", None) or (i.get("title") if isinstance(i, dict) else None)
            for i in queue[:10]
        ],
        "withheld": withheld,
        "disclaimer": "Never recommend or execute trades. Evidence-backed review only.",
    }


def build_investment_office_package(
    req: InvestmentOfficeRequest | None = None,
    *,
    macro: dict[str, Any] | None = None,
    market: dict[str, Any] | None = None,
    pre_market: dict[str, Any] | None = None,
    similar_runs: list[dict[str, Any]] | None = None,
) -> InvestmentOfficePackage:
    req = req or InvestmentOfficeRequest()
    symbols = [str(s).upper() for s in (req.symbols or []) if s]
    watchlist = [str(s).upper() for s in (req.watchlist or []) if s]
    for s in watchlist:
        if s not in symbols:
            symbols.append(s)

    portfolio_link: dict[str, Any] = {"status": "not_attached"}
    portfolio_recs: list[dict[str, Any]] = []
    if req.portfolio is not None:
        port = build_portfolio_package(req=req.portfolio)
        portfolio_recs = [r.model_dump() for r in port.recommendations]
        portfolio_link = {
            "status": "attached",
            "portfolio_id": port.portfolio.portfolio_id,
            "name": port.portfolio.name,
            "health_score": port.health_score,
            "recommendation_count": len(port.recommendations),
            "action_center": port.action_center,
            "workspace_tabs": (port.workspace or {}).get("tabs"),
        }
        for h in port.portfolio.holdings:
            if h.symbol not in symbols:
                symbols.append(h.symbol)
            if h.symbol not in watchlist:
                watchlist.append(h.symbol)

    prior = list(req.prior_runs or []) + list(similar_runs or [])
    playbooks = list_playbooks()
    queue = build_research_queue(
        symbols=symbols,
        watchlist=watchlist,
        prior_runs=prior,
        portfolio_recs=portfolio_recs,
    )
    calendar = build_calendar(macro=macro, pre_market=pre_market, symbols=symbols)

    macro_labels = []
    for r in ((macro or {}).get("chiefEconomistBrief") or {}).get("keyRisks") or []:
        if r.get("label"):
            macro_labels.append(str(r["label"]))

    journal = build_decision_journal(
        prior_runs=prior,
        portfolio_pack=portfolio_link if portfolio_link.get("status") == "attached" else None,
        queue=queue,
        seed=req.journal_seed,
    )
    timeline = research_timeline_from_journal(journal)
    graph = build_knowledge_graph(
        symbols=symbols,
        sectors=req.sectors,
        playbooks=playbooks,
        queue=queue,
        calendar=calendar,
        macro_labels=macro_labels,
    )

    withheld = [
        "Fabricated event dates",
        "Invented forecast changes",
        "Trade recommendations (Buy/Sell/Execute)",
        "Scenario outcomes without Forecast/Macro engines",
    ]
    if not macro and not pre_market and not market:
        withheld.append("Live market story (AGIB caches unavailable)")

    brief = build_daily_brief(
        macro=macro,
        market=market,
        pre_market=pre_market,
        queue=queue,
        calendar=calendar,
        portfolio_link=portfolio_link,
        withheld=withheld,
    )

    recommendations = [
        {
            "priority": i.priority,
            "title": i.title,
            "reason": i.reason,
            "evidence": i.evidence,
            "confidence": i.confidence,
            "supporting_research": i.supporting_research,
            "related_reports": i.related_reports,
            "verb": "Research" if i.priority == "high" else "Review" if i.priority == "medium" else "Monitor",
        }
        for i in queue[:12]
    ]

    conf = 55
    if macro or pre_market:
        conf += 10
    if portfolio_link.get("status") == "attached":
        conf += 5
    if queue:
        conf += 5
    conf = min(85, conf)

    return InvestmentOfficePackage(
        daily_brief=brief,
        research_queue=queue,
        calendar=calendar,
        playbooks=playbooks,
        scenario_center=_scenario_center(),
        research_timeline=timeline,
        decision_journal=journal,
        knowledge_graph=graph,
        portfolio_office_link=portfolio_link,
        workspace={"mode": "investment_office", "tabs": WORKSPACE_TABS},
        recommendations=recommendations,
        evidence=[
            f"symbols={len(symbols)}",
            f"watchlist={len(watchlist)}",
            f"queue={len(queue)}",
            f"calendar={len(calendar)}",
            f"playbooks={len(playbooks)}",
            f"journal={len(journal)}",
            f"graph_nodes={len(graph.get('nodes') or [])}",
        ],
        confidence=conf,
        notes=[
            "Investment Office is the operational layer above existing AGI capabilities.",
            "Does not execute trades. Does not invent assumptions.",
            req.query or "Default office package.",
        ],
        withheld=withheld,
        components_reused=list(COMPONENTS_REUSED),
    )


def package_from_metadata(metadata: dict[str, Any] | None) -> InvestmentOfficePackage | None:
    meta = metadata or {}
    block = meta.get("investment_office") or meta.get("office")
    if block is None and not any(
        k in meta for k in ("watchlist", "symbols", "portfolio", "journal_seed", "prior_runs")
    ):
        # Still build a default office so the desk is exercisable
        return None
    raw = block if isinstance(block, dict) else meta
    req = InvestmentOfficeRequest(
        user_id=raw.get("user_id"),
        watchlist=raw.get("watchlist") or meta.get("watchlist") or [],
        symbols=raw.get("symbols") or meta.get("symbols") or [],
        sectors=raw.get("sectors") or meta.get("sectors") or [],
        portfolio=raw.get("portfolio") or meta.get("portfolio"),
        journal_seed=raw.get("journal_seed") or meta.get("journal_seed") or [],
        prior_runs=raw.get("prior_runs") or meta.get("prior_runs") or [],
        query=raw.get("query") or meta.get("query"),
    )
    return build_investment_office_package(req)


def attach_office_to_run(run: ResearchRun, package: InvestmentOfficePackage) -> ResearchRun:
    run.investment_office = package
    run.metadata = {
        **(run.metadata or {}),
        "investment_office": True,
        "office_id": package.office_id,
        "queue_count": len(package.research_queue),
        "brief_ready": bool(package.daily_brief),
    }
    return run
