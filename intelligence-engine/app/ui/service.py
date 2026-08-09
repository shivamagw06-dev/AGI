"""UI Aggregation Service — assembles client views from existing platforms."""

from __future__ import annotations

import re
from typing import Any

from app.aws.adapters import dump, soft
from app.core.config import get_settings
from app.kip.models import ClientSearchRequest
from app.ui.flags import UiFlags
from app.ui.financial_router import route as financial_router_route
from app.ui.coverage_policy import (
    detect_unsupported_company as coverage_policy_detect,
    unsupported_coverage_executive as coverage_policy_executive,
    unsupported_coverage_why as coverage_policy_why,
)
from app.ui.company_router import route as company_router_route
from knowledge_unification.production import answer_for_ask as kul_answer_for_ask
from app.kip.extractors import KNOWN_TICKERS, TICKER_STOPWORDS
from app.ui.ask_orchestration_trace import (
    StageTimer,
    finalize_orchestration,
    format_trace_summary,
    new_ask_trace_id,
)
from app.ui.ask_pipeline_trace import (
    STAGE_ENGINE_RECEIVED,
    STAGE_LLM_STARTED,
    STAGE_RETRIEVAL_COMPLETED,
    STAGE_RETRIEVAL_STARTED,
    AskPipelineTrace,
    normalize_request_id,
    sources_from_degradation,
)
from app.ui.executive_composer import (
    alias_tickers_from_question,
    comparison_clarification_executive,
    comparison_entity_count,
    compose_executive,
    finalize_executive,
    is_comparison_question,
    is_planning_scaffold,
    requires_resolved_company,
    unknown_entity_executive,
)
from app.ui.ticker_guard import (
    accept_detected_ticker,
    alias_ticker_from_question,
    looks_like_framework_meta_executive,
)
from app.ui.iax import (
    build_charts,
    clean_thesis_text,
    enrich_timeline,
    evidence_items,
    flatten_house_view,
    house_view_card,
    knowledge_graph_view,
    market_intelligence_summary,
    normalize_stance,
    related_ideas,
    research_panel,
    synthesize_thesis_points,
    whats_changed,
)
from app.ui.models import (
    UI_VERSION,
    ArticleView,
    AutocompleteView,
    CompanyView,
    CopilotView,
    DashboardView,
    HomeView,
    MacroView,
    PortfolioView,
    PredictionCentreView,
    ResearchView,
    SearchView,
    SectorView,
    ThemeView,
    TimelineView,
    UiMeta,
    WorkflowView,
)
from app.ui.product import (
    accuracy_summary,
    discovery_pack,
    enrichment_meta,
    macro_intelligence,
    prediction_row,
    sector_intelligence,
    theme_intelligence,
    thesis_status,
)
from app.ui.questions import (
    SEED_QUESTIONS,
    autocomplete as build_autocomplete,
    build_popular_questions,
    follow_up_questions,
)
from app.ui.sanitize import (
    pick_label,
    pick_number,
    public_source,
    scrub,
    scrub_text,
)
from app.ui.timeouts import ask_slim_enabled, call_with_timeout


def _unwrap_soft_slice(name: str, data: Any) -> dict[str, Any]:
    """Flatten `{name: {...}}` wrappers so Ask AGI fields stay one level deep."""
    if not isinstance(data, dict) or not data:
        return {}
    inner = data.get(name)
    if isinstance(inner, dict) and len(data) == 1:
        return inner
    return data


_RESEARCH_SHAPED_QUESTION_RE = re.compile(
    r"\b(annual report|earnings call|transcript|management (?:said|commentary)|"
    r"guidance|capital allocation|what changed since|research memory|"
    r"investor presentation|quarterly results)\b",
    re.I,
)

# QUE decision types that must reach answer_construction / research desk —
# never a thin CapIQ/KUL company dump.
_QUE_FULL_DESK_DECISIONS = frozenset(
    {
        "Capital Allocation",
        "Research Priority",
        "Valuation Assessment",
        "Thesis Validation",
        "Peer Selection",
        "Risk Assessment",
        "Earnings Review",
        "Portfolio Construction",
        "Idea Generation",
        "Monitoring",
        "Macro Impact",
        "Sector Allocation",
    }
)


def _is_research_shaped_question(question: str) -> bool:
    """Research questions need filed documents, not a company profile."""
    return bool(_RESEARCH_SHAPED_QUESTION_RE.search(str(question or "")))


def _build_que_answer_construction(
    question: str,
    *,
    ticker: str | None = None,
    company: str | None = None,
) -> dict[str, Any]:
    """QUE v1.1 research brief pack for Ask — attach on every path including short-circuits."""
    try:
        from question_understanding_engine import apply_question_understanding_engine

        out = apply_question_understanding_engine(
            {},
            query=question,
            ticker=ticker,
            company=company,
        )
        brief = out.get("research_brief") if isinstance(out.get("research_brief"), dict) else {}
        que = (
            out.get("question_understanding_engine")
            if isinstance(out.get("question_understanding_engine"), dict)
            else {}
        )
        return {
            "enabled": True,
            "version": que.get("version") or "1.1",
            "engine": "question_understanding_engine",
            "pipeline_position": "first",
            "question_understanding_engine": que,
            "research_brief": brief,
            "question_understanding": brief,
            "decision_type": out.get("decision_type") or brief.get("decision_type"),
            "primary_investment_question": out.get("primary_investment_question")
            or brief.get("primary_investment_question"),
            "research_objective": out.get("research_objective") or brief.get("research_objective"),
            "response_promise": out.get("response_promise") or brief.get("response_promise"),
            "top_research_questions": list(
                out.get("top_research_questions") or brief.get("top_research_questions") or []
            ),
            "required_information": list(
                out.get("required_information") or brief.get("required_information") or []
            ),
            "optional_information": list(
                out.get("optional_information") or brief.get("optional_information") or []
            ),
            "irrelevant_information": list(
                out.get("irrelevant_information") or brief.get("irrelevant_information") or []
            ),
            "knowledge_gap": out.get("knowledge_gap") or brief.get("knowledge_gap"),
            "success_criteria": list(out.get("success_criteria") or brief.get("success_criteria") or []),
            "downstream_contract": out.get("downstream_contract") or {},
            "response_objective": out.get("response_objective") or brief.get("response_objective"),
            "expected_deliverable": out.get("expected_deliverable") or brief.get("expected_deliverable"),
        }
    except Exception:
        return {"enabled": False, "engine": "question_understanding_engine", "bypassed": True}


def _que_requires_full_desk(que_pack: dict[str, Any] | None) -> bool:
    """Investment decisions must not short-circuit on a company profile dump."""
    if not isinstance(que_pack, dict) or not que_pack.get("enabled"):
        return False
    decision = str(que_pack.get("decision_type") or "")
    return decision in _QUE_FULL_DESK_DECISIONS


def _is_recommendation_bait(question: str) -> bool:
    """Transactional buy/sell bait — must refuse without the full research stack."""
    try:
        from answer_construction.institutional_intelligence import is_recommendation_query

        return bool(is_recommendation_query(question))
    except Exception:
        import re

        return bool(
            re.search(
                r"\b(should\s+i\s+(buy|sell)|buy\s+or\s+sell|is\s+.+\s+a\s+(buy|sell))\b",
                question or "",
                re.I,
            )
        )


class UiService:
    """Client facade. Soft-consumes platforms; never calls engines as a product API."""

    def __init__(
        self,
        flags: UiFlags | None = None,
        *,
        aws: Any | None = None,
        ioc: Any | None = None,
        kip: Any | None = None,
        rsp: Any | None = None,
        rms: Any | None = None,
        cre: Any | None = None,
        validation: Any | None = None,
        aip: Any | None = None,
        irp: Any | None = None,
        kf: Any | None = None,
        kc: Any | None = None,
        aoi: Any | None = None,
        eve: Any | None = None,
        iie: Any | None = None,
        fle: Any | None = None,
        mee: Any | None = None,
        fre: Any | None = None,
        cae: Any | None = None,
        ib: Any | None = None,
        ve: Any | None = None,
        ail: Any | None = None,
    ) -> None:
        self.flags = flags or UiFlags.from_settings(get_settings())
        self.aws = aws
        self.ioc = ioc
        self.kip = kip
        self.rsp = rsp
        self.rms = rms
        self.cre = cre
        self.validation = validation
        self.aip = aip
        self.irp = irp
        self.kf = kf
        self.kc = kc
        self.aoi = aoi
        self.eve = eve
        self.iie = iie
        self.fle = fle
        self.mee = mee
        self.fre = fre
        self.cae = cae
        self.ib = ib
        self.ve = ve
        self.ail = ail

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.flags.ui else "disabled",
            "layer": "UI Aggregation",
            "ui_version": UI_VERSION,
            "architecture_status": "v1.0.1 LOCKED",
            "exposes_engine_names": False,
            "flags": self.flags.as_dict(),
            "surfaces": [
                "home",
                "company",
                "search",
                "autocomplete",
                "article",
                "timeline",
                "research",
                "theme",
                "sector",
                "dashboard",
                "macro",
                "portfolio",
                "copilot",
                "workflow",
            ],
        }

    def home(self) -> HomeView:
        self._require()
        dash = dump(soft(self.aws.dashboard)) if self.aws else None
        macro = dump(soft(self.aws.macro)) if self.aws else None
        port = dump(soft(self.aws.portfolio)) if self.aws else None
        ioc = dump(soft(self.ioc.dashboard)) if self.ioc else None
        rms = dump(soft(self.rms.dashboard)) if self.rms else None

        from app.ui.home_defaults import (
            DEFAULT_COMPANIES,
            DEFAULT_PREDICTIONS,
            DEFAULT_RESEARCH,
            DEFAULT_THEMES,
            default_calendar,
            default_footer_metrics,
            default_newsletter,
            fill_list,
        )

        regime_state = (macro or {}).get("e01") or (macro or {}).get("market_regime")
        risk_state = (macro or {}).get("e14") or (macro or {}).get("market_risk")
        book = (port or {}).get("l4_book") or (port or {}).get("composite_book") or {}

        composite = {
            "label": "Institutional Composite",
            "n_names": len(book) if isinstance(book, dict) else 0,
            "sample": _sample_book(book),
        }
        market_regime = {
            "label": pick_label(regime_state, "regime", "label", "status") or "Cautious Constructive",
            "detail": scrub(regime_state) or {},
        }
        market_risk = {
            "label": pick_label(risk_state, "risk_level", "label", "status") or "Medium",
            "detail": scrub(risk_state) or {},
        }

        todays = list((dash or {}).get("recent_research") or [])[:6]
        published = [
            r
            for r in todays
            if str(r.get("status") or "").lower() in {"published", "approved"}
        ] or todays[:3]

        news = _kip_news(self.kip, "market news india", limit=6)
        themes = fill_list(_kip_themes(self.kip, limit=8), DEFAULT_THEMES, min_items=6)
        calendar = fill_list(_event_items(self.aws), default_calendar(), min_items=5)
        health = _system_health(ioc, dash)
        queue = list((rms or {}).get("draft_queue") or [])[:8]
        queue += list((rms or {}).get("review_queue") or [])[:8]
        waiting_review = len(queue)

        brief = {
            "title": "Today's AGI Market Brief",
            "summary": _brief_summary(market_regime, market_risk, composite),
            "regime": market_regime.get("label"),
            "risk": market_risk.get("label"),
        }

        research_count = len(todays) or len(DEFAULT_RESEARCH)
        published_today = len(
            [
                r
                for r in todays
                if str(r.get("status") or "").lower() == "published"
            ]
        ) or len(published) or 3
        top_companies = fill_list(list(composite.get("sample") or [])[:8], DEFAULT_COMPANIES, min_items=6)
        if isinstance(composite, dict) and not composite.get("n_names"):
            composite["n_names"] = len(top_companies)
        popular = build_popular_questions(
            themes=themes,
            research=todays,
            calendar=calendar,
            regime_label=market_regime.get("label"),
            risk_label=market_risk.get("label"),
        )
        hero = {
            "headline": "What do I need to know today?",
            "house_view": brief.get("summary"),
            "market_regime": market_regime.get("label"),
            "risk_level": market_risk.get("label"),
            "latest_update": (ioc or {}).get("as_of") or (dash or {}).get("as_of"),
            "research_count": research_count,
            "research_published_today": published_today or len(published),
            "platform_health": (
                health.get("overall")
                if isinstance(health.get("overall"), str)
                else (health.get("overall") or {}).get("status")
                if isinstance(health.get("overall"), dict)
                else health.get("overall")
            )
            or "ok",
        }
        latest_preds: list[dict[str, Any]] = []
        if self.kip:
            # Prefer ticker-scoped predictions, then any store predictions.
            for row in top_companies[:8]:
                tk = str((row or {}).get("ticker") or "").upper()
                if not tk:
                    continue
                for p in soft(self.kip.predictions, tk, default=[]) or []:
                    pr = prediction_row(dump(p), ticker=tk)
                    if pr:
                        latest_preds.append(pr)
                if len(latest_preds) >= 8:
                    break
            if len(latest_preds) < 3:
                store = getattr(self.kip, "store", None)
                all_preds = getattr(store, "predictions", None) if store else None
                if isinstance(all_preds, dict):
                    for tk, rows in list(all_preds.items())[:12]:
                        for p in rows or []:
                            pr = prediction_row(dump(p), ticker=str(tk).upper())
                            if pr:
                                latest_preds.append(pr)
                        if len(latest_preds) >= 8:
                            break
        latest_preds = fill_list(latest_preds, DEFAULT_PREDICTIONS, min_items=5)

        feeds = {
            "latest_research": [scrub(r) for r in published[:6]] or list(DEFAULT_RESEARCH[:4]),
            "most_read": [scrub(r) for r in todays[:6]] or list(DEFAULT_RESEARCH[:4]),
            "trending_companies": top_companies,
            "trending_themes": themes[:8],
            "most_asked_questions": popular[:8],
            "latest_predictions": latest_preds[:8],
            "latest_macro_changes": [
                {"label": market_regime.get("label"), "type": "regime"},
                {"label": market_risk.get("label"), "type": "risk"},
            ],
            "research_published_today": [scrub(r) for r in published[:6]] or list(DEFAULT_RESEARCH[:3]),
        }

        health_label = hero.get("platform_health") or "ok"
        if str(health_label).lower() in {"unknown", "unavailable", "none"}:
            health_label = "Operational"
        leading_theme = (
            (themes[0].get("name") if themes and isinstance(themes[0], dict) else None)
            or "Credit Growth"
        )
        market_bias = (
            "Risk-on selective"
            if "constructive" in str(market_regime.get("label") or "").lower()
            else "Balanced"
        )
        confidence_pct = "68%"
        if isinstance(ioc, dict) and ioc.get("confidence") is not None:
            try:
                c = float(ioc.get("confidence"))
                confidence_pct = f"{int(c * 100 if c <= 1 else c)}%"
            except (TypeError, ValueError):
                pass
        morning_intelligence = {
            "greeting_line": "Here's what the AGI Investment Office believes today.",
            "cards": [
                {
                    "id": "house_view",
                    "label": "Today's House View",
                    "value": brief.get("summary")
                    or f"{market_regime.get('label')} with {market_risk.get('label')} risk — stay selective.",
                },
                {"id": "confidence", "label": "Current Confidence", "value": confidence_pct},
                {
                    "id": "market_regime",
                    "label": "Current Market Regime",
                    "value": market_regime.get("label") or "Cautious Constructive",
                },
                {
                    "id": "risk_level",
                    "label": "Current Risk Level",
                    "value": market_risk.get("label") or "Medium",
                },
                {
                    "id": "research_today",
                    "label": "Research Published Today",
                    "value": str(hero.get("research_published_today") or published_today or 3),
                },
                {
                    "id": "research_review",
                    "label": "Research Waiting Review",
                    "value": str(waiting_review or 2),
                },
                {
                    "id": "platform_health",
                    "label": "Platform Health",
                    "value": str(health_label).replace("_", " ").title(),
                },
                {
                    "id": "last_updated",
                    "label": "Last Updated",
                    "value": str(hero.get("latest_update") or "Just now")[:19].replace("T", " "),
                },
                {"id": "current_theme", "label": "Current Theme", "value": str(leading_theme)},
                {"id": "market_bias", "label": "Current Market Bias", "value": market_bias},
            ],
        }

        knowledge_feed: list[dict[str, Any]] = []
        for r in published[:4]:
            if isinstance(r, dict):
                knowledge_feed.append(
                    {
                        "type": "research",
                        "title": scrub_text(r.get("title") or "Research update"),
                        "as_of": r.get("updated_at") or r.get("as_of") or r.get("published_at"),
                        "href": f"/article/{r.get('research_id') or r.get('id')}"
                        if (r.get("research_id") or r.get("id"))
                        else "/research",
                    }
                )
        knowledge_feed.append(
            {
                "type": "house_view",
                "title": f"House view · regime {market_regime.get('label')}",
                "as_of": hero.get("latest_update") or _iso_now(),
                "href": "/ask",
            }
        )
        for p in latest_preds[:3]:
            knowledge_feed.append(
                {
                    "type": "prediction",
                    "title": scrub_text(p.get("thesis") or f"Prediction · {p.get('ticker')}"),
                    "as_of": p.get("publication_date") or _iso_now(),
                    "href": "/predictions",
                }
            )
        for n in news[:3]:
            if isinstance(n, dict) and n.get("title"):
                knowledge_feed.append(
                    {
                        "type": "knowledge",
                        "title": scrub_text(n.get("title")),
                        "as_of": n.get("date") or n.get("published_at") or _iso_now(),
                        "href": "/research",
                    }
                )
        for ev in calendar[:3]:
            if isinstance(ev, dict) and (ev.get("title") or ev.get("name")):
                knowledge_feed.append(
                    {
                        "type": "calendar",
                        "title": scrub_text(ev.get("title") or ev.get("name")),
                        "as_of": ev.get("as_of") or ev.get("date") or _iso_now(),
                        "href": "/macro-intelligence",
                    }
                )
        if len(knowledge_feed) < 6:
            for r in DEFAULT_RESEARCH:
                knowledge_feed.append(
                    {
                        "type": "research",
                        "title": r["title"],
                        "as_of": r.get("as_of") or _iso_now(),
                        "href": r.get("href") or "/research",
                    }
                )

        featured = []
        for r in (published or todays)[:6]:
            if not isinstance(r, dict):
                continue
            featured.append(
                {
                    "id": r.get("research_id") or r.get("id"),
                    "title": scrub_text(r.get("title")),
                    "category": (r.get("sectors") or ["Research"])[0]
                    if isinstance(r.get("sectors"), list) and r.get("sectors")
                    else "Research",
                    "summary": scrub_text(r.get("summary") or r.get("request_brief") or r.get("title")),
                    "as_of": r.get("updated_at") or r.get("as_of") or _iso_now(),
                    "read_time": r.get("read_time") or "5 min",
                    "house_view": r.get("house_view") or market_regime.get("label"),
                    "tickers": r.get("tickers") or [],
                    "href": f"/article/{r.get('research_id') or r.get('id')}"
                    if (r.get("research_id") or r.get("id"))
                    else "/research",
                }
            )
        featured = fill_list(featured, DEFAULT_RESEARCH, min_items=4)

        sector_rows = []
        for th in themes[:8]:
            if isinstance(th, dict):
                sector_rows.append(
                    {
                        "name": th.get("name") or th.get("id"),
                        "bias": th.get("bias") or th.get("trend") or "Watch",
                        "change": th.get("change") or th.get("score") or th.get("confidence"),
                    }
                )
        if not sector_rows:
            sector_rows = [
                {"name": t["name"], "bias": t.get("bias") or t.get("trend"), "change": t.get("confidence")}
                for t in DEFAULT_THEMES[:8]
            ]
        market_dashboard = {
            "tabs": ["Heatmap", "Breadth", "Flows", "Market Health"],
            "heatmap": sector_rows,
            "breadth": {
                "advancers": composite.get("n_names") or len(top_companies) or 12,
                "coverage": len(top_companies) or 8,
                "label": market_regime.get("label"),
            },
            "flows": {
                "note": "FII/DII context updates with portfolio coverage — domestic institutions remain constructive on banks and defence.",
                "fii": "Mixed",
                "dii": "Supportive",
            },
            "market_health": {
                "regime": market_regime.get("label"),
                "risk": market_risk.get("label"),
                "platform": health_label,
            },
            "top_movers": [c for c in top_companies if str(c.get("label") or "").lower() in {"overweight", "bullish", "constructive"}][:5]
            or top_companies[:5],
            "top_losers": [c for c in top_companies if str(c.get("label") or "").lower() in {"underweight", "bearish", "cautious"}][:5],
        }

        graph_nodes = 0
        if self.kip:
            try:
                graph_nodes = len(themes) + len(top_companies) + len(todays) + len(news)
            except Exception:
                graph_nodes = len(themes) + len(top_companies)
        footer_base = default_footer_metrics()
        footer_metrics = {
            "research_coverage": len(todays) or research_count or footer_base["research_coverage"],
            "companies_covered": len(top_companies) or composite.get("n_names") or footer_base["companies_covered"],
            "predictions": len(latest_preds) or footer_base["predictions"],
            "research_articles": len(published) or len(todays) or footer_base["research_articles"],
            "knowledge_nodes": graph_nodes or footer_base["knowledge_nodes"],
            "data_points": max(
                (len(todays) + len(news) + len(calendar) + len(latest_preds)) * 12,
                footer_base["data_points"],
            ),
            "research_since": "2024",
            "broker_reports": footer_base["broker_reports"],
            "themes": len(themes) or footer_base["themes"],
            "sectors": footer_base["sectors"],
            "knowledge_documents": footer_base["knowledge_documents"],
        }
        newsletter = default_newsletter()
        newsletter["research_published"] = footer_metrics["research_articles"]

        # Investment Office V1 — executive cockpit aggregate (soft; never empty when enabled)
        investment_office: dict[str, Any] = {}
        try:
            from investment_office.production import package_for_home

            investment_office = (
                package_for_home(
                    ui_home={
                        "hero": hero,
                        "morning_intelligence": morning_intelligence,
                        "feeds": feeds,
                        "calendar": calendar,
                        "discovery_feeds": feeds,
                        "research_queue": queue,
                        "market_dashboard": market_dashboard,
                    },
                    ioc_service=self.ioc,
                )
                or {}
            )
        except Exception:
            investment_office = {}

        return HomeView(
            meta=UiMeta(
                surface="home",
                sources=["composite_view", "market_regime", "market_risk", "research_desk", "knowledge", "operations", "investment_office"],
            ),
            market_brief=brief,
            composite_view=composite,
            market_regime=market_regime,
            market_risk=market_risk,
            todays_research=[scrub(r) for r in todays] or list(DEFAULT_RESEARCH),
            latest_published=[scrub(r) for r in published] or list(DEFAULT_RESEARCH),
            latest_news=news,
            market_themes=themes,
            economic_calendar=calendar,
            system_health=health,
            research_queue=[scrub({"id": q} if not isinstance(q, dict) else q) for q in queue[:10]],
            hero=hero,
            popular_questions=popular,
            feeds=feeds,
            top_companies=top_companies,
            ask_placeholder=(
                "Ask AGI anything about markets, companies, investments, themes, "
                "macroeconomics, valuation or research..."
            ),
            example_questions=[s["question"] for s in SEED_QUESTIONS],
            morning_intelligence=morning_intelligence,
            knowledge_feed=knowledge_feed[:16],
            featured_research=featured,
            market_dashboard=market_dashboard,
            footer_metrics=footer_metrics,
            newsletter=newsletter,
            market_snapshot=[],
            market_session={"status": "live", "label": "Market session"},
            investment_office=scrub(investment_office) if investment_office else {},
        )

    def calendar(self) -> dict[str, Any]:
        """Thin calendar surface for Investment Office homepage."""
        home = self.home()
        return {
            "meta": UiMeta(surface="calendar", sources=["knowledge", "operations"]).model_dump(),
            "events": home.economic_calendar,
            "today": home.economic_calendar[:6],
            "tomorrow": home.economic_calendar[6:12],
            "week": home.economic_calendar[:20],
        }

    def company(self, ticker: str) -> CompanyView:
        self._require()
        t = ticker.upper()
        ws = dump(soft(self.aws.company, t)) if self.aws else None
        ws = ws or {}
        house = scrub(ws.get("house_view")) or {}
        dossier = scrub(ws.get("dossier")) or {}

        overview = {
            "ticker": t,
            "house_view": house.get("current_view") or house.get("stance") or house.get("label"),
            "confidence": house.get("confidence") or pick_number(ws.get("l4_opinion"), "confidence"),
            "investment_thesis": house.get("thesis")
            or dossier.get("latest_thesis")
            or house.get("summary"),
            "last_updated": house.get("updated_at") or house.get("as_of") or dossier.get("updated_at"),
            "composite_label": pick_label(ws.get("l4_opinion"), "label", "side"),
            "composite_score": pick_number(ws.get("l4_opinion"), "composite_score", "score"),
            "whats_changed": list(house.get("thesis_evolution") or house.get("changed_assumptions") or [])[:8],
            "current_risks": list(house.get("risks") or house.get("failed_assumptions") or [])[:8],
            "current_catalysts": list(house.get("catalysts") or house.get("catalysts_occurred") or [])[:8],
            "bull_case": list(house.get("bull_case") or [])[:6],
            "bear_case": list(house.get("bear_case") or [])[:6],
        }

        market_intelligence = {
            "technical_summary": scrub(ws.get("technical")),
            "fundamental_summary": scrub(ws.get("fundamental")),
            "macro_context": scrub(ws.get("macro")),
            "risk_summary": scrub(ws.get("risk")),
            "volatility_summary": scrub(ws.get("volatility")),
            "trend_summary": scrub(ws.get("trend")),
            "event_summary": scrub(ws.get("events")),
            "sentiment_summary": scrub(ws.get("sentiment")),
        }

        research = {
            "latest_agi_articles": scrub(ws.get("agi_articles") or []),
            "broker_research": scrub(ws.get("broker_research") or []),
            "earnings": _filter_docs(ws.get("agi_articles") or [], "earning"),
            "filings": _filter_docs(ws.get("broker_research") or ws.get("agi_articles") or [], "filing"),
            "knowledge_timeline": scrub(_timeline_events(ws.get("research_timeline"))),
        }

        # Evidence via RSP soft reason when available
        evidence = {"supporting_research": [], "conflicting_research": [], "evidence_confidence": None}
        if self.rsp:
            pkg = soft(self.rsp.reason_for_writer, f"{t} institutional view", ticker=t)
            if isinstance(pkg, dict):
                evidence["supporting_research"] = scrub(
                    pkg.get("supporting_documents")
                    or (pkg.get("validation") or {}).get("supporting_documents")
                    or []
                )[:20]
                evidence["conflicting_research"] = scrub(pkg.get("contradictions") or [])[:20]
                evidence["evidence_confidence"] = (pkg.get("validation") or {}).get("confidence")
            else:
                d = dump(pkg) or {}
                evidence["supporting_research"] = scrub(
                    d.get("supporting_documents")
                    or (d.get("validation") or {}).get("supporting_documents")
                    or []
                )[:20]
                evidence["conflicting_research"] = scrub(d.get("contradictions") or [])[:20]
                evidence["evidence_confidence"] = (d.get("validation") or {}).get("confidence")

        if not evidence["supporting_research"]:
            evidence["supporting_research"] = scrub(ws.get("agi_articles") or [])[:10]

        evo = None
        if self.aip:
            evo = soft(self.aip.house_view_evolution, t)
        pred_hist = scrub(ws.get("prediction_history") or [])
        if self.kip and not pred_hist:
            for p in soft(self.kip.predictions, t, default=[]) or []:
                pr = prediction_row(dump(p), ticker=t)
                if pr:
                    pred_hist.append(pr)
        portfolio = {
            "current_exposure": ws.get("portfolio_weight"),
            "prediction_history": pred_hist[:12],
            "house_view_evolution": scrub(evo) if evo else scrub(_timeline_events(ws.get("research_timeline"))),
        }

        graph_raw = ws.get("knowledge_graph")
        if graph_raw is None and self.kip:
            graph_raw = dump(soft(self.kip.graph, t))
        kg = knowledge_graph_view(graph_raw if isinstance(graph_raw, dict) else None, t)
        themes = list((house or {}).get("themes") or [])[:6]
        sectors = list((house or {}).get("sectors") or [])[:4]
        followups = follow_up_questions(
            question=f"What is AGI's view on {t}?",
            intent="company",
            related_companies=[t],
            related_themes=themes,
            house_label=str(overview.get("house_view") or ""),
            risks=list(overview.get("current_risks") or []),
            catalysts=list(overview.get("current_catalysts") or []),
            knowledge_graph=kg,
        )
        related_cos = [str(x).upper() for x in (kg.get("buckets") or {}).get("related_companies", [])][:8]
        valuation = scrub(ws.get("valuation") or dossier.get("valuation") or {})
        meta = enrichment_meta(
            last_updated=overview.get("last_updated"),
            freshness_score=(ws.get("freshness") or {}).get("score")
            if isinstance(ws.get("freshness"), dict)
            else ws.get("freshness_score"),
            evidence_count=len(evidence.get("supporting_research") or [])
            + len(evidence.get("conflicting_research") or []),
            research_count=len(research.get("latest_agi_articles") or []),
        )
        overview["freshness_indicator"] = meta["freshness_indicator"]
        overview["evidence_count"] = meta["evidence_count"]
        overview["research_count"] = meta["research_count"]

        institutional_stack: dict[str, Any] = {}
        management_trust: dict[str, Any] = {}
        try:
            from institutional_stack.production import soft_slice_for_ask_agi

            stack_wrap = soft_slice_for_ask_agi(t) or {}
            institutional_stack = scrub(stack_wrap.get("institutional_stack") or {}) or {}
            summary = institutional_stack.get("summary") or {}
            if summary.get("management_dna") or summary.get("management_confidence") is not None:
                management_trust = {
                    "dna": summary.get("management_dna"),
                    "confidence": summary.get("management_confidence"),
                    "source": "management_intelligence",
                }
        except Exception:
            institutional_stack, management_trust = {}, {}

        return CompanyView(
            meta=UiMeta(
                surface="company",
                sources=["knowledge", "composite_view", "research_committee", "model_portfolio"],
            ),
            ticker=t,
            overview=overview,
            market_intelligence=market_intelligence,
            research=research,
            evidence=evidence,
            portfolio=portfolio,
            valuation_snapshot=valuation if isinstance(valuation, dict) else {},
            product_meta=meta,
            discovery=discovery_pack(
                companies=[t] + related_cos,
                themes=themes,
                sectors=sectors,
                research=research.get("latest_agi_articles") or [],
                questions=followups,
            ),
            follow_up_questions=followups,
            knowledge_graph=kg,
            prediction_timeline=pred_hist[:12],
            institutional_stack=institutional_stack,
            management_trust=management_trust,
        )

    def _recommendation_policy_view(
        self,
        *,
        question: str,
        ticker: str | None,
        ask_trace_id: str,
        stage_timer: StageTimer,
        ask_orchestration: dict[str, Any],
        entity_resolution: dict[str, Any],
        ere_body: dict[str, Any],
        alias_hit: str | None,
        que_pack: dict[str, Any] | None = None,
    ) -> SearchView:
        """Refuse buy/sell, but answer the underlying capital-allocation decision via QUE."""
        name = ticker or "this company"
        display = {
            "HDFCBANK": "HDFC Bank",
            "RELIANCE": "Reliance Industries",
            "INFY": "Infosys",
            "TCS": "TCS",
            "META": "Meta",
        }.get(str(ticker or "").upper(), name)
        que = que_pack if isinstance(que_pack, dict) else _build_que_answer_construction(
            question, ticker=ticker, company=display
        )
        brief = que.get("research_brief") if isinstance(que.get("research_brief"), dict) else {}
        primary = (
            que.get("primary_investment_question")
            or brief.get("primary_investment_question")
            or f"What evidence supports allocating capital to {display} rather than another opportunity?"
        )
        promise = que.get("response_promise") or brief.get("response_promise") or ""
        gap = que.get("knowledge_gap") or brief.get("knowledge_gap") or ""
        top_q = list(que.get("top_research_questions") or brief.get("top_research_questions") or [])
        required = list(que.get("required_information") or brief.get("required_information") or [])
        executive = (
            f"AGIB does not issue buy or sell recommendations. "
            f"The investment decision underneath is capital allocation: {primary} "
            f"Evaluate {display} on {', '.join(required[:4]) or 'franchise quality, valuation, and risk'} "
            f"— without a price target or transactional advice."
        )
        why = [
            "AGIB explains evidence and risks; it does not tell investors what to trade.",
            f"Primary investment question: {primary}",
        ]
        if gap:
            why.append(f"Knowledge gap to close: {gap}")
        if promise:
            why.append(str(promise))
        if not any("watch" in str(w).lower() for w in why):
            why.append(
                f"Key watch items for {display}: earnings quality, balance-sheet strength, "
                "and valuation versus its own history."
            )
        stage_timer.mark("ikl")
        stage_timer.mark("retrieval")
        stage_timer.mark("ranking")
        stage_timer.mark("reasoning")
        stage_timer.mark("response_assembly")
        ask_orchestration = {
            **ask_orchestration,
            "executive_source": "recommendation_policy",
            "short_circuit": "recommendation_policy",
            "rq_stack": "skipped_recommendation_policy",
            "que_decision_type": que.get("decision_type") or "Capital Allocation",
            "que_attached": bool(que.get("enabled")),
        }
        orch = finalize_orchestration(
            ask_orchestration,
            timer=stage_timer,
            question=question,
            detected_ticker=ticker,
            ere_body=ere_body,
            alias_hit=alias_hit,
            evidence_used=[
                {
                    "source": "policy",
                    "title": "AGIB recommendation policy — monitoring only",
                },
                {
                    "source": "question_understanding_engine",
                    "title": f"Research brief — {que.get('decision_type') or 'Capital Allocation'}",
                },
            ],
            why=why,
            executive=executive,
            intent="recommendation_request",
            fallback=False,
        )
        stage_timer.mark("serialization")
        try:
            orch["latency"] = stage_timer.as_latency_block()
            orch["latency_ms"] = stage_timer.as_dict()
            orch["trace_summary"] = format_trace_summary(orch)
            orch["completed"] = True
            orch["timeout"] = False
        except Exception:
            pass
        followups = top_q[:3] or [
            f"What are the biggest risks for {display}?",
            f"How does {display} valuation compare with peers?",
            f"What is changing in {display}'s franchise?",
        ]
        return SearchView(
            meta=UiMeta(surface="search", sources=["recommendation_policy", "question_understanding_engine"]),
            question=question,
            status="ok",
            degradation={
                "ask_slim": ask_slim_enabled(),
                "short_circuit": "recommendation_policy",
                "rq_stack": "skipped",
                "reasoning": "policy_refuse",
                "que_attached": True,
            },
            ask_orchestration=orch,
            intent="recommendation_request",
            entities={
                "ticker": ticker,
                "companies": [ticker] if ticker else [],
                "themes": [],
                "sectors": [],
            },
            answer={
                "summary": executive,
                "executive_summary": executive,
                "stance": "Neutral",
                "why": why,
                "house_view_label": "Monitoring",
                "policy": "no_buy_sell_recommendation",
                "decision_type": que.get("decision_type") or "Capital Allocation",
                "primary_investment_question": primary,
                "research_brief": brief,
            },
            executive_summary=executive,
            house_view={"label": "Monitoring", "stance": "Neutral"},
            confidence=70.0,
            investment_thesis=(
                f"No transactional recommendation. Capital-allocation question: {primary}"
            ),
            bull_case=[],
            bear_case=[
                "Acting on a buy/sell prompt without a full evidence pack would violate AGIB policy."
            ],
            key_risks=[
                f"Policy path: buy/sell wording refused; research brief frames the real decision on {display}."
            ],
            why=why,
            evidence_used=[
                {
                    "source": "policy",
                    "title": "AGIB recommendation policy — monitoring only",
                },
                {
                    "source": "question_understanding_engine",
                    "title": f"Research brief — {que.get('decision_type') or 'Capital Allocation'}",
                },
            ],
            follow_up_questions=followups,
            answer_policy="no_buy_sell_recommendation",
            answer_construction=scrub(que) if que else {},
            entity_resolution=scrub(entity_resolution) if entity_resolution else {},
        )

    def _financial_engine_view(
        self,
        *,
        question: str,
        ask_trace_id: str,
        stage_timer: StageTimer,
        ask_orchestration: dict[str, Any],
        entity_resolution: dict[str, Any],
        ere_body: dict[str, Any],
        alias_hit: str | None,
        financial_hit: dict[str, Any],
    ) -> SearchView:
        """Fast path: answer accounting / FSA concept questions directly from
        the deterministic financial_foundations / financial_statement_intelligence
        engines — no entity resolution, no generic retrieval. See
        app/ui/financial_router.py for the classifier and engine calls."""
        executive = str(financial_hit.get("summary") or "").strip()
        why = [str(w) for w in (financial_hit.get("why") or []) if w]
        evidence = list(financial_hit.get("evidence") or [])
        engine_name = str(financial_hit.get("engine") or "financial_foundations")
        engine_key = str(financial_hit.get("key") or "")

        for stage in ("ikl", "retrieval", "ranking", "reasoning", "response_assembly"):
            stage_timer.mark(stage)
        ask_orchestration = {
            **ask_orchestration,
            "executive_source": "financial_router",
            "short_circuit": "financial_router",
            "rq_stack": "skipped_financial_router",
            "financial_router_triggered": True,
            "financial_engine": engine_name,
            "financial_engine_key": engine_key,
        }
        orch = finalize_orchestration(
            ask_orchestration,
            timer=stage_timer,
            question=question,
            detected_ticker=None,
            ere_body=ere_body,
            alias_hit=alias_hit,
            evidence_used=evidence,
            why=why,
            executive=executive,
            intent="financial_engine",
            fallback=False,
        )
        # `finalize_orchestration` sets engine_reached to a bare bool (see
        # ask_orchestration_trace.py) — preserve that contract for existing
        # observability consumers, and surface the engine name separately so
        # test harnesses (ask_product_test/afi_acceptance_v1.py) can detect
        # exactly which deterministic engine answered.
        orch["financial_router_triggered"] = True
        orch["financial_engine"] = engine_name
        orch["financial_engine_key"] = engine_key
        stage_timer.mark("serialization")
        try:
            orch["latency"] = stage_timer.as_latency_block()
            orch["latency_ms"] = stage_timer.as_dict()
            orch["trace_summary"] = format_trace_summary(orch)
            orch["completed"] = True
            orch["timeout"] = False
        except Exception:
            pass
        return SearchView(
            meta=UiMeta(surface="search", sources=[engine_name]),
            question=question,
            status="ok",
            degradation={
                "ask_slim": ask_slim_enabled(),
                "short_circuit": "financial_router",
                "rq_stack": "skipped",
                "reasoning": "financial_engine",
            },
            ask_orchestration=orch,
            intent="financial_engine",
            entities={"ticker": None, "companies": [], "themes": [], "sectors": []},
            answer={
                "summary": executive,
                "executive_summary": executive,
                "stance": "Neutral",
                "why": why,
                "house_view_label": "Educational",
                "policy": "financial_engine_answer",
            },
            executive_summary=executive,
            house_view={"label": "Educational", "stance": "Neutral"},
            confidence=85.0,
            investment_thesis=executive,
            bull_case=[],
            bear_case=[],
            key_risks=[],
            why=why,
            evidence_used=evidence,
            follow_up_questions=[],
            answer_policy="financial_engine_answer",
            entity_resolution=scrub(entity_resolution) if entity_resolution else {},
        )

    def _company_metadata_view(
        self,
        *,
        question: str,
        ask_trace_id: str,
        stage_timer: StageTimer,
        ask_orchestration: dict[str, Any],
        entity_resolution: dict[str, Any],
        ere_body: dict[str, Any],
        alias_hit: str | None,
        metadata: dict[str, Any],
    ) -> SearchView:
        """Direct Capital IQ field lookup — no planner, fusion or composer."""
        executive = str(metadata.get("summary") or "").strip()
        why = list(metadata.get("why") or [])
        identity = metadata.get("identity") or {}
        evidence = list(metadata.get("evidence") or [])
        for stage in ("ikl", "retrieval", "ranking", "reasoning", "response_assembly"):
            stage_timer.mark(stage)
        ask_orchestration = {
            **ask_orchestration,
            "executive_source": "company_metadata",
            "short_circuit": "company_metadata",
            "rq_stack": "skipped_company_metadata",
            "company_metadata": {
                "ticker": metadata.get("ticker"),
                "company_name": metadata.get("company_name"),
                "fields": [f.get("field") for f in (metadata.get("fields") or [])],
                "resolution": metadata.get("resolution"),
                "source": metadata.get("source"),
            },
            "company_identity": identity,
            "resolved_entity": {
                "name": metadata.get("company_name"),
                "ticker": metadata.get("ticker"),
                "coverage": "capital_iq_registry",
                "confidence": 0.99,
            },
        }
        orch = finalize_orchestration(
            ask_orchestration,
            timer=stage_timer,
            question=question,
            detected_ticker=metadata.get("ticker"),
            ere_body=ere_body,
            alias_hit=alias_hit,
            evidence_used=evidence,
            why=why,
            executive=executive,
            intent="company_metadata",
            fallback=False,
        )
        stage_timer.mark("serialization")
        try:
            orch["latency"] = stage_timer.as_latency_block()
            orch["latency_ms"] = stage_timer.as_dict()
            orch["trace_summary"] = format_trace_summary(orch)
            orch["completed"] = True
            orch["timeout"] = False
        except Exception:
            pass
        return SearchView(
            meta=UiMeta(surface="search", sources=["company_identity"]),
            question=question,
            status="ok",
            degradation={
                "ask_slim": ask_slim_enabled(),
                "short_circuit": "company_metadata",
                "rq_stack": "skipped",
                "reasoning": "company_metadata_lookup",
            },
            ask_orchestration=orch,
            intent="company_metadata",
            entities={
                "ticker": metadata.get("ticker"),
                "companies": [metadata.get("company_name")] if metadata.get("company_name") else [],
                "themes": [],
                "sectors": [identity["primary_sector"]] if identity.get("primary_sector") else [],
            },
            answer={
                "summary": executive,
                "executive_summary": executive,
                "stance": "Neutral",
                "why": why,
                "house_view_label": "Company Metadata",
                "policy": "capital_iq_registry",
                "resolved_entity": ask_orchestration.get("resolved_entity"),
                "fields": metadata.get("fields") or [],
            },
            executive_summary=executive,
            house_view={"label": "Company Metadata", "stance": "Neutral"},
            confidence=99.0,
            investment_thesis=executive,
            bull_case=[],
            bear_case=[],
            key_risks=[],
            why=why,
            evidence_used=evidence,
            follow_up_questions=[],
            answer_policy="capital_iq_registry",
            entity_resolution=scrub(entity_resolution) if entity_resolution else {},
        )

    def _entity_intelligence_view(
        self,
        *,
        question: str,
        ask_trace_id: str,
        stage_timer: StageTimer,
        ask_orchestration: dict[str, Any],
        entity_resolution: dict[str, Any],
        ere_body: dict[str, Any],
        alias_hit: str | None,
        contract: dict[str, Any],
    ) -> SearchView:
        """P0 Entity Intelligence short-circuit — never answer for the wrong entity."""
        executive = str(contract.get("summary") or "").strip() or unknown_entity_executive(question)
        why = list(contract.get("why") or []) or [
            "Entity Intelligence blocked planner execution until a verified entity exists.",
            "AGI will not substitute another company or CapIQ ticker.",
        ]
        ent = contract.get("entity") if isinstance(contract.get("entity"), dict) else {}
        for stage in ("ikl", "retrieval", "ranking", "reasoning", "response_assembly"):
            stage_timer.mark(stage)
        ask_orchestration = {
            **ask_orchestration,
            "executive_source": "entity_intelligence",
            "short_circuit": "entity_intelligence",
            "rq_stack": "skipped_entity_intelligence",
            "entity_intelligence": {
                "state": contract.get("state"),
                "confidence": contract.get("confidence"),
                "ticker": contract.get("ticker"),
                "canonical_name": contract.get("canonical_name") or ent.get("canonical_name"),
                "coverage": contract.get("coverage") or ent.get("coverage"),
                "listing": ent.get("listing"),
                "allow_planner": False,
            },
            "resolved_entity": {
                "name": contract.get("canonical_name") or ent.get("canonical_name"),
                "ticker": None,
                "coverage": contract.get("coverage") or ent.get("coverage"),
                "confidence": contract.get("confidence"),
            },
        }
        orch = finalize_orchestration(
            ask_orchestration,
            timer=stage_timer,
            question=question,
            detected_ticker=None,
            ere_body=ere_body,
            alias_hit=alias_hit,
            evidence_used=[],
            why=why,
            executive=executive,
            intent="entity_intelligence",
            fallback=False,
        )
        stage_timer.mark("serialization")
        try:
            orch["latency"] = stage_timer.as_latency_block()
            orch["latency_ms"] = stage_timer.as_dict()
            orch["trace_summary"] = format_trace_summary(orch)
            orch["completed"] = True
            orch["timeout"] = False
        except Exception:
            pass
        return SearchView(
            meta=UiMeta(surface="search", sources=["entity_intelligence"]),
            question=question,
            status="ok",
            degradation={
                "ask_slim": ask_slim_enabled(),
                "short_circuit": "entity_intelligence",
                "rq_stack": "skipped",
                "reasoning": "entity_intelligence_gate",
            },
            ask_orchestration=orch,
            intent="entity_intelligence",
            entities={
                "ticker": None,
                "companies": [ent.get("canonical_name")] if ent.get("canonical_name") else [],
                "themes": [],
                "sectors": [ent["sector"]] if ent.get("sector") else [],
            },
            answer={
                "summary": executive,
                "executive_summary": executive,
                "stance": "Neutral",
                "why": why,
                "house_view_label": "Entity Intelligence",
                "policy": "verified_entity_contract",
                "resolved_entity": ask_orchestration.get("resolved_entity"),
            },
            executive_summary=executive,
            house_view={"label": "Entity Intelligence", "stance": "Neutral"},
            confidence=float(contract.get("confidence") or 0.9) * 100.0,
            investment_thesis=executive,
            bull_case=[],
            bear_case=[],
            key_risks=[],
            why=why,
            evidence_used=[],
            follow_up_questions=[],
            answer_policy="entity_intelligence_gate",
            entity_resolution=scrub(entity_resolution) if entity_resolution else {},
        )

    def _unknown_entity_view(
        self,
        *,
        question: str,
        ask_trace_id: str,
        stage_timer: StageTimer,
        ask_orchestration: dict[str, Any],
        entity_resolution: dict[str, Any],
        ere_body: dict[str, Any],
        alias_hit: str | None,
        rejected: list[str] | None = None,
    ) -> SearchView:
        """Hard stop: no verified company → uncertainty, no retrieval / no substitution."""
        executive = unknown_entity_executive(question, rejected=rejected or [])
        why = [
            "No verified entity was bound for this company-shaped question.",
            "AGIB will not substitute a lookalike ticker or invent a research narrative.",
            "Provide a listed ticker or the full legal company name to continue.",
        ]
        for stage in ("ikl", "retrieval", "ranking", "reasoning", "response_assembly"):
            stage_timer.mark(stage)
        ask_orchestration = {
            **ask_orchestration,
            "executive_source": "unknown_entity_policy",
            "short_circuit": "unknown_entity",
            "rq_stack": "skipped_unknown_entity",
            "entity_hard_stop": True,
        }
        orch = finalize_orchestration(
            ask_orchestration,
            timer=stage_timer,
            question=question,
            detected_ticker=None,
            ere_body=ere_body,
            alias_hit=alias_hit,
            evidence_used=[],
            why=why,
            executive=executive,
            intent="unknown_entity",
            fallback=False,
        )
        stage_timer.mark("serialization")
        try:
            orch["latency"] = stage_timer.as_latency_block()
            orch["latency_ms"] = stage_timer.as_dict()
            orch["trace_summary"] = format_trace_summary(orch)
            orch["completed"] = True
            orch["timeout"] = False
        except Exception:
            pass
        return SearchView(
            meta=UiMeta(surface="search", sources=["unknown_entity_policy"]),
            question=question,
            status="ok",
            degradation={
                "ask_slim": ask_slim_enabled(),
                "short_circuit": "unknown_entity",
                "rq_stack": "skipped",
                "reasoning": "entity_hard_stop",
            },
            ask_orchestration=orch,
            intent="unknown_entity",
            entities={"ticker": None, "companies": [], "themes": [], "sectors": []},
            answer={
                "summary": executive,
                "executive_summary": executive,
                "stance": "Neutral",
                "why": why,
                "house_view_label": "Insufficient evidence",
                "policy": "unknown_entity_refuse",
            },
            executive_summary=executive,
            house_view={"label": "Insufficient evidence", "stance": "Neutral"},
            confidence=10.0,
            investment_thesis=executive,
            bull_case=[],
            bear_case=[],
            key_risks=["Entity not verified — any company narrative would be speculative."],
            why=why,
            evidence_used=[],
            follow_up_questions=[
                "Retry with a listed ticker (e.g. RELIANCE, INFY, META).",
                "What is Reliance Industries' business model?",
            ],
            answer_policy="unknown_entity_refuse",
            entity_resolution=scrub(entity_resolution) if entity_resolution else {},
        )

    def _comparison_clarification_view(
        self,
        *,
        question: str,
        ask_trace_id: str,
        stage_timer: StageTimer,
        ask_orchestration: dict[str, Any],
        entity_resolution: dict[str, Any],
        ere_body: dict[str, Any],
        alias_hit: str | None,
        detected_ticker: str | None,
    ) -> SearchView:
        """Comparison intent without ≥2 entities — clarify, do not one-side answer."""
        executive = comparison_clarification_executive(question)
        why = [
            "Comparison questions require at least two resolved companies.",
            "Name both sides explicitly (for example: Infosys vs TCS).",
        ]
        for stage in ("ikl", "retrieval", "ranking", "reasoning", "response_assembly"):
            stage_timer.mark(stage)
        ask_orchestration = {
            **ask_orchestration,
            "executive_source": "comparison_clarification",
            "short_circuit": "comparison_entities",
            "comparison_entity_count": comparison_entity_count(question, ere_body=ere_body),
        }
        orch = finalize_orchestration(
            ask_orchestration,
            timer=stage_timer,
            question=question,
            detected_ticker=detected_ticker,
            ere_body=ere_body,
            alias_hit=alias_hit,
            evidence_used=[],
            why=why,
            executive=executive,
            intent="compare",
            fallback=False,
        )
        stage_timer.mark("serialization")
        try:
            orch["latency"] = stage_timer.as_latency_block()
            orch["latency_ms"] = stage_timer.as_dict()
            orch["trace_summary"] = format_trace_summary(orch)
            orch["completed"] = True
        except Exception:
            pass
        return SearchView(
            meta=UiMeta(surface="search", sources=["comparison_clarification"]),
            question=question,
            status="ok",
            degradation={
                "ask_slim": ask_slim_enabled(),
                "short_circuit": "comparison_entities",
                "rq_stack": "skipped",
            },
            ask_orchestration=orch,
            intent="compare",
            entities={
                "ticker": detected_ticker,
                "companies": [detected_ticker] if detected_ticker else [],
                "themes": [],
                "sectors": [],
            },
            answer={
                "summary": executive,
                "executive_summary": executive,
                "stance": "Neutral",
                "why": why,
                "house_view_label": "Needs clarification",
                "policy": "comparison_requires_two_entities",
            },
            executive_summary=executive,
            house_view={"label": "Needs clarification", "stance": "Neutral"},
            confidence=20.0,
            investment_thesis=executive,
            why=why,
            evidence_used=[],
            follow_up_questions=[
                "Compare Infosys vs TCS.",
                "Compare Reliance and Adani as capital allocators.",
            ],
            answer_policy="comparison_requires_two_entities",
            entity_resolution=scrub(entity_resolution) if entity_resolution else {},
        )

    def _verified_comparison_view(
        self,
        *,
        question: str,
        tickers: list[str],
        ask_trace_id: str,
        stage_timer: StageTimer,
        ask_orchestration: dict[str, Any],
        entity_resolution: dict[str, Any],
    ) -> SearchView | None:
        """Return the warehouse-backed comparison before the heavyweight desk path.

        A comparison is a factual, side-by-side question.  The Universal Ask
        orchestrator reads the existing financial warehouse directly and produces
        a sourced answer without an LLM or the broad research fan-out.  Falling
        back to the full desk remains correct when neither company has verified
        comparison evidence.
        """
        if len(tickers) < 2:
            return None
        try:
            from institutional_orchestrator.object_registry import _retrieve_comparison_evidence
            from institutional_orchestrator.response_builder import _comparison_answer

            # Call the single warehouse provider, not the general Universal Ask
            # planner.  The latter also schedules broad industry/event objects and
            # defeated this latency guard on a single-worker Render instance.
            comparison_wrap = _retrieve_comparison_evidence({"entities": tickers[:2], "question": question}) or {}
            comparison_payload = comparison_wrap.get("payload") if isinstance(comparison_wrap, dict) else {}
            comparison_payload = comparison_payload if isinstance(comparison_payload, dict) else {}
            direct = str(
                _comparison_answer({"ComparisonEvidence": {"payload": comparison_payload}}, question=question) or ""
            ).strip()
            # Do not hide richer research behind an empty warehouse response.
            if not direct or "unavailable for every requested company" in direct.lower():
                return None

            why = [
                f"{row.get('symbol')}: verified warehouse financial statements and valuation fields."
                for row in (comparison_payload.get("companies") or [])[:2]
                if isinstance(row, dict) and row.get("symbol")
            ]
            evidence = [
                {
                    "title": f"{row.get('symbol')} verified financial comparison",
                    "source": ", ".join(row.get("sources") or []) or "institutional_warehouse",
                    "as_of": row.get("as_of"),
                    "ticker": row.get("symbol"),
                }
                for row in (comparison_payload.get("companies") or [])[:2]
                if isinstance(row, dict) and row.get("symbol")
            ]
            for stage in ("ikl", "retrieval", "ranking", "reasoning", "response_assembly"):
                stage_timer.mark(stage)
            orch = finalize_orchestration(
                {
                    **ask_orchestration,
                    "short_circuit": "verified_comparison_warehouse",
                    "comparison_tickers": tickers[:2],
                    "comparison_retrieval": {"mode": "universal_ask", "tickers": tickers[:2]},
                },
                timer=stage_timer,
                question=question,
                detected_ticker=tickers[0],
                ere_body={},
                alias_hit=tickers[0],
                evidence_used=evidence,
                why=why,
                executive=direct,
                intent="comparison",
                fallback=False,
            )
            stage_timer.mark("serialization")
            orch["completed"] = True
            orch["timeout"] = False
            orch["latency"] = stage_timer.as_latency_block()
            orch["latency_ms"] = stage_timer.as_dict()
            orch["trace_summary"] = format_trace_summary(orch)
            return SearchView(
                meta=UiMeta(surface="search", sources=["verified_comparison_warehouse"]),
                question=question,
                status="ok",
                degradation={"ask_slim": ask_slim_enabled(), "short_circuit": "verified_comparison_warehouse"},
                ask_orchestration=orch,
                intent="comparison",
                entities={"ticker": tickers[0], "companies": tickers[:2], "themes": [], "sectors": []},
                answer={
                    "summary": direct,
                    "executive_summary": direct,
                    "stance": "Research comparison",
                    "why": why,
                    "policy": "verified_warehouse_comparison_no_recommendation",
                },
                executive_summary=direct,
                house_view={"label": "Research comparison", "stance": "Neutral"},
                confidence=85.0,
                investment_thesis=direct,
                why=why,
                evidence_used=evidence,
                supporting_research=evidence,
                related_companies=tickers[:2],
                follow_up_questions=[
                    f"Compare {tickers[0]} and {tickers[1]} on earnings quality.",
                    f"Compare {tickers[0]} and {tickers[1]} valuation.",
                ],
                answer_policy="verified_warehouse_comparison_no_recommendation",
                entity_resolution=scrub(entity_resolution) if entity_resolution else {},
            )
        except Exception:
            return None

    def search(
        self,
        question: str,
        *,
        ticker: str | None = None,
        ask_trace_id: str | None = None,
    ) -> SearchView:
        """Ask desk entry — always returns a SearchView when possible (never blank 503)."""
        q = (question or "").strip()
        # Per-Ask Yahoo symbol/enrich cache — resolve once, reuse across CID/DVC/YFP.
        _yahoo_scope = None
        _end_yahoo_scope = None
        try:
            from app.market_data.providers.yahoo_request_cache import (
                begin_request_scope,
                end_request_scope,
            )

            _yahoo_scope = begin_request_scope()
            _end_yahoo_scope = end_request_scope
        except Exception:
            pass
        try:
            try:
                return self._search_unguarded(
                    question, ticker=ticker, ask_trace_id=ask_trace_id
                )
            except Exception as exc:  # noqa: BLE001 — desk must degrade, not disappear
                import logging
                import traceback

                logging.getLogger("agi.ui.search").exception("ask_search_failed q=%r", q[:120])
                tid = normalize_request_id((ask_trace_id or "").strip() or None)
                try:
                    _pt = AskPipelineTrace(request_id=tid, question=q)
                    _pt.mark(STAGE_ENGINE_RECEIVED, status="error")
                    _pt.set_error(
                        stage="search",
                        message=type(exc).__name__,
                        root_cause=str(exc)[:400],
                        stack=traceback.format_exc(),
                    )
                    _pt.set_fallback("dependency_failure", detail={"exception": type(exc).__name__})
                    _pt.complete(status="error")
                except Exception:
                    pass
                return SearchView(
                    meta=UiMeta(
                        surface="search",
                        sources=["degraded_fallback"],
                    ),
                    question=q or "Ask AGI",
                    status="degraded",
                    degradation={
                        "desk": "exception",
                        "error": type(exc).__name__,
                        "faa": "background_only",
                        "reasoning": "unavailable",
                        "detail": str(exc)[:200],
                    },
                    ask_orchestration={
                        "version": "ask-orchestration-trace-2",
                        "ask_trace_id": tid,
                        "request_id": tid,
                        "fallback": True,
                        "fallback_used": True,
                        "completed": False,
                        "timeout": False,
                        "last_completed_stage": "http_ingress",
                        "engine_reached": False,
                        "reason": type(exc).__name__,
                        "diagnostics_visibility": "internal",
                        "trace_summary": f"Fallback: Yes | Exception: {type(exc).__name__}",
                    },
                    answer={
                        "summary": (
                            "The research desk returned a partial response. "
                            "Cached institutional context was insufficient for a full briefing — please try again."
                        ),
                        "stance": "Neutral",
                    },
                    executive_summary=(
                        "A full briefing could not be completed on this attempt. "
                        "Your question was preserved — retry in a moment for the complete desk view."
                    ),
                    follow_up_questions=[
                        q[:120] if q else "What is moving Indian markets today?",
                        "What is the outlook for Nifty?",
                    ],
                )
        finally:
            if _yahoo_scope is not None and _end_yahoo_scope is not None:
                try:
                    _end_yahoo_scope(_yahoo_scope)
                except Exception:
                    pass

    def _search_unguarded(
        self,
        question: str,
        *,
        ticker: str | None = None,
        ask_trace_id: str | None = None,
    ) -> SearchView:
        self._require()
        q = (question or "").strip()
        from semantic_research_retrieval.routing import (
            COMPANY_RESEARCH,
            classify_research_route,
        )

        research_route = classify_research_route(q)
        client = None
        detected_ticker = ticker.upper() if ticker else None
        # Comparisons are multi-entity research requests.  Keep the canonical pair
        # separate from the primary ticker used by legacy single-company adapters.
        comparison_tickers: list[str] = []
        rsp_pkg: dict[str, Any] = {}
        irp_pkg = None
        irp_dump: dict[str, Any] = {}
        ask_trace_id = normalize_request_id((ask_trace_id or "").strip() or None)
        stage_timer = StageTimer(ask_trace_id=ask_trace_id)
        pipeline = AskPipelineTrace(request_id=ask_trace_id, question=q)
        pipeline.mark(STAGE_ENGINE_RECEIVED, status="ok")

        knowledge_bundle: dict[str, Any] = {}

        # RQ1 Sprint 1 — classify research type first (metadata only; does not block layers yet)
        research_ontology: dict[str, Any] = {}
        try:
            from research_ontology.production import soft_slice_for_ask_agi

            research_ontology = soft_slice_for_ask_agi(q) or {}
        except Exception:
            research_ontology = {}
        # Phase-1 observability — intent (no behavior change)
        try:
            _ro = (research_ontology.get("research_ontology") or research_ontology) if isinstance(research_ontology, dict) else {}
            _intent = (
                _ro.get("research_type")
                or _ro.get("question_type")
                or _ro.get("intent")
                or (research_ontology.get("research_type") if isinstance(research_ontology, dict) else None)
            )
            _conf = _ro.get("confidence") if isinstance(_ro, dict) else None
            if _intent:
                pipeline.set_intent(str(_intent), confidence=float(_conf) if _conf is not None else None)
            else:
                pipeline.set_intent(
                    "Unknown",
                    confidence=0.0,
                    why_unknown="research_ontology returned no research_type/question_type",
                )
        except Exception:
            pipeline.set_intent("Unknown", confidence=0.0, why_unknown="intent logging failed")

        # RQ1 Sprint 2 — Entity Resolution Engine (canonical identity; metadata soft-wire)
        entity_resolution: dict[str, Any] = {}
        ere_body: dict[str, Any] = {}
        ere_research_blocked = False
        ere_ticker: str | None = None
        alias_hit: str | None = None
        ask_orchestration: dict[str, Any] = {
            "ask_trace_id": ask_trace_id,
            "request_id": ask_trace_id,
            "ticker_source": "user" if detected_ticker else None,
            "ticker_rejects": [],
            "ere_research_blocked": False,
            "executive_source": None,
            "research_route": research_route,
        }
        try:
            if research_route != COMPANY_RESEARCH:
                raise LookupError("entity resolution is not required for this research route")
            from entity_resolution.production import soft_slice_for_ask_agi as ere_soft_slice

            entity_resolution = ere_soft_slice(q) or {}
            # Prefer ERE ticker when clear
            ere_body = entity_resolution.get("entity_resolution") or {}
            if isinstance(ere_body, dict):
                ere_research_blocked = bool(
                    ere_body.get("research_blocked")
                    or (ere_body.get("needs_clarification") and not ere_body.get("ticker"))
                )
                ask_orchestration["ere_research_blocked"] = ere_research_blocked
                if (
                    not ere_body.get("needs_clarification")
                    and ere_body.get("ticker")
                    and not detected_ticker
                ):
                    safe = accept_detected_ticker(ere_body.get("ticker"))
                    if safe:
                        detected_ticker = safe
                        ere_ticker = safe
                        ask_orchestration["ticker_source"] = "ere"
        except Exception:
            entity_resolution = {}
            ere_body = {}

        # Deterministic alias bind (Meta/Apple/…) before soft packs can pollute.
        alias_hit = (
            alias_ticker_from_question(q)
            if research_route == COMPANY_RESEARCH
            else None
        )
        if alias_hit and not detected_ticker:
            detected_ticker = alias_hit
            ask_orchestration["ticker_source"] = "alias"
        elif alias_hit and detected_ticker and detected_ticker != alias_hit and not ticker:
            # Soft-pack / theme pollution must not override an explicit company mention.
            detected_ticker = alias_hit
            ask_orchestration["ticker_source"] = "alias_override"
        stage_timer.set_context(
            entity={
                "name": detected_ticker,
                "detected": detected_ticker,
                "confidence": 0.98 if alias_hit else (0.9 if ere_ticker else 0.0),
                "source": ask_orchestration.get("ticker_source"),
            }
        )
        stage_timer.mark("entity_resolution")
        # Phase-1 observability — entities (never silent on miss)
        try:
            _ent_rows: list[dict[str, Any]] = []
            if detected_ticker:
                _ent_rows.append(
                    {
                        "name": detected_ticker,
                        "ticker": detected_ticker,
                        "confidence": 0.98 if alias_hit else (0.9 if ere_ticker else 0.5),
                        "source": ask_orchestration.get("ticker_source"),
                    }
                )
            pipeline.set_entities(
                _ent_rows,
                confidence=0.98 if alias_hit else (0.9 if ere_ticker else (0.0 if not _ent_rows else 0.5)),
                aliases_matched=[alias_hit] if alias_hit else [],
                none_found=not _ent_rows,
            )
        except Exception:
            pipeline.set_entities([], none_found=True)

        # A two-company comparison with deterministic aliases does not need the
        # general KUL/QUE research fan-out before it can return verified financial
        # facts.  Keep this before those expensive soft layers; the later guard is
        # retained for comparisons resolved by non-alias entity paths.
        early_comparison_tickers = alias_tickers_from_question(q) if is_comparison_question(q) else []
        if len(early_comparison_tickers) >= 2:
            ask_orchestration["comparison_tickers"] = early_comparison_tickers[:2]
            ask_orchestration["comparison_entity_count"] = len(early_comparison_tickers[:2])
            fast_comparison = self._verified_comparison_view(
                question=q,
                tickers=early_comparison_tickers[:2],
                ask_trace_id=ask_trace_id,
                stage_timer=stage_timer,
                ask_orchestration=ask_orchestration,
                entity_resolution=entity_resolution,
            )
            if fast_comparison is not None:
                return fast_comparison

        # QUE v1.1 — first pipeline stage. Built once; attached to every Ask path
        # (including short-circuits) so downstream always knows the decision.
        que_pack = _build_que_answer_construction(q, ticker=detected_ticker)
        ask_orchestration["que_decision_type"] = que_pack.get("decision_type")
        ask_orchestration["que_attached"] = bool(que_pack.get("enabled"))
        if que_pack.get("primary_investment_question"):
            ask_orchestration["primary_investment_question"] = que_pack.get(
                "primary_investment_question"
            )

        # Recommendation / buy-sell bait: refuse transactional advice, but still
        # attach the capital-allocation research brief (QUE) so Ask answers the
        # real decision rather than going silent on the investment question.
        if _is_recommendation_bait(q):
            try:
                pipeline.set_intent("Recommendation Request", confidence=0.99)
                pipeline.mark(STAGE_RETRIEVAL_STARTED, status="skipped")
                pipeline.mark(STAGE_RETRIEVAL_COMPLETED, status="skipped")
                pipeline.set_evidence(retrieved=0, used=1, top_ids=["policy"], sources=["policy"])
                pipeline.set_prompt(
                    prompt_chars=len(q) + 200,
                    estimated_tokens=80,
                    evidence_count=1,
                    system_prompt_version="recommendation_policy",
                    playbook="no_buy_sell",
                )
                pipeline.set_llm(model="policy", used=False, finish_reason="policy_refuse")
                pipeline.complete(status="success")
            except Exception:
                pass
            return self._recommendation_policy_view(
                question=q,
                ticker=detected_ticker,
                ask_trace_id=ask_trace_id,
                stage_timer=stage_timer,
                ask_orchestration={
                    **ask_orchestration,
                    "request_id": ask_trace_id,
                    "pipeline_debug": pipeline.to_debug_payload(),
                },
                entity_resolution=entity_resolution,
                ere_body=ere_body if isinstance(ere_body, dict) else {},
                alias_hit=alias_hit,
                que_pack=que_pack,
            )

        # Unsupported Coverage Policy (Phase 2.6 Module 12) — a REAL, well-
        # known company outside this platform's verified retrieval universe
        # (e.g. Visa, Costco, Ferrari) must get an honest "no coverage"
        # refusal, never irrelevant generic evidence — and this must run
        # BEFORE the Financial Router below, since a question like "Why does
        # Visa generate high free cash flow?" also matches the generic
        # 'free cash flow' concept and would otherwise get a company-blind
        # concept answer instead of the honest coverage refusal. Distinct
        # from the unknown-entity hard stop further down, which handles
        # genuinely fictitious/unrecognized names — see
        # app/ui/coverage_policy.py.
        try:
            if research_route != COMPANY_RESEARCH:
                raise LookupError("coverage policy is company-only")
            unsupported_company = coverage_policy_detect(q)
        except Exception:
            unsupported_company = None

        # Company Metadata Router — "Axis Bank primary sector" is a stored
        # Capital IQ field, not a research question. It must answer from the
        # Company Identity Service without touching Entity Intelligence, KUL,
        # fusion or the composer. Only unambiguous, registered companies route
        # here; anything else falls through to the normal pipeline.
        try:
            if research_route != COMPANY_RESEARCH:
                raise LookupError("company metadata routing is company-only")
            from company_identity.metadata_router import route as metadata_route

            metadata_hit = metadata_route(q)
        except Exception:
            metadata_hit = None
        if metadata_hit:
            try:
                pipeline.set_intent("Company Metadata", confidence=0.99)
                pipeline.mark(STAGE_RETRIEVAL_STARTED, status="skipped")
                pipeline.mark(STAGE_RETRIEVAL_COMPLETED, status="skipped")
                pipeline.set_evidence(
                    retrieved=0,
                    used=1,
                    top_ids=["company_identity"],
                    sources=["company_identity"],
                )
                pipeline.set_llm(model="registry", used=False, finish_reason="company_metadata")
                pipeline.complete(status="success")
            except Exception:
                pass
            return self._company_metadata_view(
                question=q,
                ask_trace_id=ask_trace_id,
                stage_timer=stage_timer,
                ask_orchestration={
                    **ask_orchestration,
                    "request_id": ask_trace_id,
                    "pipeline_debug": pipeline.to_debug_payload(),
                },
                entity_resolution=entity_resolution,
                ere_body=ere_body if isinstance(ere_body, dict) else {},
                alias_hit=alias_hit,
                metadata=metadata_hit,
            )

        # P0 Entity Intelligence — verified entity contract BEFORE KUL.
        # Never execute intelligence engines on a substituted / unverified company.
        ei_contract: dict[str, Any] = {}
        try:
            from entity_intelligence.production import (
                analyse as ei_analyse,
                should_short_circuit as ei_should_short_circuit,
                validate_bound_ticker as ei_validate_bound_ticker,
            )

            ei_contract = ei_analyse(q) or {}
            ask_orchestration["entity_intelligence"] = {
                "state": ei_contract.get("state"),
                "confidence": ei_contract.get("confidence"),
                "ticker": ei_contract.get("ticker"),
                "canonical_name": ei_contract.get("canonical_name"),
                "allow_planner": ei_contract.get("allow_planner"),
                "coverage": ei_contract.get("coverage"),
            }
            # Prefer EI verified ticker over CapIQ/ERE when present.
            ei_tk = ei_contract.get("ticker")
            if ei_tk and ei_contract.get("allow_planner"):
                safe = accept_detected_ticker(ei_tk)
                if safe:
                    detected_ticker = safe
                    ask_orchestration["ticker_source"] = "entity_intelligence"
            # Drop any prior bind that violates forbid / private rules.
            if detected_ticker and not ei_validate_bound_ticker(ei_contract, detected_ticker):
                ask_orchestration.setdefault("ticker_rejects", []).append(
                    {"ticker": detected_ticker, "reason": "entity_intelligence_forbidden_bind"}
                )
                detected_ticker = None
                ask_orchestration["ticker_source"] = "entity_intelligence_cleared"
            if ei_should_short_circuit(ei_contract):
                try:
                    pipeline.set_intent("Entity Intelligence", confidence=0.99)
                    pipeline.mark(STAGE_RETRIEVAL_STARTED, status="skipped")
                    pipeline.mark(STAGE_RETRIEVAL_COMPLETED, status="skipped")
                    pipeline.set_evidence(
                        retrieved=0, used=1, top_ids=["entity_intelligence"], sources=["entity_intelligence"]
                    )
                    pipeline.set_llm(model="policy", used=False, finish_reason="entity_intelligence_gate")
                    pipeline.complete(status="success")
                except Exception:
                    pass
                return self._entity_intelligence_view(
                    question=q,
                    ask_trace_id=ask_trace_id,
                    stage_timer=stage_timer,
                    ask_orchestration={
                        **ask_orchestration,
                        "request_id": ask_trace_id,
                        "pipeline_debug": pipeline.to_debug_payload(),
                    },
                    entity_resolution=entity_resolution,
                    ere_body=ere_body if isinstance(ere_body, dict) else {},
                    alias_hit=alias_hit,
                    contract=ei_contract,
                )
        except Exception:
            ei_contract = {}

        # Knowledge Unification Layer (KUL) — Phase X. Single deterministic
        # planner over CapIQ/IKT, IKL, Company Memory, KF, CGL, financial
        # concepts/foundations/FSI, Academy, BI Foundation, and legacy KIP.
        # For unsupported globals on *business-shaped* questions, prefer BI
        # via KUL (industry templates / honest economics) over a hard refuse
        # that blocks all business reasoning. CapIQ false-binds remain guarded
        # inside KUL. Non-business unsupported questions still refuse below.
        # Entity Intelligence must have allowed the planner (or been unavailable).
        try:
            kul_hit = kul_answer_for_ask(q, ticker=detected_ticker)
        except Exception:
            kul_hit = None
        if research_route != COMPANY_RESEARCH and kul_hit:
            ask_orchestration["kul_deferred_for_semantic_research"] = True
            kul_hit = None
        # Post-KUL: if KUL somehow bound a forbidden ticker, discard and refuse.
        try:
            from entity_intelligence.production import validate_bound_ticker as ei_validate_bound_ticker

            kul_tk = None
            if isinstance(kul_hit, dict):
                kul_tk = ((kul_hit.get("company_intelligence") or {}).get("identity") or {}).get("ticker")
            if ei_contract and kul_tk and not ei_validate_bound_ticker(ei_contract, kul_tk):
                kul_hit = None
                ask_orchestration.setdefault("ticker_rejects", []).append(
                    {"ticker": kul_tk, "reason": "entity_intelligence_post_kul_forbid"}
                )
        except Exception:
            pass

        if unsupported_company and not (
            kul_hit
            and (kul_hit.get("summary") or kul_hit.get("why"))
            and "business_intelligence" in list(kul_hit.get("providers_used") or [])
        ):
            for stage in ("ikl", "retrieval", "ranking", "reasoning", "response_assembly"):
                stage_timer.mark(stage)
            executive = coverage_policy_executive(unsupported_company)
            why = coverage_policy_why(unsupported_company)
            cov_orch = {
                **ask_orchestration,
                "executive_source": "unsupported_coverage_policy",
                "short_circuit": "unsupported_coverage_policy",
                "rq_stack": "skipped_unsupported_coverage_policy",
                "unsupported_company": unsupported_company,
            }
            orch = finalize_orchestration(
                cov_orch,
                timer=stage_timer,
                question=q,
                detected_ticker=None,
                ere_body=ere_body if isinstance(ere_body, dict) else {},
                alias_hit=alias_hit,
                evidence_used=[],
                why=why,
                executive=executive,
                intent="unsupported_coverage_policy",
                fallback=False,
            )
            stage_timer.mark("serialization")
            try:
                orch["latency"] = stage_timer.as_latency_block()
                orch["latency_ms"] = stage_timer.as_dict()
                orch["trace_summary"] = format_trace_summary(orch)
                orch["completed"] = True
                orch["timeout"] = False
            except Exception:
                pass
            return SearchView(
                meta=UiMeta(surface="search", sources=["unsupported_coverage_policy"]),
                question=q,
                status="ok",
                degradation={
                    "ask_slim": ask_slim_enabled(),
                    "short_circuit": "unsupported_coverage_policy",
                    "rq_stack": "skipped",
                    "reasoning": "unsupported_company",
                },
                ask_orchestration=orch,
                intent="unsupported_coverage_policy",
                entities={"ticker": None, "companies": [], "themes": [], "sectors": []},
                answer={
                    "summary": executive,
                    "executive_summary": executive,
                    "stance": "Neutral",
                    "why": why,
                    "house_view_label": "Insufficient evidence",
                    "policy": "unsupported_coverage_refuse",
                },
                executive_summary=executive,
                house_view={"label": "Insufficient evidence", "stance": "Neutral"},
                confidence=15.0,
                investment_thesis=executive,
                bull_case=[],
                bear_case=[],
                key_risks=[f"{unsupported_company} is outside this platform's verified coverage universe."],
                why=why,
                evidence_used=[],
                follow_up_questions=[
                    "Ask about the underlying financial concept for a general explanation.",
                    "Ask about a covered company (e.g. Reliance, TCS, Infosys, HDFC Bank) for full research.",
                ],
                answer_policy="unsupported_coverage_refuse",
                entity_resolution=scrub(entity_resolution) if entity_resolution else {},
            )

        # Investment decisions (Research Priority, Valuation, etc.) must reach
        # answer_construction / QUE-shaped research — not a thin company dump.
        kul_providers_preview = list((kul_hit or {}).get("providers_used") or []) if kul_hit else []
        kul_is_finance_concept = bool(
            kul_hit
            and any(
                p in kul_providers_preview
                for p in (
                    "financial_concepts",
                    "financial_foundations",
                    "financial_statement_intelligence",
                )
            )
            and not ((kul_hit.get("company_intelligence") or {}).get("identity") or {}).get("ticker")
        )
        if (
            kul_hit
            and (kul_hit.get("summary") or kul_hit.get("why"))
            and _que_requires_full_desk(que_pack)
            and not kul_is_finance_concept
        ):
            ask_orchestration["kul_deferred_for_que"] = True
            ask_orchestration["kul_deferred_providers"] = kul_providers_preview[:8]
            ask_orchestration["kul_deferred_summary"] = str(kul_hit.get("summary") or "")[:280]
            kul_hit = None  # fall through to full desk

        if kul_hit and (kul_hit.get("summary") or kul_hit.get("why")):
            for stage in ("ikl", "retrieval", "ranking", "reasoning", "response_assembly"):
                stage_timer.mark(stage)
            executive = kul_hit["summary"]
            why = list(kul_hit.get("why") or [])
            providers_used = list(kul_hit.get("providers_used") or [])
            coverage = kul_hit.get("coverage") or {}
            kul_key = kul_hit.get("key") or detected_ticker
            kul_orch = {
                **ask_orchestration,
                "executive_source": "knowledge_unification",
                "short_circuit": "knowledge_unification",
                "rq_stack": "skipped_knowledge_unification",
                "ikt_company_key": kul_key,
                "kul_providers_used": providers_used,
                "kul_coverage": coverage,
                "kul_diagnostics": kul_hit.get("diagnostics") or {},
            }
            intent = (
                "company_profile"
                if (kul_hit.get("company_intelligence") or {}).get("identity", {}).get("ticker")
                or "capiq_ikt" in providers_used
                else "financial_engine"
                if any(
                    p in providers_used
                    for p in (
                        "financial_concepts",
                        "financial_foundations",
                        "financial_statement_intelligence",
                    )
                )
                else "knowledge_unification"
            )
            orch = finalize_orchestration(
                kul_orch,
                timer=stage_timer,
                question=q,
                detected_ticker=kul_key,
                ere_body=ere_body if isinstance(ere_body, dict) else {},
                alias_hit=alias_hit,
                evidence_used=kul_hit.get("evidence") or [],
                why=why,
                executive=executive,
                intent=intent,
                fallback=False,
            )
            stage_timer.mark("serialization")
            try:
                orch["latency"] = stage_timer.as_latency_block()
                orch["latency_ms"] = stage_timer.as_dict()
                orch["trace_summary"] = format_trace_summary(orch)
                orch["completed"] = True
                orch["timeout"] = False
                # Preserve pre-KUL acceptance signals: primary deterministic
                # finance engine + concept key when KUL answered via those
                # providers (concept/accounting acceptance + AFI routing).
                det_finance = [
                    p
                    for p in (
                        "financial_concepts",
                        "financial_foundations",
                        "financial_statement_intelligence",
                    )
                    if p in providers_used
                ]
                concept_intel = kul_hit.get("concept_intelligence") or {}
                primary_finance = concept_intel.get("provider") if concept_intel.get("provider") in det_finance else None
                if not primary_finance and det_finance:
                    primary_finance = det_finance[0]
                if primary_finance and not (
                    (kul_hit.get("company_intelligence") or {}).get("identity") or {}
                ).get("ticker"):
                    orch["financial_engine"] = primary_finance
                    orch["financial_router_triggered"] = True
                    if concept_intel.get("key"):
                        orch["financial_engine_key"] = concept_intel.get("key")
                    orch["kul_stack"] = providers_used
                else:
                    orch["financial_engine"] = (
                        "knowledge_unification+" + ",".join(providers_used[:4])
                        if providers_used
                        else "knowledge_unification"
                    )
                    if det_finance:
                        orch["financial_router_triggered"] = True
            except Exception:
                pass
            conf = float(coverage.get("confidence") or 80.0)
            sources = ["knowledge_unification", "question_understanding_engine", *providers_used]
            followups = list(que_pack.get("top_research_questions") or [])[:3]
            return SearchView(
                meta=UiMeta(surface="search", sources=sources),
                question=q,
                status="ok",
                degradation={
                    "ask_slim": ask_slim_enabled(),
                    "short_circuit": "knowledge_unification",
                    "rq_stack": "skipped",
                    "reasoning": "kul_fused_evidence",
                    "que_attached": bool(que_pack.get("enabled")),
                },
                ask_orchestration=orch,
                intent=intent,
                entities={
                    "ticker": kul_key,
                    "companies": [kul_hit.get("company_name") or kul_key] if kul_key else [],
                    "themes": [],
                    "sectors": [],
                },
                answer={
                    "summary": executive,
                    "executive_summary": executive,
                    "stance": "Neutral",
                    "why": why,
                    "house_view_label": "Unified Knowledge",
                    "policy": "knowledge_unification",
                    "coverage": coverage,
                    "company_intelligence": kul_hit.get("company_intelligence") or {},
                    "concept_intelligence": kul_hit.get("concept_intelligence") or {},
                    "decision_type": que_pack.get("decision_type"),
                    "primary_investment_question": que_pack.get("primary_investment_question"),
                    "research_brief": que_pack.get("research_brief") or {},
                },
                executive_summary=executive,
                house_view={"label": "Unified Knowledge", "stance": "Neutral"},
                confidence=conf,
                investment_thesis=executive,
                bull_case=[],
                bear_case=[],
                key_risks=list(coverage.get("missing_information") or []),
                why=why,
                evidence_used=kul_hit.get("evidence") or [],
                follow_up_questions=followups,
                answer_policy="knowledge_unification",
                answer_construction=scrub(que_pack) if que_pack else {},
                entity_resolution=scrub(entity_resolution) if entity_resolution else {},
            )

        # Fallback: isolated IKT company router (pre-KUL path) if unification
        # returned nothing but CapIQ still has a direct profile hit.
        try:
            if research_route != COMPANY_RESEARCH:
                raise LookupError("company profile routing is company-only")
            ikt_hit = company_router_route(q)
        except Exception:
            ikt_hit = None
        if ikt_hit and _que_requires_full_desk(que_pack):
            ask_orchestration["ikt_deferred_for_que"] = True
            ikt_hit = None
        if ikt_hit:
            for stage in ("ikl", "retrieval", "ranking", "reasoning", "response_assembly"):
                stage_timer.mark(stage)
            executive = ikt_hit["summary"]
            why = ikt_hit["why"]
            # A question about an annual report, transcript or guidance must
            # not be answered with a company profile as if it were research.
            if _is_research_shaped_question(q):
                company_label = ikt_hit.get("company_name") or ikt_hit.get("key") or "this company"
                executive = (
                    f"No annual report, transcript or management commentary for "
                    f"{company_label} is in research memory yet, so there is nothing to quote. "
                    f"What is on file is the company profile: {executive}"
                )
                why = [
                    "Research memory holds no filed document for this company yet.",
                    *list(why or []),
                ]
            ikt_orch = {
                **ask_orchestration,
                "executive_source": "ikt_company_router",
                "short_circuit": "ikt_company_router",
                "rq_stack": "skipped_ikt_company_router",
                "ikt_company_key": ikt_hit.get("key"),
            }
            orch = finalize_orchestration(
                ikt_orch,
                timer=stage_timer,
                question=q,
                detected_ticker=ikt_hit.get("key"),
                ere_body=ere_body if isinstance(ere_body, dict) else {},
                alias_hit=alias_hit,
                evidence_used=ikt_hit.get("evidence") or [],
                why=why,
                executive=executive,
                intent="company_profile",
                fallback=False,
            )
            stage_timer.mark("serialization")
            try:
                orch["latency"] = stage_timer.as_latency_block()
                orch["latency_ms"] = stage_timer.as_dict()
                orch["trace_summary"] = format_trace_summary(orch)
                orch["completed"] = True
                orch["timeout"] = False
            except Exception:
                pass
            return SearchView(
                meta=UiMeta(surface="search", sources=["institutional_knowledge_tables"]),
                question=q,
                status="ok",
                degradation={
                    "ask_slim": ask_slim_enabled(),
                    "short_circuit": "ikt_company_router",
                    "rq_stack": "skipped",
                    "reasoning": "ikt_company_profile",
                },
                ask_orchestration=orch,
                intent="company_profile",
                entities={
                    "ticker": ikt_hit.get("key"),
                    "companies": [ikt_hit.get("company_name") or ikt_hit.get("key")],
                    "themes": [],
                    "sectors": [],
                },
                answer={
                    "summary": executive,
                    "executive_summary": executive,
                    "stance": "Neutral",
                    "why": why,
                    "house_view_label": "Company Profile",
                    "policy": "ikt_company_profile",
                },
                executive_summary=executive,
                house_view={"label": "Company Profile", "stance": "Neutral"},
                confidence=80.0,
                investment_thesis=executive,
                bull_case=[],
                bear_case=[],
                key_risks=[],
                why=why,
                evidence_used=ikt_hit.get("evidence") or [],
                follow_up_questions=list(que_pack.get("top_research_questions") or [])[:3],
                answer_policy="ikt_company_profile",
                answer_construction=scrub(que_pack) if que_pack else {},
                entity_resolution=scrub(entity_resolution) if entity_resolution else {},
            )

        # Financial Router — accounting / financial-statement-analysis concept
        # questions ("Explain retained earnings", "Why does every transaction
        # require a debit and a credit?", "Founder invests ₹1 crore. Build the
        # journal entry...") answer directly from the deterministic Phase 1/2
        # engines (financial_foundations / financial_statement_intelligence)
        # and must never fall through to entity resolution or generic
        # retrieval. Runs before the unknown-entity gate below because many
        # of these questions are shaped like "Explain <term>" and would
        # otherwise be misread as requiring a company.
        try:
            if research_route != COMPANY_RESEARCH:
                raise LookupError("financial concept router deferred to semantic research")
            financial_hit = financial_router_route(q)
        except Exception:
            financial_hit = None
        if financial_hit:
            try:
                pipeline.set_intent("Financial Engine", confidence=0.95)
                pipeline.mark(STAGE_RETRIEVAL_STARTED, status="skipped")
                pipeline.mark(STAGE_RETRIEVAL_COMPLETED, status="skipped")
                pipeline.complete(status="success")
            except Exception:
                pass
            return self._financial_engine_view(
                question=q,
                ask_trace_id=ask_trace_id,
                stage_timer=stage_timer,
                ask_orchestration={
                    **ask_orchestration,
                    "request_id": ask_trace_id,
                    "pipeline_debug": pipeline.to_debug_payload(),
                },
                entity_resolution=entity_resolution,
                ere_body=ere_body if isinstance(ere_body, dict) else {},
                alias_hit=alias_hit,
                financial_hit=financial_hit,
            )

        # Executive Composer Rule 3 — unknown / blocked company: STOP (no retrieval, no LT swap).
        _rejected = []
        if isinstance(ere_body, dict):
            for r in ere_body.get("rejected_candidates") or ere_body.get("rejected") or []:
                if isinstance(r, dict):
                    _rejected.append(str(r.get("ticker") or r.get("raw") or r.get("name") or ""))
                elif r:
                    _rejected.append(str(r))
        _rejected = [x for x in _rejected if x]
        if (
            research_route == COMPANY_RESEARCH
            and
            requires_resolved_company(q)
            and not detected_ticker
            and (ere_research_blocked or not alias_hit)
        ):
            return self._unknown_entity_view(
                question=q,
                ask_trace_id=ask_trace_id,
                stage_timer=stage_timer,
                ask_orchestration=ask_orchestration,
                entity_resolution=entity_resolution,
                ere_body=ere_body if isinstance(ere_body, dict) else {},
                alias_hit=alias_hit,
                rejected=_rejected,
            )

        # Executive Composer Rule 4 — comparison requires ≥2 entities.
        if is_comparison_question(q):
            _cmp_n = comparison_entity_count(
                q, ere_body=ere_body if isinstance(ere_body, dict) else {}
            )
            _alias_all = alias_tickers_from_question(q)
            if _cmp_n < 2 and len(_alias_all) < 2:
                return self._comparison_clarification_view(
                    question=q,
                    ask_trace_id=ask_trace_id,
                    stage_timer=stage_timer,
                    ask_orchestration=ask_orchestration,
                    entity_resolution=entity_resolution,
                    ere_body=ere_body if isinstance(ere_body, dict) else {},
                    alias_hit=alias_hit,
                    detected_ticker=detected_ticker,
                )
            # Ensure primary ticker is set when aliases resolved both sides.
            if not detected_ticker and _alias_all:
                detected_ticker = _alias_all[0]
                ask_orchestration["ticker_source"] = "alias_compare"
            comparison_tickers = list(dict.fromkeys(str(x).upper() for x in _alias_all if x))[:2]
            ask_orchestration["comparison_tickers"] = comparison_tickers
            ask_orchestration["comparison_entity_count"] = max(_cmp_n, len(comparison_tickers))
            fast_comparison = self._verified_comparison_view(
                question=q,
                tickers=comparison_tickers,
                ask_trace_id=ask_trace_id,
                stage_timer=stage_timer,
                ask_orchestration=ask_orchestration,
                entity_resolution=entity_resolution,
            )
            if fast_comparison is not None:
                return fast_comparison

        slim = ask_slim_enabled()


        # Market Indices — which stock ↔ which Nifty index (factual membership)
        market_indices: dict[str, Any] = {}
        try:
            from market_indices.production import soft_slice_for_ask_agi as mi_soft_slice

            market_indices = (
                mi_soft_slice(
                    q,
                    {
                        "ticker": detected_ticker,
                        "entity_resolution": (entity_resolution.get("entity_resolution") or {}),
                    },
                )
                or {}
            )
        except Exception:
            market_indices = {}

        # RQ1/RQ2 soft-cascade — skipped when ASK_SLIM (default) to keep Ask responsive.
        research_objective: dict[str, Any] = {}
        context_intelligence: dict[str, Any] = {}
        analyst_router: dict[str, Any] = {}
        layer_router: dict[str, Any] = {}
        execution_policy: dict[str, Any] = {}
        acquisition_planner: dict[str, Any] = {}
        research_blueprint: dict[str, Any] = {}
        validation_engine: dict[str, Any] = {}
        research_execution: dict[str, Any] = {}
        hypothesis_engine: dict[str, Any] = {}
        research_questions: dict[str, Any] = {}
        hypothesis_testing: dict[str, Any] = {}
        belief_engine: dict[str, Any] = {}
        thesis_engine: dict[str, Any] = {}
        debate_engine: dict[str, Any] = {}
        decision_readiness: dict[str, Any] = {}
        reasoning_audit: dict[str, Any] = {}
        if not slim:
            # RQ1 Sprint 3 — Research Objective Engine (institutional research plan; metadata soft-wire)
            research_objective: dict[str, Any] = {}
            try:
                from research_objective.production import soft_slice_for_ask_agi as roe_soft_slice

                roe_payload = {
                    "entity_resolution": (entity_resolution.get("entity_resolution") or {}),
                    "intent": (research_ontology.get("research_ontology") or {}),
                }
                research_objective = roe_soft_slice(q, roe_payload) or {}
            except Exception:
                research_objective = {}

            # RQ1 Sprint 4 — Context Intelligence Engine (surrounding context + Research Context Card)
            context_intelligence: dict[str, Any] = {}
            try:
                from context_intelligence.production import soft_slice_for_ask_agi as cie_soft_slice

                cie_payload = {
                    "entity_resolution": (entity_resolution.get("entity_resolution") or {}),
                    "research_objective": (research_objective.get("research_objective") or {}),
                    "skip_iar": True,
                }
                context_intelligence = cie_soft_slice(q, cie_payload) or {}
            except Exception:
                context_intelligence = {}

            # RQ1 Sprint 5 — Institutional Analyst Router (who participates; metadata soft-wire)
            analyst_router: dict[str, Any] = {}
            try:
                from analyst_router.production import soft_slice_for_ask_agi as iar_soft_slice

                iar_payload = {
                    "research_objective": (research_objective.get("research_objective") or {}),
                }
                analyst_router = iar_soft_slice(q, iar_payload) or {}
            except Exception:
                analyst_router = {}

            # RQ1 Sprint 6 — Intelligence Layer Router (execution plan; metadata soft-wire)
            layer_router: dict[str, Any] = {}
            try:
                from layer_router.production import soft_slice_for_ask_agi as ilr_soft_slice

                ilr_payload = {
                    "research_objective": (research_objective.get("research_objective") or {}),
                    "analyst_router": (analyst_router.get("analyst_router") or {}),
                    "skip_iar": True,
                }
                layer_router = ilr_soft_slice(q, ilr_payload) or {}
            except Exception:
                layer_router = {}

            # Framework Execution Policy — select required frameworks BEFORE packs run.
            # Soft-wire only: knowledge is useless unless the planner forces execution.
            execution_policy: dict[str, Any] = {}
            try:
                from institutional_reasoning.execution_policy import soft_slice_for_ask_agi as fep_select

                execution_policy = fep_select(q, ontology=research_ontology) or {}
            except Exception:
                execution_policy = {}

            # RQ1 Sprint 7 — Institutional Acquisition & API Planning Engine (evidence plan; metadata soft-wire)
            acquisition_planner: dict[str, Any] = {}
            try:
                from acquisition_planner.production import soft_slice_for_ask_agi as iape_soft_slice

                iape_payload = {
                    "primary_objective": (research_objective.get("research_objective") or {}).get("primary_objective")
                    or (research_objective.get("primary_objective")),
                    "intent_family": (research_ontology.get("intent_family") or research_ontology.get("family")),
                    "required_layers": (layer_router.get("required_layers") or []),
                    "required_frameworks": [
                        f.get("framework_id")
                        for f in (execution_policy.get("required_frameworks") or [])
                        if isinstance(f, dict)
                    ],
                }
                acquisition_planner = iape_soft_slice(q, iape_payload) or {}
            except Exception:
                acquisition_planner = {}

            # RQ1 Sprint 8 — Dynamic Research Blueprint Engine (publication plan; metadata soft-wire)
            research_blueprint: dict[str, Any] = {}
            try:
                from research_blueprint.production import soft_slice_for_ask_agi as drbe_soft_slice

                drbe_payload = {
                    "primary_objective": (research_objective.get("research_objective") or {}).get("primary_objective")
                    or research_objective.get("primary_objective"),
                    "intent_family": (research_ontology.get("intent_family") or research_ontology.get("family")),
                    "required_analysts": (analyst_router.get("required_analysts") or []),
                    "analyst_router": analyst_router,
                }
                research_blueprint = drbe_soft_slice(q, drbe_payload) or {}
            except Exception:
                research_blueprint = {}

            # RQ1 Sprint 9 — Institutional Validation & Clarification Engine (readiness gate; metadata soft-wire)
            validation_engine: dict[str, Any] = {}
            try:
                from validation_engine.production import soft_slice_for_ask_agi as ivce_soft_slice

                ivce_payload = {
                    "research_ontology": research_ontology,
                    "entity_resolution": entity_resolution,
                    "research_objective": research_objective,
                    "context_intelligence": context_intelligence,
                    "analyst_router": analyst_router,
                    "layer_router": layer_router,
                    "primary_objective": (research_objective.get("research_objective") or {}).get("primary_objective")
                    or research_objective.get("primary_objective"),
                    "intent_family": (research_ontology.get("intent_family") or research_ontology.get("family")),
                }
                validation_engine = ivce_soft_slice(q, ivce_payload) or {}
            except Exception:
                validation_engine = {}

            # RQ1 Sprint 10 — Institutional Research Execution Package (final immutable planning brief)
            research_execution: dict[str, Any] = {}
            try:
                from research_execution.production import soft_slice_for_ask_agi as irep_soft_slice

                irep_payload = {
                    "research_ontology": research_ontology,
                    "entity_resolution": entity_resolution,
                    "research_objective": research_objective,
                    "context_intelligence": context_intelligence,
                    "analyst_router": analyst_router,
                    "layer_router": layer_router,
                }
                research_execution = irep_soft_slice(q, irep_payload) or {}
            except Exception:
                research_execution = {}

            # RQ2 Sprint 1 — Institutional Hypothesis Generation Engine (AFTER IREP / Layer Router; BEFORE analysts)
            hypothesis_engine: dict[str, Any] = {}
            try:
                from hypothesis_engine.production import soft_slice_for_ask_agi as ihg_soft_slice

                ihg_payload = {
                    "entity_resolution": entity_resolution,
                    "research_objective": research_objective,
                    "analyst_router": analyst_router,
                    "layer_router": layer_router,
                    "context_intelligence": context_intelligence,
                    "acquisition_planner": acquisition_planner,
                    "research_blueprint": research_blueprint,
                    "validation_engine": validation_engine,
                    "research_execution": research_execution,
                }
                hypothesis_engine = _unwrap_soft_slice(
                    "hypothesis_engine", ihg_soft_slice(q, ihg_payload) or {}
                )
            except Exception:
                hypothesis_engine = {}

            # RQ2 Sprint 2 — Institutional Research Question Engine (AFTER IHG; BEFORE evidence collection)
            research_questions: dict[str, Any] = {}
            try:
                from research_questions.production import soft_slice_for_ask_agi as irq_soft_slice

                irq_payload = {
                    "entity_resolution": entity_resolution,
                    "research_objective": research_objective,
                    "analyst_router": analyst_router,
                    "layer_router": layer_router,
                    "context_intelligence": context_intelligence,
                    "hypothesis_engine": hypothesis_engine,
                }
                research_questions = _unwrap_soft_slice(
                    "research_questions", irq_soft_slice(q, irq_payload) or {}
                )
            except Exception:
                research_questions = {}

            # RQ2 Sprint 4 — Institutional Hypothesis Testing Engine (AFTER evidence planning; BEFORE analysts)
            hypothesis_testing: dict[str, Any] = {}
            try:
                from hypothesis_testing.production import soft_slice_for_ask_agi as ihte_soft_slice

                ihte_payload = {
                    "entity_resolution": entity_resolution,
                    "research_objective": research_objective,
                    "analyst_router": analyst_router,
                    "layer_router": layer_router,
                    "context_intelligence": context_intelligence,
                    "hypothesis_engine": hypothesis_engine,
                    "research_questions": research_questions,
                    "acquisition_planner": acquisition_planner,
                    "research_blueprint": research_blueprint,
                    "validation_engine": validation_engine,
                    "research_execution": research_execution,
                }
                hypothesis_testing = _unwrap_soft_slice(
                    "hypothesis_testing", ihte_soft_slice(q, ihte_payload) or {}
                )
            except Exception:
                hypothesis_testing = {}

            # RQ2 Sprint 6 — Bayesian Belief & Confidence Engine (AFTER falsification; BEFORE analyst opinions)
            belief_engine: dict[str, Any] = {}
            try:
                from belief_engine.production import soft_slice_for_ask_agi as bbce_soft_slice

                bbce_payload = {
                    "entity_resolution": entity_resolution,
                    "research_objective": research_objective,
                    "analyst_router": analyst_router,
                    "layer_router": layer_router,
                    "context_intelligence": context_intelligence,
                    "hypothesis_engine": hypothesis_engine,
                    "research_questions": research_questions,
                    "hypothesis_testing": hypothesis_testing,
                }
                # Soft-import falsification engine when available (RQ2.5)
                try:
                    from falsification_engine.production import soft_slice_for_ask_agi as ife_soft  # type: ignore

                    ife = ife_soft(q, bbce_payload) or {}
                    if isinstance(ife, dict):
                        bbce_payload.update(ife)
                except Exception:
                    pass
                belief_engine = _unwrap_soft_slice(
                    "belief_engine", bbce_soft_slice(q, bbce_payload) or {}
                )
            except Exception:
                belief_engine = {}

            # RQ2 Sprint 7 — Institutional Thesis Construction Engine (AFTER BBCE; BEFORE Investment Committee)
            thesis_engine: dict[str, Any] = {}
            try:
                from thesis_engine.production import soft_slice_for_ask_agi as itce_soft_slice

                itce_payload = {
                    "entity_resolution": entity_resolution,
                    "research_objective": research_objective,
                    "analyst_router": analyst_router,
                    "context_intelligence": context_intelligence,
                    "hypothesis_engine": hypothesis_engine,
                    "research_questions": research_questions,
                    "hypothesis_testing": hypothesis_testing,
                    "belief_engine": belief_engine,
                }
                thesis_engine = _unwrap_soft_slice(
                    "thesis_engine", itce_soft_slice(q, itce_payload) or {}
                )
            except Exception:
                thesis_engine = {}

            # RQ2 Sprint 8 — Institutional Debate Engine (AFTER ITCE; BEFORE Investment Committee)
            debate_engine: dict[str, Any] = {}
            try:
                from debate_engine.production import soft_slice_for_ask_agi as ideb_soft_slice

                ideb_payload = {
                    "entity_resolution": entity_resolution,
                    "research_objective": research_objective,
                    "analyst_router": analyst_router,
                    "hypothesis_engine": hypothesis_engine,
                    "research_questions": research_questions,
                    "hypothesis_testing": hypothesis_testing,
                    "belief_engine": belief_engine,
                    "thesis_engine": thesis_engine,
                }
                debate_engine = _unwrap_soft_slice(
                    "debate_engine", ideb_soft_slice(q, ideb_payload) or {}
                )
            except Exception:
                debate_engine = {}

            # RQ2 Sprint 9 — Institutional Decision Readiness Engine (AFTER IDEB; BEFORE Committee)
            decision_readiness: dict[str, Any] = {}
            try:
                from decision_readiness.production import soft_slice_for_ask_agi as idre_soft_slice

                idre_payload = {
                    "entity_resolution": entity_resolution,
                    "research_objective": research_objective,
                    "analyst_router": analyst_router,
                    "hypothesis_testing": hypothesis_testing,
                    "belief_engine": belief_engine,
                    "thesis_engine": thesis_engine,
                    "debate_engine": debate_engine,
                }
                decision_readiness = _unwrap_soft_slice(
                    "decision_readiness", idre_soft_slice(q, idre_payload) or {}
                )
            except Exception:
                decision_readiness = {}

            # RQ2 Sprint 10 — Institutional Reasoning Audit Engine (final certification BEFORE Committee)
            reasoning_audit: dict[str, Any] = {}
            try:
                from reasoning_audit.production import soft_slice_for_ask_agi as irae_soft_slice

                irae_payload = {
                    "hypothesis_engine": hypothesis_engine,
                    "research_questions": research_questions,
                    "hypothesis_testing": hypothesis_testing,
                    "belief_engine": belief_engine,
                    "thesis_engine": thesis_engine,
                    "debate_engine": debate_engine,
                    "decision_readiness": decision_readiness,
                }
                # Preserve the explicit falsification handoff when RQ2.5 is available.
                try:
                    from falsification_engine.production import soft_slice_for_ask_agi as ife_soft  # type: ignore

                    ife = ife_soft(q, irae_payload) or {}
                    if isinstance(ife, dict):
                        irae_payload.update(ife)
                except Exception:
                    pass
                reasoning_audit = _unwrap_soft_slice(
                    "reasoning_audit", irae_soft_slice(q, irae_payload) or {}
                )
            except Exception:
                reasoning_audit = {}

        else:
            ask_orchestration["rq_stack"] = "skipped_slim"

        # CAE gateway (preferred) — else MEE→FLE→IIE→EVE→AOI→KCV/KF soft enrichment.
        kf_hits: list[dict[str, Any]] = []
        knowledge_corpus: dict[str, Any] = {}
        open_intelligence: dict[str, Any] = {}
        finance_retrieval: dict[str, Any] = {}
        evidence_verification: dict[str, Any] = {}
        investment_intelligence: dict[str, Any] = {}
        forecast_learning: dict[str, Any] = {}
        research_intelligence: dict[str, Any] = {}
        semantic_research: dict[str, Any] = {}
        market_events: dict[str, Any] = {}
        context_assembly: dict[str, Any] = {}
        intelligence_bus: dict[str, Any] = {}
        valuation: dict[str, Any] = {}
        finance_academy: dict[str, Any] = {}
        academy_books: dict[str, Any] = {}
        sector_intelligence: dict[str, Any] = {}
        live_evidence: dict[str, Any] = {}
        company_dossier: dict[str, Any] = {}
        institutional_knowledge: dict[str, Any] = {}
        ikl_answer_hints: list[str] = []
        data_validation: dict[str, Any] = {}
        evidence_completion: dict[str, Any] = {}
        company_analysis: dict[str, Any] = {}
        company_monitor: dict[str, Any] = {}
        intelligence_construction: dict[str, Any] = {}
        answer_construction: dict[str, Any] = {}
        decision_engine: dict[str, Any] = {}
        intelligence_layer: dict[str, Any] = {}
        used_cae = False

        # Degradation ledger — optional collectors/deps never block a briefing.
        # `slim` already resolved after entity binding (gates RQ cascade + live fan-out).
        degradation: dict[str, Any] = {
            "faa": "background_only",
            "market_data": "cached" if slim else "live",
            "news": "cached" if slim else "live",
            "reasoning": "pending",
            "ask_slim": slim,
        }

        # Existing-intelligence bridge: retrieve only the research datasets required
        # by this question. Forecasts remain typed estimates, never observed facts.
        try:
            from research_intelligence_tool.production import (
                soft_slice_for_ask_agi as research_intelligence_slice,
            )

            research_intelligence = research_intelligence_slice(
                q,
                {"ticker": detected_ticker},
            ) or {}
            if research_intelligence.get("matched"):
                failures = (
                    ((research_intelligence.get("sections") or {}).get("DATA_QUALITY") or {}).get(
                        "retrieval_failures"
                    )
                    or []
                )
                degradation["research_intelligence"] = "degraded" if failures else "ok"
        except Exception:
            research_intelligence = {}
            degradation["research_intelligence"] = "unavailable"

        # Sprint 6.4 KRIG — Knowledge Bundle soft-wire (IE never discovers Yahoo/NSE/BSE).
        # Soft / timed: Ask must not block if Knowledge Platform is down.
        pipeline.mark(STAGE_RETRIEVAL_STARTED, status="ok")
        try:
            from app.kaip_client import KrigClient

            def _krig_pull() -> dict[str, Any]:
                client = KrigClient(timeout_seconds=2.5)
                if len(comparison_tickers) >= 2:
                    # Use the comparison endpoint: /bundle with a primary symbol
                    # silently produced a one-company brief for questions such as
                    # "Compare ICICI Bank and HDFC Bank".
                    try:
                        comparison = client.compare(comparison_tickers, question=q) or {}
                        if comparison:
                            return comparison
                    except Exception:
                        # Older Knowledge Platform deployments may not yet expose
                        # /compare.  The regular bundle still receives both sides.
                        pass
                    return client.retrieve_bundle(question=q, symbols=comparison_tickers) or {}
                symbols = [detected_ticker] if detected_ticker else ([ticker.upper()] if ticker else None)
                return client.retrieve_bundle(question=q, symbols=symbols) or {}

            krig_result, krig_timed_out = call_with_timeout(
                _krig_pull,
                timeout_sec=3.0,
                default={},
            )
            knowledge_bundle = krig_result if isinstance(krig_result, dict) else {}
            if krig_timed_out:
                degradation["krig"] = "timeout_cached"
            elif knowledge_bundle:
                degradation["krig"] = "ok"
                if len(comparison_tickers) >= 2:
                    ask_orchestration["comparison_retrieval"] = {
                        "mode": "krig_compare",
                        "tickers": comparison_tickers,
                    }
            else:
                degradation["krig"] = "empty"
        except Exception:
            knowledge_bundle = {}
            degradation["krig"] = "unavailable"

        # LEO v1.0 — gather / verify / package live evidence BEFORE Academy + SIF + IRP
        # ASK_SLIM skips live fan-out (Render Starter OOM under parallel Yahoo/Agib).
        if slim:
            live_evidence = {}
            degradation["live_evidence"] = "skipped_slim"
        else:
            try:
                from leo.production import package_for_query as leo_package

                live_evidence, leo_to = call_with_timeout(
                    leo_package,
                    q,
                    ticker=detected_ticker,
                    engine="ask_agi",
                    eve=self.eve,
                    kip=self.kip,
                    aoi=self.aoi,
                    mee=self.mee,
                    timeout_sec=5.0,
                    default={},
                )
                live_evidence = live_evidence or {}
                if leo_to:
                    degradation["live_evidence"] = "timeout_cached"
                    degradation["market_data"] = "cached"
                if live_evidence.get("ticker") and not detected_ticker:
                    detected_ticker = str(live_evidence["ticker"]).upper()
            except Exception:
                live_evidence = {}
                degradation["live_evidence"] = "unavailable"

        # FAPI + SIF — sector framework then Finance Academy (consume LEO evidence_supplied)
        leo_supplied = (live_evidence.get("sif_evidence_supplied") or {}) if isinstance(live_evidence, dict) else {}
        try:
            from academy.fapi.production import package_for_query

            finance_academy = package_for_query(q, engine="ask_agi", ticker=detected_ticker) or {}
            sector_intelligence = finance_academy.get("sector_intelligence") or {}
            if sector_intelligence.get("ticker") and not detected_ticker:
                detected_ticker = str(sector_intelligence["ticker"]).upper()
        except Exception:
            finance_academy = {}
            sector_intelligence = {}

        # Academy Books soft slice — frameworks/terminology for IRW + UI (never book text)
        try:
            from academy.books.production import research_writer_slice as books_slice_fn

            academy_books = books_slice_fn(q, ticker=detected_ticker) or {}
            if isinstance(academy_books, dict) and academy_books.get("enabled") and isinstance(finance_academy, dict):
                hints = list(finance_academy.get("answer_hints") or [])
                for h in (academy_books.get("logic_hints") or [])[:4]:
                    if h and h not in hints:
                        hints.append(h)
                if hints:
                    finance_academy = {
                        **finance_academy,
                        "answer_hints": hints[:12],
                        "academy_books_soft": True,
                        "book_frameworks": list(academy_books.get("frameworks") or [])[:8],
                    }
        except Exception:
            academy_books = {}

        if not sector_intelligence or leo_supplied:
            try:
                from sif.production import analyse_query as sif_analyse

                sector_intelligence = (
                    sif_analyse(
                        q,
                        ticker=detected_ticker,
                        engine="ask_agi",
                        evidence_supplied=leo_supplied or None,
                        kip=self.kip,
                        eve=self.eve,
                        aws=self.aws,
                    )
                    or sector_intelligence
                    or {}
                )
                if sector_intelligence.get("ticker") and not detected_ticker:
                    detected_ticker = str(sector_intelligence["ticker"]).upper()
            except Exception:
                if not sector_intelligence:
                    sector_intelligence = {}

        # Semantic Research Retrieval V2 runs after Sector Intelligence so thematic
        # questions can complete a controlled second hop into current confirmation.
        try:
            from semantic_research_retrieval.production import (
                package_for_ask_agi as semantic_research_package,
            )

            semantic_research = semantic_research_package(
                q,
                kip=self.kip,
                ticker=detected_ticker,
                current_intelligence=research_intelligence,
                sector_intelligence=sector_intelligence,
            ) or {}
            degradation["semantic_research"] = (
                "ok"
                if (semantic_research.get("answerability") or {}).get("may_answer")
                else "insufficient"
            )
        except Exception:
            semantic_research = {}
            degradation["semantic_research"] = "unavailable"

        # CID v1.0 — load living company dossier FIRST for company analysis (never rebuild from raw APIs)
        try:
            from cid.production import package_for_ask_agi as cid_package

            cid_budget_s = 8.0 if slim else 20.0
            company_dossier, cid_to = call_with_timeout(
                cid_package,
                q,
                ticker=detected_ticker,
                leo_pkg=live_evidence if isinstance(live_evidence, dict) else None,
                finance_academy=finance_academy if isinstance(finance_academy, dict) else None,
                sif_pkg=sector_intelligence if isinstance(sector_intelligence, dict) else None,
                timeout_sec=cid_budget_s,
                default={},
            )
            company_dossier = company_dossier if isinstance(company_dossier, dict) else {}
            if cid_to:
                degradation["cid"] = "timeout"
                # Prefer empty dossier over hanging Ask — CMS/KIP continue below.
                company_dossier = company_dossier or {"enabled": False, "timeout": True, "ticker": detected_ticker}
            if company_dossier.get("ticker") and not detected_ticker:
                detected_ticker = str(company_dossier["ticker"]).upper()
            # Prefer dossier-embedded SIF when richer
            if not sector_intelligence.get("sector_id") and (company_dossier.get("sector_framework") or {}).get("sector_id"):
                sector_intelligence = {
                    **sector_intelligence,
                    "sector_id": company_dossier["sector_framework"].get("sector_id"),
                    "sector_name": company_dossier["sector_framework"].get("sector_name"),
                    "priority_metrics": (company_dossier.get("sector_kpis") or {}).get("priority_metrics") or [],
                    "from_cid": True,
                }
        except Exception:
            company_dossier = live_evidence.get("company_dossier") if isinstance(live_evidence, dict) else {}
            company_dossier = company_dossier or {}

        # IKL — consult persistent institutional memory BEFORE raw documents
        ikl_answer_hints: list[str] = []
        try:
            from institutional_knowledge_layer.production import ask_consult as ikl_ask_consult

            institutional_knowledge = (
                ikl_ask_consult(
                    q,
                    ticker=detected_ticker,
                    companies=comparison_tickers or ([detected_ticker] if detected_ticker else None),
                )
                or {}
            )
            if isinstance(institutional_knowledge, dict) and institutional_knowledge.get("enabled"):
                ask_orchestration["ikl"] = {
                    "layers_hit": institutional_knowledge.get("layers_hit") or [],
                    "confidence": institutional_knowledge.get("confidence"),
                    "explainability": institutional_knowledge.get("explainability") or {},
                    "primary_before_raw_documents": True,
                }
                ikl_answer_hints = [
                    str(h)[:280] for h in (institutional_knowledge.get("answer_hints") or [])[:6] if h
                ]
                stage_timer.set_context(ikl=ask_orchestration.get("ikl") or {})
        except Exception:
            institutional_knowledge = {}
            ikl_answer_hints = []
        stage_timer.mark("ikl")

        # DVC V1 — load validated canonical values / conflict hints before answering
        try:
            from dvc.production import package_for_ask_agi as dvc_package

            data_validation, dvc_to = call_with_timeout(
                dvc_package,
                detected_ticker,
                timeout_sec=5.0 if slim else 12.0,
                default={},
            )
            data_validation = data_validation if isinstance(data_validation, dict) else {}
            if dvc_to:
                degradation["dvc"] = "timeout"
                data_validation = data_validation or {}
            data_validation = data_validation or {}
            # Prefer dossier-embedded DVC panel when already attached via CID
            if not data_validation.get("validated_fields") and isinstance(company_dossier.get("dvc"), dict):
                data_validation = {
                    "enabled": True,
                    "ticker": company_dossier.get("ticker"),
                    "validated_fields": company_dossier.get("validated_fields") or {},
                    "quality": (company_dossier.get("dvc") or {}).get("quality"),
                    "grades": (company_dossier.get("dvc") or {}).get("grades"),
                    "conflicts": (company_dossier.get("dvc") or {}).get("conflicts") or [],
                    "panel": company_dossier.get("data_quality_panel")
                    or (company_dossier.get("dvc") or {}).get("panel"),
                    "ask_agi_hints": [],
                    "answer_policy": "validated_canonical_values_only",
                    "from_cid": True,
                }
        except Exception:
            data_validation = {}

        # ECP V1 — complete missing evidence BEFORE IRP / recommendation gate evaluation
        # Hard timeout: ECP must not stack unbounded MarketData after LEO.
        if slim:
            evidence_completion = {}
            degradation["evidence_completion"] = "skipped_slim"
        try:
            from app.core.config import get_settings
            from ecp.production import soft_complete as ecp_soft_complete

            if (
                not slim
                and bool(getattr(get_settings(), "ecp", True))
                and bool(getattr(get_settings(), "ecp_before_irp", True))
            ):
                evidence_completion, ecp_to = call_with_timeout(
                    ecp_soft_complete,
                    query=q,
                    ticker=detected_ticker,
                    leo_pkg=live_evidence if isinstance(live_evidence, dict) else {},
                    cid=company_dossier if isinstance(company_dossier, dict) else {},
                    sif_pkg=sector_intelligence if isinstance(sector_intelligence, dict) else {},
                    dvc_pkg=data_validation if isinstance(data_validation, dict) else {},
                    kip=self.kip,
                    kf=self.kf,
                    timeout_sec=4.0,
                    default={},
                )
                evidence_completion = evidence_completion or {}
                if ecp_to:
                    degradation["evidence_completion"] = "timeout_cached"
                leo_delta = evidence_completion.get("leo_delta") or {}
                if leo_delta:
                    live_evidence = {**live_evidence, **leo_delta}
                cid_delta = evidence_completion.get("cid_delta") or {}
                if cid_delta:
                    company_dossier = {**company_dossier, **cid_delta}
                sif_delta = evidence_completion.get("sif_delta") or {}
                if sif_delta:
                    sector_intelligence = {**sector_intelligence, **sif_delta}
                    if sif_delta.get("sif_evidence_supplied"):
                        # Keep LEO-supplied map aligned for downstream soft consumers
                        live_evidence = {
                            **live_evidence,
                            "sif_evidence_supplied": sif_delta.get("sif_evidence_supplied"),
                        }
                # Refresh DVC panel from CID if ECP attached validated fields
                if company_dossier.get("validated_fields") and not (data_validation or {}).get("validated_fields"):
                    data_validation = {
                        **(data_validation or {}),
                        "enabled": True,
                        "validated_fields": company_dossier.get("validated_fields"),
                        "panel": company_dossier.get("data_quality_panel"),
                        "quality": (company_dossier.get("dvc") or {}).get("quality"),
                        "grades": (company_dossier.get("dvc") or {}).get("grades"),
                        "from_ecp": True,
                    }
        except Exception:
            evidence_completion = {}
            degradation["evidence_completion"] = "unavailable"

        if slim:
            degradation["context_assembly"] = "skipped_slim"
        if self.cae and q and not slim:
            try:
                assembled = dump(soft(self.cae.assemble_for_ask_agi, q, ticker=detected_ticker)) or {}
                if isinstance(assembled, dict) and assembled.get("soft_fields"):
                    used_cae = True
                    cae_soft = assembled.get("soft_fields") or {}
                    context_assembly = {
                        "answer_policy": assembled.get("answer_policy") or "unified_context_before_reasoning",
                        "package": assembled.get("package") or {},
                        "guidance": assembled.get("guidance") or {},
                    }
                    knowledge_corpus = cae_soft.get("knowledge_corpus") or {}
                    open_intelligence = cae_soft.get("open_intelligence") or {}
                    evidence_verification = cae_soft.get("evidence_verification") or {}
                    investment_intelligence = cae_soft.get("investment_intelligence") or {}
                    forecast_learning = cae_soft.get("forecast_learning") or {}
                    market_events = cae_soft.get("market_events") or {}
                    kf_hits = list((cae_soft.get("knowledge_foundation") or {}).get("hits") or [])
                    if not finance_academy.get("concept_ids") and isinstance(cae_soft.get("finance_academy"), dict):
                        finance_academy = cae_soft.get("finance_academy") or finance_academy
                    if (not live_evidence.get("evidence_objects")) and isinstance(
                        cae_soft.get("live_evidence"), dict
                    ):
                        live_evidence = cae_soft.get("live_evidence") or live_evidence
                    if (not company_dossier.get("ticker")) and isinstance(
                        cae_soft.get("company_dossier"), dict
                    ):
                        company_dossier = cae_soft.get("company_dossier") or company_dossier
                    if assembled.get("primary_ticker") and not detected_ticker:
                        safe = accept_detected_ticker(
                            assembled["primary_ticker"], ere_blocked=ere_research_blocked
                        )
                        if safe:
                            detected_ticker = safe
                            ask_orchestration["ticker_source"] = ask_orchestration.get(
                                "ticker_source"
                            ) or "cae"
                        else:
                            ask_orchestration["ticker_rejects"].append(
                                {"raw": assembled.get("primary_ticker"), "source": "cae"}
                            )
            except Exception:
                used_cae = False
                context_assembly = {}
        if not used_cae:
            if self.mee and q:
                try:
                    market_events = dump(soft(self.mee.consult, q, limit=8)) or {}
                    if isinstance(market_events, dict):
                        company_pack = market_events.get("company") or {}
                        if isinstance(company_pack, dict) and company_pack.get("company_id") and not detected_ticker:
                            events = company_pack.get("events") or []
                            if events and events[0].get("company_symbols"):
                                detected_ticker = str(events[0]["company_symbols"][0]).upper()
                except Exception:
                    market_events = {}
            if self.fle and q:
                try:
                    forecast_learning = dump(soft(self.fle.consult, q, limit=8)) or {}
                    if isinstance(forecast_learning, dict):
                        company_pack = forecast_learning.get("company") or {}
                        if isinstance(company_pack, dict) and company_pack.get("company_id") and not detected_ticker:
                            pending = company_pack.get("pending_forecasts") or []
                            if pending and pending[0].get("company_symbol"):
                                detected_ticker = str(pending[0]["company_symbol"]).upper()
                except Exception:
                    forecast_learning = {}
            if self.iie and q:
                try:
                    investment_intelligence = dump(soft(self.iie.consult, q, limit=8)) or {}
                    if isinstance(investment_intelligence, dict):
                        company_pack = investment_intelligence.get("company") or {}
                        if isinstance(company_pack, dict) and company_pack.get("symbol") and not detected_ticker:
                            detected_ticker = str(company_pack["symbol"]).upper()
                except Exception:
                    investment_intelligence = {}
            if self.eve and q:
                try:
                    evidence_verification = dump(soft(self.eve.consult, q, limit=8)) or {}
                    if isinstance(evidence_verification, dict):
                        company_pack = evidence_verification.get("company") or {}
                        if isinstance(company_pack, dict) and company_pack.get("symbol") and not detected_ticker:
                            detected_ticker = str(company_pack["symbol"]).upper()
                except Exception:
                    evidence_verification = {}
            if self.aoi and q:
                try:
                    open_intelligence = dump(soft(self.aoi.consult, q, limit=8)) or {}
                    if isinstance(open_intelligence, dict):
                        company_pack = open_intelligence.get("company") or {}
                        co = company_pack.get("company") if isinstance(company_pack, dict) else None
                        if isinstance(co, dict) and co.get("nse_symbol") and not detected_ticker:
                            detected_ticker = str(co["nse_symbol"]).upper()
                except Exception:
                    open_intelligence = {}
            if self.fre and q:
                try:
                    finance_retrieval, fre_to = call_with_timeout(
                        self.fre.consult,
                        q,
                        limit=8,
                        timeout_sec=3.0,
                        default={},
                    )
                    finance_retrieval = dump(finance_retrieval) or {}
                    if fre_to:
                        degradation["finance_retrieval"] = "timeout_cached"
                    if isinstance(finance_retrieval, dict):
                        for hit in finance_retrieval.get("hits") or []:
                            if isinstance(hit, dict) and hit.get("symbol") and not detected_ticker:
                                detected_ticker = str(hit["symbol"]).upper()
                                break
                except Exception:
                    finance_retrieval = {}
            if self.kc and q:
                try:
                    knowledge_corpus = dump(soft(self.kc.consult, q, limit=8)) or {}
                    kf_hits = list(knowledge_corpus.get("hits") or []) if isinstance(knowledge_corpus, dict) else []
                except Exception:
                    knowledge_corpus = {}
                    kf_hits = []
            if not kf_hits and self.kf and q:
                try:
                    kf_search = dump(soft(self.kf.search, q, limit=8)) or {}
                    kf_hits = list(kf_search.get("hits") or []) if isinstance(kf_search, dict) else []
                except Exception:
                    kf_hits = []
            if q and kf_hits and not detected_ticker:
                for hit in kf_hits:
                    if isinstance(hit, dict) and hit.get("kind") == "company" and hit.get("key"):
                        detected_ticker = str(hit["key"]).upper()
                        break

        # FRE soft consult — indexed/seed corpus only (never faa.acquire on Ask).
        if self.fre and q and not finance_retrieval:
            try:
                finance_retrieval, fre_to = call_with_timeout(
                    self.fre.consult,
                    q,
                    limit=8,
                    timeout_sec=3.0,
                    default={},
                )
                finance_retrieval = dump(finance_retrieval) or {}
                if fre_to:
                    degradation["finance_retrieval"] = "timeout_cached"
                else:
                    degradation["finance_retrieval"] = "cached_index"
            except Exception:
                finance_retrieval = {}
                degradation["finance_retrieval"] = "unavailable"

        # VE soft consult — intrinsic value / MoS before reasoning (CAE and fallback paths).
        if self.ve and q:
            try:
                valuation = dump(soft(self.ve.consult, q, limit=8)) or {}
                if isinstance(valuation, dict):
                    company_pack = valuation.get("company") or {}
                    if isinstance(company_pack, dict) and company_pack.get("company_symbol") and not detected_ticker:
                        detected_ticker = str(company_pack["company_symbol"]).upper()
            except Exception:
                valuation = {}

        # Company Analysis Engine V1 — apply Academy to THIS company before IRP (not Context Assembly)
        try:
            from company_analysis.production import package_for_ask_agi as company_analysis_package

            if detected_ticker or q:
                company_analysis = (
                    company_analysis_package(
                        q,
                        ticker=detected_ticker,
                        cid=company_dossier if isinstance(company_dossier, dict) else None,
                        finance_academy=finance_academy if isinstance(finance_academy, dict) else None,
                        sif_pkg=sector_intelligence if isinstance(sector_intelligence, dict) else None,
                        leo_pkg=live_evidence if isinstance(live_evidence, dict) else None,
                        dvc_pkg=data_validation if isinstance(data_validation, dict) else None,
                        valuation_pack=valuation if isinstance(valuation, dict) else None,
                        forecast_learning=forecast_learning if isinstance(forecast_learning, dict) else None,
                        market_events=market_events if isinstance(market_events, dict) else None,
                    )
                    or {}
                )
                if company_analysis.get("ticker") and not detected_ticker:
                    detected_ticker = str(company_analysis["ticker"]).upper()
        except Exception:
            company_analysis = {}

        # Company Monitoring System V1 — what changed since prior snapshot/quarter (never auto house-view)
        try:
            from company_monitor.production import package_for_ask_agi as company_monitor_package

            if detected_ticker:
                company_monitor = (
                    company_monitor_package(
                        q,
                        ticker=detected_ticker,
                        run_monitor=not slim,
                        layers={
                            "cid": company_dossier if isinstance(company_dossier, dict) else {},
                            "leo_pkg": live_evidence if isinstance(live_evidence, dict) else {},
                            "financial": (company_analysis or {}).get("financial_intelligence") or {},
                            "valuation": (company_analysis or {}).get("valuation_intelligence")
                            or (valuation if isinstance(valuation, dict) else {}),
                            "company_analysis": company_analysis if isinstance(company_analysis, dict) else {},
                            "house_view": {},
                            "predictions": [],
                        },
                    )
                    or {}
                )
        except Exception:
            company_monitor = {}

        # Investment Office V1 — executive desk context for Ask AGI (aggregate only)
        investment_office_pkg: dict[str, Any] = {}
        try:
            from investment_office.production import package_for_ask_agi as io_package

            investment_office_pkg = io_package(q, ticker=detected_ticker) or {}
            for hint in (investment_office_pkg.get("ask_agi_hints") or [])[:3]:
                cleaned = scrub_text(hint)
                if cleaned:
                    # Collected into why later with other ask_agi_hints
                    pass
        except Exception:
            investment_office_pkg = {}

        # Multi-source retrieval — Private Markets + Valuation CMS + Nifty research.
        # Soft-wire only; never blocks Ask if adapters fail.
        multi_source_pack: dict[str, Any] = {}
        try:
            from multi_source import retrieve_multi_source

            multi_source_pack, ms_to = call_with_timeout(
                retrieve_multi_source,
                q,
                ticker=detected_ticker,
                entities=(entity_resolution or {}).get("entities")
                if isinstance(entity_resolution, dict)
                else None,
                timeout_sec=3.0,
                default={},
            )
            multi_source_pack = multi_source_pack if isinstance(multi_source_pack, dict) else {}
            if ms_to:
                degradation["multi_source"] = "timeout_cached"
            elif multi_source_pack.get("evidence_count"):
                degradation["multi_source"] = "ok"
            else:
                degradation["multi_source"] = "empty"
        except Exception:
            multi_source_pack = {}
            degradation["multi_source"] = "unavailable"
        stage_timer.mark("retrieval")
        # Phase-1 observability — retrieval completed + per-source rows from degradation ledger
        try:
            for _src in sources_from_degradation(degradation):
                pipeline.set_source(
                    str(_src.get("key") or _src.get("name") or "source"),
                    searched=bool(_src.get("searched")),
                    latency_ms=int(_src.get("latency_ms") or 0),
                    returned=int(_src.get("returned") or 0),
                    selected=int(_src.get("selected") or 0),
                    status=str(_src.get("status") or "ok"),
                )
            # Enrich returned counts from soft packs when available (labels only).
            if isinstance(knowledge_bundle, dict) and knowledge_bundle:
                pipeline.set_source(
                    "krig",
                    searched=True,
                    returned=int(knowledge_bundle.get("document_count") or len(knowledge_bundle.get("documents") or []) or 0),
                    selected=min(8, int(knowledge_bundle.get("document_count") or 0)),
                    status=str(degradation.get("krig") or "ok"),
                )
            if isinstance(multi_source_pack, dict):
                pipeline.set_source(
                    "multi_source",
                    searched=degradation.get("multi_source") not in {None, "unavailable", "skipped_slim"},
                    returned=int(multi_source_pack.get("evidence_count") or 0),
                    selected=min(8, int(multi_source_pack.get("evidence_count") or 0)),
                    status=str(degradation.get("multi_source") or "ok"),
                )
            if isinstance(live_evidence, dict):
                pipeline.set_source(
                    "live_evidence",
                    searched=degradation.get("live_evidence") not in {None, "unavailable", "skipped_slim"},
                    returned=int(live_evidence.get("evidence_count") or 0),
                    selected=min(8, int(live_evidence.get("evidence_count") or 0)),
                    status=str(degradation.get("live_evidence") or "ok"),
                )
            # Soft packs — labels/counts only (no retrieval behavior change).
            for _key, _pack, _count_keys in (
                ("valuation", locals().get("valuation"), ("evidence_count", "hit_count", "items")),
                ("kip", locals().get("kip_pack") or locals().get("kip"), ("evidence_count", "documents", "hits")),
                (
                    "finance_academy",
                    locals().get("finance_academy"),
                    ("evidence_count", "passages", "hits"),
                ),
                (
                    "finance_retrieval",
                    locals().get("finance_retrieval"),
                    ("evidence_count", "hits"),
                ),
                (
                    "market_indices",
                    locals().get("market_indices"),
                    ("membership_count", "indices", "hits"),
                ),
            ):
                if not isinstance(_pack, dict) or not _pack:
                    continue
                _ret = 0
                for _ck in _count_keys:
                    _v = _pack.get(_ck)
                    if isinstance(_v, int):
                        _ret = _v
                        break
                    if isinstance(_v, list):
                        _ret = len(_v)
                        break
                pipeline.set_source(
                    _key,
                    searched=True,
                    returned=int(_ret or 0),
                    selected=min(8, int(_ret or 0)),
                    status=str(degradation.get(_key) or "ok"),
                )
            pipeline.mark(STAGE_RETRIEVAL_COMPLETED, status="ok")
        except Exception:
            pipeline.mark(STAGE_RETRIEVAL_COMPLETED, status="degraded")

        # AGIB v2.1 — Complete Ask Pipeline (soft-wire).
        # Context → Intent → Entities → KF retrieval → Evidence → IRO plan → DAG
        # → existing govern_answer (Phase 1–7) → DQ record → IOI register → telemetry.
        # Does not redesign reasoning / KF / governance internals.
        execution_governance: dict[str, Any] = {}
        ask_pipeline_runtime: dict[str, Any] = {}
        try:
            from institutional_reasoning.execution_governance import (
                enforce_editorial,
                governed_executive,
                telemetry_rows,
            )
            from institutional_reasoning.telemetry_sink import persist_rows
            from ask_pipeline.pipeline import run_complete_ask

            # Bound complete-ask soft-wire so retrieval-heavy prompts (SMOKE-04)
            # cannot hold the gateway until ASK_ENGINE_TIMEOUT_MS.
            rca_budget_s = 20.0 if slim else 40.0

            def _run_rca():
                return run_complete_ask(
                    q,
                    ticker_hint=detected_ticker,
                    entity_resolution_pack=entity_resolution if isinstance(entity_resolution, dict) else None,
                    extra_packs={
                        "valuation": valuation if isinstance(valuation, dict) else {},
                        "company_analysis": company_analysis if isinstance(company_analysis, dict) else {},
                        "data_validation": data_validation if isinstance(data_validation, dict) else {},
                        "finance_retrieval": finance_retrieval if isinstance(finance_retrieval, dict) else {},
                        "sector_intelligence": sector_intelligence if isinstance(sector_intelligence, dict) else {},
                        "live_evidence": live_evidence if isinstance(live_evidence, dict) else {},
                        "research_intelligence": research_intelligence
                        if isinstance(research_intelligence, dict)
                        else {},
                        "semantic_research": semantic_research
                        if isinstance(semantic_research, dict)
                        else {},
                        "company_dossier": company_dossier if isinstance(company_dossier, dict) else {},
                        "multi_source": multi_source_pack if isinstance(multi_source_pack, dict) else {},
                    },
                    academy=finance_academy if isinstance(finance_academy, dict) else None,
                )

            ask_pipeline_runtime, rca_to = call_with_timeout(
                _run_rca,
                timeout_sec=rca_budget_s,
                default={},
            )
            ask_pipeline_runtime = ask_pipeline_runtime if isinstance(ask_pipeline_runtime, dict) else {}
            if rca_to:
                degradation["complete_ask"] = "timeout"
                ask_orchestration["complete_ask"] = {
                    "status": "timeout",
                    "budget_s": rca_budget_s,
                }
            execution_governance = ask_pipeline_runtime.get("governance") or {}
            _iere = (ask_pipeline_runtime.get("knowledge") or {}).get("iere") or {}
            _ice = ask_pipeline_runtime.get("communication") or {}
            _pb = ask_pipeline_runtime.get("playbook_selection") or {}
            _eg = ask_pipeline_runtime.get("evidence_graph") or {}
            _im = ask_pipeline_runtime.get("institutional_memory") or {}
            execution_governance["ask_pipeline"] = {
                "pipeline_id": ask_pipeline_runtime.get("pipeline_id"),
                "replay_id": ask_pipeline_runtime.get("replay_id"),
                "pipeline_version": ask_pipeline_runtime.get("pipeline_version"),
                "intent": (ask_pipeline_runtime.get("intent") or {}).get("intent"),
                "institutionally_complete": ask_pipeline_runtime.get("institutionally_complete"),
                "quality_gates": ask_pipeline_runtime.get("quality_gates"),
                "modules_executed": (ask_pipeline_runtime.get("telemetry") or {}).get("modules_executed"),
                "modules_skipped": (ask_pipeline_runtime.get("telemetry") or {}).get("modules_skipped"),
                "decision_id": (ask_pipeline_runtime.get("decision_quality") or {}).get("decision_id"),
                "outcome_decision_id": (ask_pipeline_runtime.get("outcome") or {}).get("decision_id"),
                "evidence_coverage": (ask_pipeline_runtime.get("evidence") or {}).get("coverage"),
                "knowledge_primary": (ask_pipeline_runtime.get("knowledge") or {}).get("primary_engine")
                or "knowledge_factory",
                "iere_retrieval_id": (ask_pipeline_runtime.get("evidence") or {}).get("iere_retrieval_id")
                or _iere.get("retrieval_id"),
                "iere_ranked_count": _iere.get("ranked_count"),
                "latency_ms": ask_pipeline_runtime.get("latency_ms"),
                # AGIB v3.4 Track D — ICE metadata (soft)
                "ice_version": _ice.get("ice_version")
                or ask_pipeline_runtime.get("institutional_communication_version"),
                "ice_template": _ice.get("template"),
                "ice_framework_visible": _ice.get("framework_visible"),
                "ice_validation_passed": (_ice.get("validation") or {}).get("passed"),
                # AGIB v3.5 — IAP metadata (soft)
                "iap_version": (_pb.get("iap_version") if isinstance(_pb, dict) else None)
                or ask_pipeline_runtime.get("playbook_selection_version"),
                "iap_playbook_id": (_pb.get("playbook_id") if isinstance(_pb, dict) else None),
                "iap_category": (_pb.get("category") if isinstance(_pb, dict) else None),
                "ieg_version": (_eg.get("ieg_version") if isinstance(_eg, dict) else None)
                or ask_pipeline_runtime.get("evidence_graph_version"),
                "ieg_graph_id": (_eg.get("graph_id") if isinstance(_eg, dict) else None),
                "ieg_domain_coverage_pct": (_eg.get("domain_coverage_pct") if isinstance(_eg, dict) else None),
                "ieg_n_nodes": (_eg.get("n_nodes") if isinstance(_eg, dict) else None),
                "imai_version": (_im.get("imai_version") if isinstance(_im, dict) else None)
                or ask_pipeline_runtime.get("institutional_memory_version"),
                "imai_have_we_seen_this_before": (
                    _im.get("have_we_seen_this_before") if isinstance(_im, dict) else None
                ),
                "imai_top_memory_ids": (_im.get("top_memory_ids") if isinstance(_im, dict) else None),
            }
            execution_governance["institutional_communication"] = {
                "template": _ice.get("template"),
                "ice_version": _ice.get("ice_version"),
                "framework_visible": _ice.get("framework_visible"),
                "section_order": _ice.get("section_order"),
                "validation": _ice.get("validation"),
            }
            if isinstance(_pb, dict) and _pb.get("playbook_id"):
                execution_governance["playbook_selection"] = {
                    "playbook_id": _pb.get("playbook_id"),
                    "playbook_name": _pb.get("playbook_name"),
                    "category": _pb.get("category"),
                    "iap_version": _pb.get("iap_version"),
                    "guides_reasoning": True,
                }
            if isinstance(_eg, dict) and _eg.get("graph_id"):
                execution_governance["evidence_graph"] = {
                    "graph_id": _eg.get("graph_id"),
                    "entities": _eg.get("entities"),
                    "n_nodes": _eg.get("n_nodes"),
                    "domain_coverage_pct": _eg.get("domain_coverage_pct"),
                    "ieg_version": _eg.get("ieg_version"),
                    "guides_evidence": True,
                }
            if isinstance(_im, dict) and (_im.get("top_memory_ids") or _im.get("have_we_seen_this_before")):
                execution_governance["institutional_memory"] = {
                    "imai_version": _im.get("imai_version"),
                    "have_we_seen_this_before": _im.get("have_we_seen_this_before"),
                    "top_memory_ids": _im.get("top_memory_ids"),
                    "regimes": _im.get("regimes"),
                    "guides_memory": True,
                    "invented_analogues": False,
                }
            telemetry = persist_rows(
                telemetry_rows(execution_governance, answer_id=execution_governance.get("run_id"))
            )
            execution_governance["telemetry"] = {
                "ok": telemetry.get("ok"),
                "sink": telemetry.get("sink"),
                "written": telemetry.get("written"),
                "ask_pipeline": ask_pipeline_runtime.get("telemetry"),
            }
        except Exception:
            execution_governance = {}
            ask_pipeline_runtime = {}

        # Finalize execution policy against VE / FRE / CA evidence packs.
        try:
            from institutional_reasoning.execution_policy import finalize_for_ask_agi as fep_finalize

            if execution_policy.get("required_frameworks"):
                execution_policy = fep_finalize(
                    execution_policy,
                    valuation=valuation if isinstance(valuation, dict) else None,
                    company_analysis=company_analysis if isinstance(company_analysis, dict) else None,
                    finance_retrieval=finance_retrieval if isinstance(finance_retrieval, dict) else None,
                    sector_intelligence=sector_intelligence if isinstance(sector_intelligence, dict) else None,
                    live_evidence=live_evidence if isinstance(live_evidence, dict) else None,
                    decision_engine=None,
                    peer=(company_analysis or {}).get("peer_intelligence")
                    if isinstance(company_analysis, dict)
                    else None,
                )
        except Exception:
            pass

        # IRP V1 — think (intent → entities → plan → retrieve → reason) before answering.
        if self.irp and q:
            try:
                irp_budget_s = 25.0 if slim else 50.0
                irp_pkg, irp_to = call_with_timeout(
                    lambda: soft(self.irp.run, q, ticker=detected_ticker),
                    timeout_sec=irp_budget_s,
                    default=None,
                )
                if irp_to:
                    degradation["irp"] = "timeout"
                    ask_orchestration["irp"] = {"status": "timeout", "budget_s": irp_budget_s}
                irp_dump = dump(irp_pkg) if irp_pkg is not None else {}
                if isinstance(irp_dump, dict) and irp_dump:
                    client = irp_dump.get("client_search") or {}
                    rsp_pkg = irp_dump.get("rsp") or {}
                    ents = irp_dump.get("entities") or {}
                    if not detected_ticker and isinstance(ents, dict) and ents.get("primary_ticker"):
                        safe = accept_detected_ticker(
                            ents["primary_ticker"], ere_blocked=ere_research_blocked
                        )
                        if safe:
                            detected_ticker = safe
                            ask_orchestration["ticker_source"] = ask_orchestration.get(
                                "ticker_source"
                            ) or "irp"
                        else:
                            ask_orchestration["ticker_rejects"].append(
                                {"raw": ents.get("primary_ticker"), "source": "irp"}
                            )
            except Exception:
                irp_pkg = None
                irp_dump = {}
        stage_timer.mark("reasoning")

        if self.kip and q and not client:
            l4 = None
            port = None
            if detected_ticker and self.aws:
                co = dump(soft(self.aws.company, detected_ticker)) or {}
                l4 = co.get("l4_opinion")
                port = {"weight": co.get("portfolio_weight")}
            req = ClientSearchRequest(
                question=q,
                ticker=detected_ticker,
                l4_opinion=l4,
                portfolio_exposure=port,
            )
            client = dump(soft(self.kip.client_search, req))
            if not detected_ticker and isinstance(client, dict):
                hv = client.get("house_view") or {}
                if hv.get("ticker"):
                    detected_ticker = str(hv["ticker"]).upper()

        aws_hits = dump(soft(self.aws.search, q, limit=12)) if self.aws and q else None
        hits = []
        for h in (aws_hits or {}).get("hits") or []:
            hits.append(
                {
                    "kind": h.get("kind"),
                    "id": h.get("id"),
                    "title": scrub_text(h.get("title")),
                    "score": h.get("score"),
                    "ticker": h.get("ticker"),
                    "snippet": scrub_text(h.get("snippet")),
                    "source": public_source(h.get("source")),
                }
            )

        evidence = (client or {}).get("evidence") or {}
        house = flatten_house_view(scrub((client or {}).get("house_view")))
        if isinstance(house, dict) and house.get("ticker"):
            tkr = str(house["ticker"]).upper()
            # Sector synthetic subjects (e.g. INDIA_IT) are not company tickers.
            if "_" not in tkr and tkr not in TICKER_STOPWORDS and (
                tkr in KNOWN_TICKERS or tkr.endswith("BANK")
            ):
                if not detected_ticker:
                    detected_ticker = tkr

        conf = None
        if isinstance(evidence, dict):
            conf = evidence.get("confidence_score")
        if conf is None and isinstance(house, dict):
            conf = house.get("confidence") or house.get("research_confidence")

        # Soft RSP reasoning package for thesis / bull / bear / risks
        # (skipped when IRP already ran the Research Committee pass)
        if not rsp_pkg and self.rsp and detected_ticker:
            raw = soft(self.rsp.reason_for_writer, q or f"{detected_ticker} search", ticker=detected_ticker)
            rsp_pkg = dump(raw) if raw is not None and not isinstance(raw, dict) else (raw or {})
            if not isinstance(rsp_pkg, dict):
                rsp_pkg = {}
            rsp_pkg = scrub(rsp_pkg) or {}
        elif rsp_pkg:
            rsp_pkg = scrub(rsp_pkg) or {}

        # Prefer IRP-ranked evidence, then rich RAG items, then raw document id lists.
        irp_ranked = []
        if isinstance(irp_dump, dict):
            irp_ranked = [
                {
                    "id": r.get("document_id"),
                    "document_id": r.get("document_id"),
                    "title": r.get("title"),
                    "snippet": r.get("snippet"),
                    "summary": r.get("snippet"),
                    "tickers": r.get("tickers") or [],
                    "stance": r.get("stance"),
                    "confidence": r.get("confidence"),
                    "freshness": r.get("freshness"),
                    "type": r.get("source_class") or "agi_research",
                    "source_class": r.get("source_class") or "agi_research",
                }
                for r in (irp_dump.get("ranked_evidence") or [])
                if isinstance(r, dict) and not r.get("rejected")
            ]
        supporting = _filter_junk_docs(
            self._hydrate_evidence(
                _evidence_dicts(
                    irp_ranked
                    or evidence.get("supporting_evidence")
                    or evidence.get("agi_research_used")
                    or evidence.get("documents_retrieved")
                    or []
                )
            )
        )
        news = _filter_junk_docs(self._hydrate_evidence(_evidence_dicts(evidence.get("news_used") or [])))
        articles = supporting[:8]
        irp_conflicts = []
        if isinstance(irp_dump, dict):
            for c in irp_dump.get("contradictions") or []:
                if not isinstance(c, dict):
                    continue
                irp_conflicts.append(
                    {
                        "title": c.get("topic") or "Research disagreement",
                        "summary": c.get("summary"),
                        "snippet": c.get("why") or c.get("summary"),
                        "type": "conflict",
                        "confidence": c.get("confidence"),
                    }
                )
        conflicting = _filter_junk_docs(
            self._hydrate_evidence(
                scrub(irp_conflicts or evidence.get("conflicting_opinions") or [])[:12]
            )
        )
        if not conflicting and isinstance(rsp_pkg.get("contradictions"), list):
            conflicting = scrub(rsp_pkg.get("contradictions") or [])[:12]

        evidence_used = scrub(
            [
                {"type": "agi_research", "items": evidence.get("agi_research_used") or []},
                {"type": "broker", "items": evidence.get("broker_reports_used") or []},
                {"type": "news", "items": evidence.get("news_used") or []},
                {"type": "filings", "items": evidence.get("filings_used") or []},
                {"type": "model_evidence", "items": evidence.get("engine_evidence") or []},
            ]
        )
        stage_timer.mark("ranking")

        related = []
        related_themes: list[str] = []
        related_sectors: list[str] = []
        irp_entities = (irp_dump or {}).get("entities") if isinstance(irp_dump, dict) else {}
        if isinstance(irp_entities, dict):
            related.extend([str(t) for t in (irp_entities.get("tickers") or [])])
            related_themes.extend([str(t) for t in (irp_entities.get("themes") or [])])
            if irp_entities.get("sector"):
                related_sectors.append(str(irp_entities.get("sector")))
            if irp_entities.get("sector_label"):
                related_sectors.append(str(irp_entities.get("sector_label")))
        for hit in kf_hits:
            if not isinstance(hit, dict):
                continue
            kind = str(hit.get("kind") or "")
            key = str(hit.get("key") or "")
            if kind == "company" and key:
                related.append(key.upper())
            elif kind == "theme" and key:
                related_themes.append(key)
            elif kind == "sector" and key:
                related_sectors.append(str(hit.get("label") or key))
        if isinstance(house, dict):
            related_themes.extend([str(x) for x in (house.get("themes") or [])])
            related_sectors.extend([str(x) for x in (house.get("sectors") or [])])
        for item in supporting:
            if not isinstance(item, dict):
                continue
            for t in item.get("tickers") or []:
                related.append(str(t))
        for h in hits:
            if h.get("ticker"):
                related.append(str(h["ticker"]))
            if h.get("kind") == "theme" and h.get("id"):
                related_themes.append(str(h["id"]))
        related = sorted(
            {
                r.upper()
                for r in related
                if r
                and str(r).upper() not in TICKER_STOPWORDS
                and (str(r).upper() in KNOWN_TICKERS or str(r).upper().endswith("BANK"))
            }
        )[:12]
        related_themes = sorted({t for t in related_themes if t})[:8]
        related_sectors = sorted({s for s in related_sectors if s})[:8]

        house_label = None
        if isinstance(house, dict) and house:
            house_label = normalize_stance(
                house.get("stance") or house.get("current_view_label") or house.get("label")
            )

        thesis = None
        bull: list[str] = []
        bear: list[str] = []
        risks: list[str] = []
        catalysts: list[str] = []
        if isinstance(house, dict) and house:
            thesis = clean_thesis_text(house.get("thesis") or house.get("summary"))
            bull = [str(x) for x in (house.get("bull_case") or [])][:6]
            bear = [str(x) for x in (house.get("bear_case") or [])][:6]
            risks = [str(x) for x in (house.get("risks") or house.get("failed_assumptions") or [])][:6]
            catalysts = [str(x) for x in (house.get("catalysts") or house.get("catalysts_occurred") or [])][:6]
            # Pull risks / catalysts from the latest source document backing the house view.
            cv = house.get("current_view")
            doc_id = cv.get("document_id") if isinstance(cv, dict) else None
            if self.kip and doc_id and (not risks or not catalysts or not bull or not bear or not thesis):
                src = soft(self.kip.get_document, doc_id)
                research = getattr(src, "research", None) if src is not None else None
                if research is not None:
                    if not bull:
                        bull = [str(x) for x in (research.bull_case or [])][:6]
                    if not bear:
                        bear = [str(x) for x in (research.bear_case or [])][:6]
                    if not risks:
                        risks = [str(x) for x in (research.risks or [])][:6]
                    if not catalysts:
                        catalysts = [str(x) for x in (research.catalysts or [])][:6]
                    if not thesis and research.investment_thesis:
                        thesis = clean_thesis_text(research.investment_thesis)
        # Fill thesis fields from strongest supporting evidence when house view is thin.
        if not thesis:
            for item in supporting:
                if isinstance(item, dict) and (item.get("snippet") or item.get("summary") or item.get("title")):
                    thesis = clean_thesis_text(
                        item.get("snippet") or item.get("summary") or item.get("title")
                    )
                    break
        if thesis and (not bull or not bear or not risks or not catalysts):
            synthesized = synthesize_thesis_points(thesis)
            if not bull:
                bull = synthesized["bull_case"]
            if not bear:
                bear = synthesized["bear_case"]
            if not risks:
                risks = synthesized["risks"]
            if not catalysts:
                catalysts = synthesized["catalysts"]
        if not bear:
            for item in supporting + conflicting:
                if isinstance(item, dict) and str(item.get("stance") or "").lower() == "bear":
                    snip = clean_thesis_text(item.get("snippet") or item.get("summary"))
                    if snip:
                        bear.append(snip[:220])
                if len(bear) >= 3:
                    break
        # IRP reasoning wins when present — this is the institutional think-step.
        irp_reasoning = (irp_dump or {}).get("reasoning") if isinstance(irp_dump, dict) else None
        if isinstance(irp_reasoning, dict) and irp_reasoning:
            thesis = clean_thesis_text(irp_reasoning.get("what_is_happening") or thesis) or thesis
            bull = [str(x) for x in (irp_reasoning.get("bull_case") or bull)][:6]
            bear = [str(x) for x in (irp_reasoning.get("bear_case") or bear)][:6]
            risks = [str(x) for x in (irp_reasoning.get("risks") or risks)][:6]
            catalysts = [str(x) for x in (irp_reasoning.get("catalysts") or catalysts)][:6]
            house_label = normalize_stance(irp_reasoning.get("stance") or house_label)
            if isinstance(house, dict):
                house = dict(house)
                house["stance"] = house_label
                house["label"] = house_label
                house["current_view_label"] = house_label
                house["thesis"] = thesis
                if irp_reasoning.get("confidence") is not None:
                    house["confidence"] = irp_reasoning.get("confidence")
                    conf = irp_reasoning.get("confidence")

        # Recompute stance from the cleaned thesis so "bull_case" field names cannot flip Bullish.
        if thesis and not (isinstance(irp_reasoning, dict) and irp_reasoning.get("stance")):
            house_label = normalize_stance(
                {"thesis": thesis, "bull_case": bull, "bear_case": bear}
            )
            if isinstance(house, dict) and house:
                house["stance"] = house_label
                house["label"] = house_label
                house["current_view_label"] = house_label
                house["thesis"] = thesis
        # RSP enrichment — never let a noisy research_brief overwrite a real AGI thesis.
        synth = rsp_pkg.get("synthesis") if isinstance(rsp_pkg.get("synthesis"), dict) else rsp_pkg
        if isinstance(synth, dict):
            rsp_thesis = clean_thesis_text(synth.get("thesis") or "")
            rsp_brief = clean_thesis_text(synth.get("research_brief") or "")
            if not thesis and rsp_thesis:
                thesis = rsp_thesis
            elif not thesis and rsp_brief and "research brief —" not in rsp_brief.lower():
                thesis = rsp_brief
            bull = bull or [str(x) for x in (synth.get("bull_case") or [])][:6]
            bear = bear or [str(x) for x in (synth.get("bear_case") or [])][:6]
            risks = risks or [str(x) for x in (synth.get("risks") or [])][:6]
            catalysts = catalysts or [str(x) for x in (synth.get("catalysts") or [])][:6]
            if thesis and isinstance(house, dict) and house:
                house["thesis"] = thesis
                house_label = normalize_stance(
                    {"thesis": thesis, "bull_case": bull, "bear_case": bear}
                )
                house["stance"] = house_label
                house["label"] = house_label
                house["current_view_label"] = house_label

        executive = _search_answer_summary(
            q,
            house if isinstance(house, dict) else None,
            conf,
            supporting,
            house_label=house_label,
        )
        why = _why_bullets(house if isinstance(house, dict) else None, supporting, news, house_label)
        # IKL memory hints — prepend evidence-backed institutional memory (before raw docs)
        if ikl_answer_hints:
            merged = [h for h in ikl_answer_hints if h not in why]
            why = (merged + why)[:16]

        # Prefer factual index membership / constituent answers when the question asks for them.
        mi_body = (market_indices or {}).get("market_indices") if isinstance(market_indices, dict) else {}
        if isinstance(mi_body, dict) and mi_body.get("answerable") and mi_body.get("direct_answer"):
            executive = scrub_text(mi_body.get("direct_answer")) or executive
            mi_bullets = [scrub_text(b) for b in (mi_body.get("bullets") or []) if b]
            if mi_bullets:
                why = mi_bullets[:12] + [w for w in why if w not in mi_bullets][:8]
            house_label = "Index Membership" if mi_body.get("mode") == "symbol_membership" else "Index Constituents"

        # Prefer richer SIF / Academy packages from IRP when present
        if isinstance(irp_dump, dict) and isinstance(irp_dump.get("sector_intelligence"), dict):
            irp_sif = irp_dump.get("sector_intelligence") or {}
            if irp_sif.get("sector_id"):
                sector_intelligence = irp_sif
        if isinstance(irp_dump, dict) and isinstance(irp_dump.get("finance_academy"), dict):
            irp_fa = irp_dump.get("finance_academy") or {}
            if len(irp_fa.get("concept_ids") or []) >= len(finance_academy.get("concept_ids") or []):
                finance_academy = irp_fa
        # Sector framework hints first, then Academy
        if sector_intelligence.get("answer_hints"):
            for hint in (sector_intelligence.get("answer_hints") or [])[:4]:
                if hint and hint not in why:
                    why.insert(0, scrub_text(hint)[:300])
        if finance_academy.get("is_finance") and finance_academy.get("answer_hints"):
            for hint in (finance_academy.get("answer_hints") or [])[:3]:
                if hint and hint not in why:
                    why.insert(0, scrub_text(hint)[:280])
            why = why[:10]
            if not thesis:
                thesis = scrub_text((finance_academy.get("answer_hints") or [None])[0])
            prov = finance_academy.get("provenance") or {}
            if prov.get("concept_ids"):
                # Translate Academy ids into plain institutional language — never expose snake_case ids.
                try:
                    from intelligence_construction.cio_prose import translate_academy_concept

                    translated = [
                        t
                        for t in (translate_academy_concept(cid) for cid in list(prov.get("concept_ids") or [])[:8])
                        if t
                    ]
                except Exception:
                    translated = []
                finance_academy = {
                    **finance_academy,
                    "influenced_answer": True,
                    "reasoning_points": translated[:8],
                }
        # CID first — reason from living dossier, not raw API rebuilds
        # Answer Construction V3: never inject raw Missing: checklist keys into why.
        if isinstance(company_dossier, dict) and company_dossier.get("ticker"):
            hint = company_dossier.get("reasoning_hint")
            if hint and hint not in why:
                why.insert(0, scrub_text(hint)[:320])
            why = why[:12]

        # DVC — mention conflicts; prefer validated canonical values (no provider / grade spam)
        if isinstance(data_validation, dict) and data_validation.get("enabled") is not False:
            for hint in (data_validation.get("ask_agi_hints") or [])[:4]:
                cleaned = scrub_text(hint)[:360]
                if cleaned and cleaned not in why and "winning_provider" not in cleaned.lower():
                    why.insert(0, cleaned)
            why = why[:12]

        # ECP — completion hints only (coverage / Missing checklists deferred to Recommendation Status)
        if isinstance(evidence_completion, dict) and evidence_completion.get("enabled") is not False:
            for hint in (evidence_completion.get("ask_agi_hints") or [])[:4]:
                cleaned = scrub_text(hint)[:400]
                if (
                    cleaned
                    and cleaned not in why
                    and "missing:" not in cleaned.lower()
                    and "recommendation withheld" not in cleaned.lower()
                ):
                    why.insert(0, cleaned)
            why = why[:12]

        # Company Analysis — applied Academy concepts (readiness gate is trailing, not lead why)
        if isinstance(company_analysis, dict) and company_analysis.get("enabled"):
            for hint in (company_analysis.get("ask_agi_hints") or [])[:4]:
                cleaned = scrub_text(hint)[:400]
                if (
                    cleaned
                    and cleaned not in why
                    and "readiness" not in cleaned.lower()
                    and "gate:" not in cleaned.lower()
                ):
                    why.insert(0, cleaned)
            bq = (company_analysis.get("business_quality") or {}).get("business_quality_score")
            if bq is not None:
                why.insert(0, scrub_text(f"Business quality score: {bq}/100.")[:200])
            why = why[:12]

        # Multi-source evidence — Private Markets / Valuation CMS / Nifty research
        if isinstance(multi_source_pack, dict) and multi_source_pack.get("evidence_count"):
            for hint in (multi_source_pack.get("ask_agi_hints") or [])[:6]:
                cleaned = scrub_text(hint)[:420]
                if cleaned and cleaned not in why:
                    why.insert(0, cleaned)
            why = why[:16]

        # Phase 1 governance enforcement — executive/stance derive from framework outputs.
        if isinstance(execution_governance, dict) and execution_governance.get("run_id"):
            try:
                from institutional_reasoning.execution_governance import (
                    enforce_editorial,
                    governed_executive,
                )

                gov_path = execution_governance.get("path")
                committee_gov = execution_governance.get("committee") or {}
                if gov_path == "clarification":
                    executive = scrub_text(governed_executive(execution_governance)) or executive
                    house_label = "Clarification required"
                elif gov_path == "research" and not execution_governance.get("narrative_allowed"):
                    executive = scrub_text(governed_executive(execution_governance)) or executive
                    house_label = "Insufficient evidence"
                guarded = enforce_editorial(text=executive, record=execution_governance)
                if guarded.get("blocked"):
                    executive = scrub_text(guarded.get("text")) or executive
                    house_label = "Insufficient evidence"
                for line in (committee_gov.get("findings") or [])[:4]:
                    cleaned = scrub_text(line)[:420]
                    if cleaned and cleaned not in why:
                        why.insert(0, cleaned)
                for line in (committee_gov.get("disagreements") or [])[:2]:
                    cleaned = scrub_text(line)[:420]
                    if cleaned and cleaned not in why:
                        why.insert(0, cleaned)
                missing_gov = execution_governance.get("missing_evidence") or []
                if missing_gov:
                    note = scrub_text(
                        "Evidence contract incomplete — missing "
                        + ", ".join(str(m) for m in missing_gov[:6])
                        + "."
                    )[:420]
                    if note and note not in why:
                        why.insert(0, note)
                why = why[:16]
            except Exception:
                pass

        # Framework Execution Policy — mandatory why bullets (execute or report insufficient).
        if isinstance(execution_policy, dict) and (
            execution_policy.get("results") or execution_policy.get("required_frameworks")
        ):
            for hint in (execution_policy.get("ask_agi_hints") or [])[:6]:
                cleaned = scrub_text(hint)[:420]
                if cleaned and cleaned not in why:
                    why.insert(0, cleaned)
            why = why[:16]
            try:
                from institutional_reasoning.execution_policy import enforce_valuation_narrative

                enforced = enforce_valuation_narrative(
                    executive=executive,
                    house_label=house_label,
                    report=execution_policy,
                )
                if enforced.get("rewritten"):
                    executive = scrub_text(enforced.get("executive")) or executive
                    house_label = enforced.get("house_label") or house_label
            except Exception:
                pass

        # Company Monitor — what changed since prior period
        if isinstance(company_monitor, dict) and company_monitor.get("enabled"):
            for hint in (company_monitor.get("ask_agi_hints") or [])[:5]:
                if hint and hint not in why:
                    why.insert(0, scrub_text(hint)[:400])
            wc = company_monitor.get("what_changed") or {}
            if wc.get("change_count"):
                why.insert(
                    0,
                    scrub_text(
                        f"Company Monitor: {wc.get('change_count')} change(s) since prior snapshot "
                        f"(max significance: {wc.get('max_significance')})."
                    )[:300],
                )
            why = why[:12]

        # Investment Office — desk attention / research queue context
        if isinstance(investment_office_pkg, dict) and investment_office_pkg.get("enabled"):
            for hint in (investment_office_pkg.get("ask_agi_hints") or [])[:4]:
                if hint and hint not in why:
                    why.insert(0, scrub_text(hint)[:400])
            why = why[:12]

        # LEO hints — live evidence contribution before recommendation
        if isinstance(live_evidence, dict) and live_evidence.get("enabled"):
            for hint in (live_evidence.get("answer_hints") or [])[:3]:
                if hint and hint not in why:
                    why.insert(0, scrub_text(hint)[:300])
            why = why[:12]

        # AGIB Intelligence Layer V2 — living dossier/thesis/forecast (soft; no FAA/FRE/CAE redesign)
        try:
            if slim:
                intelligence_layer = {}
                degradation["intelligence_layer"] = "skipped_slim"
            elif self.ail is not None and hasattr(self.ail, "package_for_ask_agi"):
                intelligence_layer, ail_to = call_with_timeout(
                    self.ail.package_for_ask_agi,
                    q,
                    ticker=detected_ticker,
                    timeout_sec=4.0,
                    default={},
                )
                intelligence_layer = intelligence_layer or {}
                if ail_to:
                    degradation["intelligence_layer"] = "timeout_cached"
                else:
                    degradation["intelligence_layer"] = "cached_snapshot"
                if intelligence_layer.get("enabled") and intelligence_layer.get("ticker"):
                    detected_ticker = detected_ticker or str(intelligence_layer.get("ticker")).upper()
                    for hint in (intelligence_layer.get("ask_agi_hints") or [])[:4]:
                        cleaned = scrub_text(hint)
                        if cleaned and cleaned not in why:
                            why.insert(0, cleaned[:300])
                    why = why[:14]
            else:
                intelligence_layer = {}
        except Exception:
            intelligence_layer = {}

        # Ask AGI Intelligence Construction V2 — consume validated CID/CA/DVC/LEO/etc into one brief
        try:
            from intelligence_construction.production import package_for_ask_agi as ic_package

            intelligence_construction = (
                ic_package(
                    q,
                    ticker=detected_ticker,
                    cid=company_dossier if isinstance(company_dossier, dict) else None,
                    company_analysis=company_analysis if isinstance(company_analysis, dict) else None,
                    company_monitor=company_monitor if isinstance(company_monitor, dict) else None,
                    finance_academy=finance_academy if isinstance(finance_academy, dict) else None,
                    knowledge_foundation={"hits": kf_hits} if kf_hits else (knowledge_corpus if isinstance(knowledge_corpus, dict) else None),
                    live_evidence=live_evidence if isinstance(live_evidence, dict) else None,
                    data_validation=data_validation if isinstance(data_validation, dict) else None,
                    evidence_completion=evidence_completion if isinstance(evidence_completion, dict) else None,
                    irp=irp_dump if isinstance(irp_dump, dict) else None,
                    investment_office=investment_office_pkg if isinstance(investment_office_pkg, dict) else None,
                    sector_intelligence=sector_intelligence if isinstance(sector_intelligence, dict) else None,
                )
                or {}
            )
            if intelligence_construction.get("enabled"):
                enrich = intelligence_construction.get("answer_enrichment") or {}
                for bullet in (enrich.get("why_bullets") or [])[:8]:
                    cleaned = scrub_text(bullet)
                    if cleaned and cleaned not in why:
                        why.insert(0, cleaned[:420])
                if enrich.get("executive_summary"):
                    executive = scrub_text(enrich["executive_summary"]) or executive
                if enrich.get("valuation_perspective") and not thesis:
                    pass
                why = why[:14]
        except Exception:
            intelligence_construction = {}

        # ECP second pass — if still blocked, one more soft completion before final gate
        try:
            from app.core.config import get_settings
            from ecp.production import soft_complete as ecp_soft_complete

            reco_gate_pre = (sector_intelligence.get("recommendation_gate") or {})
            leo_gate_pre = (live_evidence.get("quality_gate") or {}) if isinstance(live_evidence, dict) else {}
            if (
                not slim
                and bool(getattr(get_settings(), "ecp", True))
                and bool(getattr(get_settings(), "ecp_before_gate", True))
                and (reco_gate_pre.get("blocked") or leo_gate_pre.get("blocked"))
            ):
                pass2, ecp2_to = call_with_timeout(
                    ecp_soft_complete,
                    query=q,
                    ticker=detected_ticker,
                    leo_pkg=live_evidence if isinstance(live_evidence, dict) else {},
                    cid=company_dossier if isinstance(company_dossier, dict) else {},
                    sif_pkg=sector_intelligence if isinstance(sector_intelligence, dict) else {},
                    dvc_pkg=data_validation if isinstance(data_validation, dict) else {},
                    kip=self.kip,
                    kf=self.kf,
                    force=True,
                    timeout_sec=3.0,
                    default={},
                )
                pass2 = pass2 or {}
                if ecp2_to:
                    degradation["evidence_completion_pass2"] = "timeout_cached"
                if pass2.get("leo_delta"):
                    live_evidence = {**live_evidence, **(pass2.get("leo_delta") or {})}
                if pass2.get("cid_delta"):
                    company_dossier = {**company_dossier, **(pass2.get("cid_delta") or {})}
                if pass2.get("sif_delta"):
                    sector_intelligence = {**sector_intelligence, **(pass2.get("sif_delta") or {})}
                if pass2:
                    evidence_completion = {
                        **(evidence_completion or {}),
                        "pass2": {
                            "completed_automatically": pass2.get("completed_automatically"),
                            "still_missing": pass2.get("still_missing"),
                            "gate_blocked_after": pass2.get("gate_blocked_after"),
                            "quality_improvement": pass2.get("quality_improvement"),
                        },
                        "quality_panel": pass2.get("quality_panel")
                        or (evidence_completion or {}).get("quality_panel"),
                        "withheld_explanation": pass2.get("withheld_explanation")
                        or (evidence_completion or {}).get("withheld_explanation"),
                        "ask_agi_hints": list(
                            dict.fromkeys(
                                list((evidence_completion or {}).get("ask_agi_hints") or [])
                                + list(pass2.get("ask_agi_hints") or [])
                            )
                        )[:8],
                    }
                    # Soft refresh Company Analysis + Intelligence Construction after secondary enrichment
                    try:
                        from company_analysis.production import package_for_ask_agi as company_analysis_package

                        refreshed_ca = (
                            company_analysis_package(
                                q,
                                ticker=detected_ticker,
                                cid=company_dossier if isinstance(company_dossier, dict) else None,
                                finance_academy=finance_academy if isinstance(finance_academy, dict) else None,
                                sif_pkg=sector_intelligence if isinstance(sector_intelligence, dict) else None,
                                leo_pkg=live_evidence if isinstance(live_evidence, dict) else None,
                                dvc_pkg=data_validation if isinstance(data_validation, dict) else None,
                                valuation_pack=valuation if isinstance(valuation, dict) else None,
                                forecast_learning=forecast_learning if isinstance(forecast_learning, dict) else None,
                                market_events=market_events if isinstance(market_events, dict) else None,
                            )
                            or {}
                        )
                        if refreshed_ca.get("enabled") or refreshed_ca.get("ticker"):
                            company_analysis = refreshed_ca
                    except Exception:
                        pass
                    try:
                        from intelligence_construction.production import package_for_ask_agi as ic_package

                        refreshed_ic = (
                            ic_package(
                                q,
                                ticker=detected_ticker,
                                cid=company_dossier if isinstance(company_dossier, dict) else None,
                                company_analysis=company_analysis if isinstance(company_analysis, dict) else None,
                                company_monitor=company_monitor if isinstance(company_monitor, dict) else None,
                                finance_academy=finance_academy if isinstance(finance_academy, dict) else None,
                                knowledge_foundation={"hits": kf_hits}
                                if kf_hits
                                else (knowledge_corpus if isinstance(knowledge_corpus, dict) else None),
                                live_evidence=live_evidence if isinstance(live_evidence, dict) else None,
                                data_validation=data_validation if isinstance(data_validation, dict) else None,
                                evidence_completion=evidence_completion if isinstance(evidence_completion, dict) else None,
                                irp=irp_dump if isinstance(irp_dump, dict) else None,
                                investment_office=investment_office_pkg if isinstance(investment_office_pkg, dict) else None,
                                sector_intelligence=sector_intelligence if isinstance(sector_intelligence, dict) else None,
                            )
                            or {}
                        )
                        if refreshed_ic.get("enabled"):
                            intelligence_construction = refreshed_ic
                            enrich2 = refreshed_ic.get("answer_enrichment") or {}
                            if enrich2.get("executive_summary"):
                                executive = scrub_text(enrich2["executive_summary"]) or executive
                            for bullet in (enrich2.get("why_bullets") or [])[:6]:
                                cleaned = scrub_text(bullet)
                                if cleaned and cleaned not in why:
                                    why.insert(0, cleaned[:420])
                            why = why[:14]
                    except Exception:
                        pass
        except Exception:
            pass

        # Evidence gate — SIF + LEO still control Buy/Hold/Sell.
        # Answer Construction V3: do NOT replace the research briefing with a withheld checklist.
        reco_gate = (sector_intelligence.get("recommendation_gate") or {})
        leo_gate = (live_evidence.get("quality_gate") or {}) if isinstance(live_evidence, dict) else {}

        # AGIB Investment Decision Engine — multi-layer stack before any buy/sell conclusion
        try:
            from decision_engine.production import package_for_ask_agi as ide_package

            aws_macro_pkg = dump(soft(self.aws.macro)) if self.aws else {}
            decision_engine = (
                ide_package(
                    q,
                    ticker=detected_ticker,
                    cid=company_dossier if isinstance(company_dossier, dict) else None,
                    company_analysis=company_analysis if isinstance(company_analysis, dict) else None,
                    company_monitor=company_monitor if isinstance(company_monitor, dict) else None,
                    sector_intelligence=sector_intelligence if isinstance(sector_intelligence, dict) else None,
                    live_evidence=live_evidence if isinstance(live_evidence, dict) else None,
                    evidence_completion=evidence_completion if isinstance(evidence_completion, dict) else None,
                    valuation_pack=valuation if isinstance(valuation, dict) else None,
                    market_events=market_events if isinstance(market_events, dict) else None,
                    investment_intelligence=investment_intelligence
                    if isinstance(investment_intelligence, dict)
                    else None,
                    institutional_briefing=(irp_dump or {}).get("institutional_briefing")
                    if isinstance(irp_dump, dict)
                    else None,
                    intelligence_construction=intelligence_construction
                    if isinstance(intelligence_construction, dict)
                    else None,
                    irp=irp_dump if isinstance(irp_dump, dict) else None,
                    aws_macro=aws_macro_pkg if isinstance(aws_macro_pkg, dict) else None,
                    gate_blocked=bool(reco_gate.get("blocked") or leo_gate.get("blocked")),
                )
                or {}
            )
            if decision_engine.get("active"):
                # Decision Engine owns the scorecard — not the executive lead or duplicated why bullets.
                # Why bullets / layer essays stay out of the lead narrative to avoid section duplication.
                pass
        except Exception:
            decision_engine = {}

        answer_meta_institutional: dict[str, Any] = {}
        intent_resolution_pack: dict[str, Any] = {}
        try:
            intent_resolution_pack = (ask_pipeline_runtime or {}).get("intent_resolution") or {}
            if not intent_resolution_pack:
                from ask_pipeline.intent_resolution import resolve_intent

                intent_resolution_pack = resolve_intent(q) or {}
        except Exception:
            intent_resolution_pack = {}
        _playbook_selection = (ask_pipeline_runtime or {}).get("playbook_selection") or {}
        try:
            from answer_construction.production import package_for_ask_agi as ac_package

            answer_construction = (
                ac_package(
                    query=q,
                    ticker=detected_ticker,
                    intent_resolution=intent_resolution_pack if isinstance(intent_resolution_pack, dict) else None,
                    playbook_selection=_playbook_selection if isinstance(_playbook_selection, dict) else None,
                    executive=executive,
                    thesis=thesis,
                    house_label=house_label,
                    bull=bull,
                    bear=bear,
                    risks=risks,
                    catalysts=catalysts,
                    why=why,
                    intelligence_construction=intelligence_construction
                    if isinstance(intelligence_construction, dict)
                    else None,
                    company_analysis=company_analysis if isinstance(company_analysis, dict) else None,
                    company_dossier=company_dossier if isinstance(company_dossier, dict) else None,
                    evidence_completion=evidence_completion if isinstance(evidence_completion, dict) else None,
                    live_evidence=live_evidence if isinstance(live_evidence, dict) else None,
                    sector_intelligence=sector_intelligence if isinstance(sector_intelligence, dict) else None,
                    institutional_briefing=(irp_dump or {}).get("institutional_briefing")
                    if isinstance(irp_dump, dict)
                    else None,
                    decision_engine=decision_engine if isinstance(decision_engine, dict) else None,
                    company_monitor=company_monitor if isinstance(company_monitor, dict) else None,
                    finance_academy=finance_academy if isinstance(finance_academy, dict) else None,
                    valuation=valuation if isinstance(valuation, dict) else None,
                    intelligence_layer=intelligence_layer if isinstance(intelligence_layer, dict) else None,
                    irp=irp_dump if isinstance(irp_dump, dict) else None,
                    data_validation=data_validation if isinstance(data_validation, dict) else None,
                    knowledge_foundation={"hits": kf_hits} if kf_hits else None,
                    reco_gate=reco_gate,
                    leo_gate=leo_gate,
                    execution_policy=execution_policy if isinstance(execution_policy, dict) else None,
                )
                or {}
            )
            if answer_construction.get("enabled"):
                executive = answer_construction.get("executive") or executive
                thesis = answer_construction.get("thesis") or thesis
                house_label = answer_construction.get("house_label") or house_label
                bull = list(answer_construction.get("bull") or bull)
                bear = list(answer_construction.get("bear") or bear)
                risks = list(answer_construction.get("risks") or risks)
                catalysts = list(answer_construction.get("catalysts") or catalysts)
                why = list(answer_construction.get("why") or why)
                if answer_construction.get("institutional_answer"):
                    answer_meta_institutional = answer_construction.get("institutional_answer")
                else:
                    answer_meta_institutional = {}
                # Soft-apply Response Constitution confidence when Ask pack lacks a score.
                rc = answer_construction.get("response_constitution")
                if isinstance(rc, dict) and rc.get("enabled") and conf is None:
                    score = (rc.get("confidence") or {}).get("score")
                    if score is not None:
                        try:
                            conf = float(score)
                        except (TypeError, ValueError):
                            pass
            else:
                answer_meta_institutional = {}
        except Exception:
            answer_construction = {}
            answer_meta_institutional = {}
            # Legacy soft fallback — still avoid wiping the brief when gated
            if reco_gate.get("blocked") or leo_gate.get("blocked"):
                if house_label and "insufficient" in str(house_label).lower():
                    house_label = "Neutral"

        timeline: list[dict[str, Any]] = []
        if detected_ticker and self.kip:
            timeline = scrub(_timeline_events(dump(soft(self.kip.timeline, detected_ticker))))[:20]

        freshness = {
            "score": evidence.get("freshness_score") if isinstance(evidence, dict) else None,
            "last_updated": evidence.get("last_updated") if isinstance(evidence, dict) else None,
            "knowledge_version": evidence.get("knowledge_version") if isinstance(evidence, dict) else None,
        }
        last_updated = freshness.get("last_updated")
        if isinstance(house, dict):
            last_updated = last_updated or house.get("updated_at") or house.get("as_of")

        # Follow-ups assembled after IAX graph/evidence enrichment below.
        followups: list[str] = []

        _rc = (
            answer_construction.get("response_constitution")
            if isinstance(answer_construction, dict)
            else None
        )
        answer = {
            "policy": "evidence_pack_not_direct_advice",
            "summary": executive,
            "house_view_label": house_label,
            "executive_summary": executive,
            "investment_thesis": scrub_text(thesis) if thesis else None,
            "bull_case": bull,
            "bear_case": bear,
            "key_risks": risks,
            "key_catalysts": catalysts,
            "why": why,
            "institutional_answer": answer_meta_institutional or None,
            "voice": "AGIB Institutional Intelligence",
            "bottom_line": (
                (answer_construction or {}).get("bottom_line")
                if isinstance(answer_construction, dict)
                else None
            )
            or ((_rc or {}).get("bottom_line") if isinstance(_rc, dict) else None),
            "confidence_explanation": (
                (answer_construction or {}).get("confidence_explanation")
                if isinstance(answer_construction, dict)
                else None
            )
            or (
                ((_rc or {}).get("confidence") or {}).get("explanation")
                if isinstance(_rc, dict)
                else None
            ),
            "response_constitution": _rc if isinstance(_rc, dict) else None,
            "ask_intelligence_constitution": (
                (answer_construction or {}).get("ask_intelligence_constitution")
                if isinstance(answer_construction, dict)
                else None
            ),
            "research_conclusion": (
                (answer_construction or {}).get("research_conclusion")
                if isinstance(answer_construction, dict)
                else None
            ),
            "questions_before_you_decide": (
                (answer_construction or {}).get("questions_before_you_decide")
                if isinstance(answer_construction, dict)
                else None
            ),
            "institutional_playbook_framework": (
                (answer_construction or {}).get("institutional_playbook_framework")
                if isinstance(answer_construction, dict)
                else None
            ),
            "research_journey": (
                (answer_construction or {}).get("research_journey")
                if isinstance(answer_construction, dict)
                else None
            ),
            "research_journey_state": (
                (answer_construction or {}).get("research_journey_state")
                if isinstance(answer_construction, dict)
                else None
            ),
            "suggested_next_research": (
                (answer_construction or {}).get("suggested_next_research")
                if isinstance(answer_construction, dict)
                else None
            ),
            "playbook_validation": (
                (answer_construction or {}).get("playbook_validation")
                if isinstance(answer_construction, dict)
                else None
            ),
            "research_workflow_framework": (
                (answer_construction or {}).get("research_workflow_framework")
                if isinstance(answer_construction, dict)
                else None
            ),
            "decision_objective": (
                (answer_construction or {}).get("decision_objective")
                if isinstance(answer_construction, dict)
                else None
            ),
            "research_status": (
                (answer_construction or {}).get("research_status")
                if isinstance(answer_construction, dict)
                else None
            ),
            "research_session": (
                (answer_construction or {}).get("research_session")
                if isinstance(answer_construction, dict)
                else None
            ),
            "research_session_state": (
                (answer_construction or {}).get("research_session_state")
                if isinstance(answer_construction, dict)
                else None
            ),
            "next_best_research_question": (
                (answer_construction or {}).get("next_best_research_question")
                if isinstance(answer_construction, dict)
                else None
            ),
            "workflow_validation": (
                (answer_construction or {}).get("workflow_validation")
                if isinstance(answer_construction, dict)
                else None
            ),
            "intent_resolution": intent_resolution_pack if isinstance(intent_resolution_pack, dict) else None,
            "answer_structure": (
                (answer_construction or {}).get("answer_structure")
                if isinstance(answer_construction, dict)
                else None
            )
            or "response_constitution_v1",
        }

        recommendations = {
            "related_research": scrub(articles)[:6],
            "related_companies": related[:6],
            "related_themes": related_themes[:6],
            "related_articles": scrub(articles)[:6],
            "related_questions": followups[:6],
        }

        # --- IAX enrichment ---
        company_ws = dump(soft(self.aws.company, detected_ticker)) if self.aws and detected_ticker else None
        company_ws = company_ws or {}
        prior_house = None
        if isinstance(house, dict):
            hist = house.get("historical_views") or house.get("history") or []
            if isinstance(hist, list) and hist:
                prior_house = scrub(hist[0] if isinstance(hist[0], dict) else None)
        if prior_house is None and detected_ticker and self.aip:
            evo = soft(self.aip.house_view_evolution, detected_ticker)
            evo_d = dump(evo) if evo is not None else None
            points = (evo_d or {}).get("points") or []
            if len(points) >= 2:
                prior_house = {
                    "label": points[-2].get("label"),
                    "current_view": points[-2].get("label"),
                    "confidence": points[-2].get("confidence"),
                }

        hv_card = house_view_card(house if isinstance(house, dict) else None, conf)
        changed = whats_changed(
            house=house if isinstance(house, dict) else None,
            prior_house=prior_house if isinstance(prior_house, dict) else None,
            conf=float(conf) if conf is not None else None,
            prior_conf=float(prior_house["confidence"])
            if isinstance(prior_house, dict) and prior_house.get("confidence") is not None
            else None,
            thesis=thesis,
        )

        broker_docs = evidence_items(
            _as_docs((company_ws.get("broker_research") or [])[:10]),
            default_type="broker",
        )
        filing_docs = evidence_items(
            [
                d
                for d in _as_docs(company_ws.get("agi_articles") or [])
                if "filing" in str(d.get("document_type") or d.get("title") or "").lower()
            ],
            default_type="filing",
        )
        earning_docs = evidence_items(
            [
                d
                for d in _as_docs(company_ws.get("agi_articles") or [])
                if "earn" in str(d.get("document_type") or d.get("title") or "").lower()
            ],
            default_type="earnings",
        )
        support_ev = evidence_items(scrub(supporting)[:12], default_type="agi_research")
        conflict_ev = evidence_items(
            conflicting if isinstance(conflicting, list) else [],
            default_type="conflict",
        )
        if not support_ev:
            support_ev = evidence_items(scrub(articles)[:8], default_type="agi_research")

        preds = []
        if detected_ticker and self.kip:
            for p in soft(self.kip.predictions, detected_ticker, default=[]) or []:
                d = dump(p)
                if d:
                    preds.append(scrub(d))

        graph_raw = company_ws.get("knowledge_graph")
        if graph_raw is None and detected_ticker and self.kip:
            graph_raw = dump(soft(self.kip.graph, detected_ticker))
        kg = knowledge_graph_view(graph_raw if isinstance(graph_raw, dict) else None, detected_ticker)

        if isinstance(irp_dump, dict) and irp_dump.get("follow_ups"):
            followups = [str(x) for x in irp_dump.get("follow_ups") or [] if x][:8]
        else:
            followups = follow_up_questions(
                question=q,
                intent=(irp_dump or {}).get("intent") or (client or {}).get("intent"),
                related_companies=related,
                related_themes=related_themes,
                house_label=str(house_label) if house_label else None,
                risks=risks,
                catalysts=catalysts,
                knowledge_graph=kg,
                recent_research_titles=[
                    str(a.get("title"))
                    for a in (articles or [])[:4]
                    if isinstance(a, dict) and a.get("title")
                ],
            )
        _nbrq = (
            (answer_construction or {}).get("next_best_research_question")
            if isinstance(answer_construction, dict)
            else None
        )
        _next_research = (
            (answer_construction or {}).get("suggested_next_research")
            if isinstance(answer_construction, dict)
            else None
        )
        if isinstance(_nbrq, dict) and _nbrq.get("question"):
            followups = [str(_nbrq["question"])] + [x for x in followups if x != _nbrq["question"]]
        if isinstance(_next_research, list) and _next_research:
            followups = [str(x) for x in _next_research if x] + [x for x in followups if x not in _next_research]
        recommendations["related_questions"] = followups[:6]

        timeline_enriched = enrich_timeline(timeline if isinstance(timeline, list) else [])
        # merge news into timeline
        for n in (news or [])[:8]:
            if isinstance(n, dict):
                timeline_enriched.append(
                    {
                        "as_of": n.get("date") or n.get("published_at"),
                        "type": "news",
                        "title": scrub_text(n.get("title")),
                        "summary": scrub_text(n.get("snippet")),
                        "source": "knowledge",
                    }
                )
        timeline_enriched = enrich_timeline(timeline_enriched)

        mi = market_intelligence_summary(company_ws)
        chart_subject = detected_ticker
        if not chart_subject and isinstance(irp_entities, dict):
            chart_subject = irp_entities.get("sector_key") or irp_entities.get("sector_label")
        charts = build_charts(ticker=chart_subject, predictions=preds, timeline=timeline_enriched)
        ideas = related_ideas(
            related_companies=related,
            related_sectors=related_sectors,
            related_themes=related_themes,
            stance=hv_card.get("stance"),
        )

        port_ctx: dict[str, Any] = {}
        if self.aws:
            port = dump(soft(self.aws.portfolio)) or {}
            weight = company_ws.get("portfolio_weight")
            port_ctx = {
                "current_exposure": weight,
                "sector_allocation": scrub(port.get("sector_exposure") or {}),
                "theme_allocation": related_themes[:6],
                "position_history": scrub(port.get("historical_portfolio") or [])[:5],
                "note": "Model portfolio context — not a recommendation to trade.",
            }

        regime_label = None
        macro = dump(soft(self.aws.macro)) if self.aws else None
        if isinstance(macro, dict):
            regime_label = pick_label(macro.get("e01") or macro.get("market_regime"), "regime", "label")

        freshness_score = freshness.get("score")
        if isinstance(freshness_score, (int, float)):
            freshness_indicator = (
                "fresh" if freshness_score >= 0.7 else "aging" if freshness_score >= 0.4 else "stale"
            )
        else:
            freshness_indicator = "Current"

        briefing = (irp_dump or {}).get("institutional_briefing") if isinstance(irp_dump, dict) else {}
        if not isinstance(briefing, dict):
            briefing = {}
        # Soft-merge Intelligence Construction V2 interpretive sections into briefing
        if isinstance(intelligence_construction, dict) and intelligence_construction.get("enabled"):
            enrich = intelligence_construction.get("answer_enrichment") or {}
            sections = intelligence_construction.get("sections") or {}
            briefing = {
                **briefing,
                "executive_summary": enrich.get("executive_summary") or briefing.get("executive_summary"),
                "current_outlook": enrich.get("current_outlook") or briefing.get("current_outlook"),
                "valuation_perspective": enrich.get("valuation_perspective")
                or briefing.get("valuation_perspective"),
                "key_drivers": list(enrich.get("key_drivers") or briefing.get("key_drivers") or [])[:8],
                "market_performance": (sections.get("market_performance") or {}).get("narrative"),
                "financial_intelligence": (sections.get("financial_intelligence") or {}).get("narrative"),
                "ownership": (sections.get("ownership") or {}).get("narrative"),
                "intelligence_construction_version": intelligence_construction.get("version"),
            }
            if enrich.get("executive_summary"):
                # Prefer ACV3 executive when it already replaced a gate-failure summary
                from answer_construction.knowledge_gaps import looks_like_gate_failure_summary as _gate_fail

                candidate = scrub_text(enrich["executive_summary"])
                if candidate and not _gate_fail(candidate):
                    if not executive or _gate_fail(executive):
                        executive = candidate
                    elif not answer_construction.get("enabled"):
                        executive = candidate
                answer["executive_summary"] = executive
                answer["summary"] = executive
            if enrich.get("valuation_perspective"):
                current_thesis_val = scrub_text(enrich["valuation_perspective"])
                if current_thesis_val:
                    briefing["valuation_perspective"] = current_thesis_val

        # Answer Construction V3 — keep IRP gate-failure outlook out of the lead briefing
        if isinstance(answer_construction, dict) and answer_construction.get("enabled"):
            from answer_construction.knowledge_gaps import looks_like_gate_failure_summary as _gate_fail

            if answer_construction.get("executive"):
                executive = scrub_text(answer_construction["executive"]) or executive
                answer["executive_summary"] = executive
                answer["summary"] = executive
                briefing["executive_summary"] = executive
            if _gate_fail(briefing.get("current_outlook")):
                briefing["current_outlook"] = answer_construction.get("thesis") or executive
            reco_status = answer_construction.get("recommendation_status") or {}
            if reco_status:
                briefing["recommendation_status"] = reco_status
                briefing["knowledge_gaps"] = reco_status.get("knowledge_gaps") or answer_construction.get(
                    "knowledge_gaps"
                )

        # AGIB v3.4 Track D — Institutional Communication Engine soft-wire.
        # Framework/playbook metadata must NOT replace an evidence-backed executive.
        _ice_view = (ask_pipeline_runtime or {}).get("communication") or {}
        if isinstance(_ice_view, dict) and _ice_view.get("executive_summary"):
            ice_exec = scrub_text(_ice_view.get("executive_summary"))
            ice_is_meta = looks_like_framework_meta_executive(ice_exec or "")
            existing_is_meta = looks_like_framework_meta_executive(executive or "")
            if ice_exec and not ice_is_meta:
                executive = ice_exec
                answer["executive_summary"] = executive
                answer["summary"] = executive
                answer["source"] = "institutional_communication"
                briefing["executive_summary"] = executive
                ask_orchestration["executive_source"] = "ice"
            elif ice_exec and ice_is_meta and (not executive or existing_is_meta):
                # Prefer answer-construction / prior executive over framework scaffolding.
                ac_exec = None
                if isinstance(answer_construction, dict):
                    ac_exec = scrub_text(answer_construction.get("executive"))
                if ac_exec and not looks_like_framework_meta_executive(ac_exec):
                    executive = ac_exec
                    ask_orchestration["executive_source"] = "answer_construction_over_ice_meta"
                else:
                    ask_orchestration["executive_source"] = "ice_meta_suppressed"
                answer["executive_summary"] = executive
                answer["summary"] = executive
                briefing["executive_summary"] = executive
            answer["communication_template"] = _ice_view.get("template")
            answer["communication_sections"] = _ice_view.get("sections")
            if not ice_is_meta:
                answer["source"] = answer.get("source") or "institutional_communication"
            ice_why = _ice_view.get("why") or []
            if isinstance(ice_why, list) and ice_why and not ice_is_meta:
                why = [scrub_text(x) or str(x) for x in ice_why if x][:16]
            answer["institutional_communication"] = {
                "ice_version": _ice_view.get("ice_version"),
                "template": _ice_view.get("template"),
                "framework_visible": _ice_view.get("framework_visible"),
                "playbook_visible": _ice_view.get("playbook_visible"),
                "playbook_id": _ice_view.get("playbook_id"),
                "validation": _ice_view.get("validation"),
                "consumes_institutional_answer": True,
                "llm_used": False,
                "executive_was_framework_meta": ice_is_meta,
            }
            _pb_view = (ask_pipeline_runtime or {}).get("playbook_selection") or {}
            if isinstance(_pb_view, dict) and _pb_view.get("playbook_id"):
                answer["playbook_selection"] = {
                    "playbook_id": _pb_view.get("playbook_id"),
                    "playbook_name": _pb_view.get("playbook_name"),
                    "category": _pb_view.get("category"),
                    "iap_version": _pb_view.get("iap_version"),
                    "procedure": (_pb_view.get("procedure") or {}).get("arrow_text"),
                    "guides_reasoning": True,
                }
            _eg_view = (ask_pipeline_runtime or {}).get("evidence_graph") or {}
            if isinstance(_eg_view, dict) and _eg_view.get("graph_id"):
                answer["evidence_graph"] = {
                    "graph_id": _eg_view.get("graph_id"),
                    "entities": _eg_view.get("entities"),
                    "n_nodes": _eg_view.get("n_nodes"),
                    "domain_coverage_pct": _eg_view.get("domain_coverage_pct"),
                    "chains": (_eg_view.get("chain_bullets") or [])[:6],
                    "ieg_version": _eg_view.get("ieg_version"),
                    "guides_evidence": True,
                }
            _im_view = (ask_pipeline_runtime or {}).get("institutional_memory") or {}
            if isinstance(_im_view, dict) and (
                _im_view.get("have_we_seen_this_before") or _im_view.get("top_memory_ids")
            ):
                answer["institutional_memory"] = {
                    "imai_version": _im_view.get("imai_version"),
                    "have_we_seen_this_before": _im_view.get("have_we_seen_this_before"),
                    "top_memory_ids": _im_view.get("top_memory_ids"),
                    "surface_bullets": (_im_view.get("surface_bullets") or [])[:5],
                    "regimes": _im_view.get("regimes"),
                    "guides_memory": True,
                }
            if isinstance(_ice_view, dict):
                answer["institutional_communication"] = {
                    **(answer.get("institutional_communication") or {}),
                    "evidence_graph_visible": _ice_view.get("evidence_graph_visible"),
                    "evidence_graph_id": _ice_view.get("evidence_graph_id"),
                    "institutional_memory_visible": _ice_view.get("institutional_memory_visible"),
                    "have_we_seen_this_before": _ice_view.get("have_we_seen_this_before"),
                    "top_memory_ids": _ice_view.get("top_memory_ids"),
                }

        neutral_case = list(briefing.get("neutral_case") or [])
        if not neutral_case:
            if hv_card.get("stance") == "Neutral":
                neutral_case = ["Wait for clearer catalysts before increasing conviction."]
            elif risks and catalysts:
                neutral_case = [
                    "Balance catalysts against listed risks; position sizing remains discretionary."
                ]

        current_thesis = {
            "bull_case": bull,
            "bear_case": bear,
            "neutral_case": neutral_case,
            "catalysts": catalysts,
            "risks": risks,
            "valuation": briefing.get("valuation_perspective")
            or ((house or {}).get("valuation") if isinstance(house, dict) else None),
            "time_horizon": hv_card.get("investment_horizon"),
            "summary": scrub_text(thesis) if thesis else None,
        }

        rpanel = research_panel(
            agi=evidence_items(scrub(articles)[:10], default_type="agi_research"),
            broker=broker_docs,
            filings=filing_docs,
            earnings=earning_docs,
            historical=evidence_items(
                _as_docs(company_ws.get("agi_articles") or [])[3:12],
                default_type="agi_research",
            ),
        )

        workspace = {
            "mode": "institutional_answer",
            "four_questions": {
                "view": hv_card.get("stance"),
                "why": why[:3],
                "evidence_count": len(support_ev),
                "explore_next": followups[:4],
            },
        }

        # Final ticker hygiene — drop prose tokens / soft-pack pollution before response.
        alias_final = alias_ticker_from_question(q)
        if alias_final and (not detected_ticker or detected_ticker != alias_final):
            if not ticker or str(ticker).upper() == alias_final:
                if detected_ticker and detected_ticker != alias_final:
                    ask_orchestration["ticker_rejects"].append(
                        {"raw": detected_ticker, "source": "final_alias_override"}
                    )
                detected_ticker = alias_final
                ask_orchestration["ticker_source"] = ask_orchestration.get("ticker_source") or "alias_final"
        safe_final = accept_detected_ticker(
            detected_ticker,
            ere_blocked=ere_research_blocked and detected_ticker not in {ere_ticker, alias_final, (str(ticker).upper() if ticker else None)},
            allow_when_blocked=bool(
                detected_ticker
                and detected_ticker in {ere_ticker, alias_final, (str(ticker).upper() if ticker else None)}
            ),
        )
        if detected_ticker and not safe_final:
            ask_orchestration["ticker_rejects"].append(
                {"raw": detected_ticker, "source": "final_sanitize"}
            )
            detected_ticker = None
        else:
            detected_ticker = safe_final
        # Strip polluted related companies that are not plausible tickers
        related = [
            str(r).upper()
            for r in (related or [])
            if accept_detected_ticker(r) and str(r).upper() != "SUMMARIZE"
        ][:8]
        if detected_ticker and detected_ticker not in related:
            related = [detected_ticker] + [r for r in related if r != detected_ticker]
        # The response UI uses related_companies for entity chips and follow-up
        # context; guarantee that a verified comparison retains both sides.
        if comparison_tickers:
            related = list(dict.fromkeys([*comparison_tickers, *related]))[:8]
        stage_timer.mark("response_assembly")
        _ice_for_trace = (ask_pipeline_runtime or {}).get("communication") or {}
        ask_orchestration["ice_framework_meta_suppressed"] = bool(
            ((answer.get("institutional_communication") or {}) if isinstance(answer, dict) else {}).get(
                "executive_was_framework_meta"
            )
        )
        ask_orchestration = finalize_orchestration(
            ask_orchestration,
            timer=stage_timer,
            question=q,
            detected_ticker=detected_ticker,
            ere_body=ere_body,
            alias_hit=alias_hit,
            kf_hits=kf_hits,
            finance_retrieval=finance_retrieval,
            live_evidence=live_evidence,
            multi_source=multi_source_pack,
            knowledge_corpus=knowledge_corpus,
            open_intelligence=open_intelligence,
            hits=hits,
            articles=articles,
            supporting=supporting,
            evidence_used=evidence_used,
            supporting_research=supporting,
            support_ev=support_ev,
            ask_pipeline_runtime=ask_pipeline_runtime,
            ice_view=_ice_for_trace,
            why=why,
            executive=executive or "",
            intent=(irp_dump or {}).get("intent") or (client or {}).get("intent"),
            fallback=False,
        )
        # Phase-1 observability — evidence / prompt sizes / LLM soft status (no behavior change)
        try:
            _funnel = ask_orchestration.get("funnel") or ask_orchestration.get("evidence") or {}
            _ev_ids = []
            for _e in (evidence_used or [])[:12]:
                if isinstance(_e, dict):
                    _ev_ids.append(str(_e.get("id") or _e.get("title") or _e.get("source") or "")[:80])
            pipeline.set_evidence(
                retrieved=int(_funnel.get("retrieved") or 0),
                used=int(_funnel.get("referenced") or _funnel.get("passed") or len(evidence_used or [])),
                top_ids=[x for x in _ev_ids if x],
                sources=[s.get("name") for s in pipeline.sources if s.get("searched") or s.get("returned")],
            )
            _exec = executive or ""
            _why_join = " ".join(str(x) for x in (why or [])[:12])
            _prompt_chars = len(_exec) + len(_why_join) + len(q)
            _playbook = None
            try:
                _playbook = ((ask_pipeline_runtime or {}).get("playbook_selection") or {}).get("playbook_id")
            except Exception:
                _playbook = None
            pipeline.set_prompt(
                prompt_chars=_prompt_chars,
                estimated_tokens=max(1, _prompt_chars // 4),
                evidence_count=int(_funnel.get("passed") or len(evidence_used or [])),
                system_prompt_version="ask-orchestration-trace-2",
                playbook=_playbook,
            )
            # Soft ICE / IRP path — record whether a generative LLM call was used.
            _llm_used = bool((ask_pipeline_runtime or {}).get("llm_used"))
            _lat = (ask_orchestration.get("latency") or {})
            pipeline.mark(STAGE_LLM_STARTED, status="ok" if _llm_used else "skipped")
            pipeline.set_llm(
                model=((ask_pipeline_runtime or {}).get("model") or ("ice_compose" if _ice_for_trace else "irp_soft")),
                prompt_tokens=pipeline.prompt.get("estimated_tokens"),
                completion_tokens=max(1, len(_exec) // 4) if _exec else 0,
                latency_ms=int(_lat.get("reasoning_ms") or 0),
                finish_reason="stop",
                used=_llm_used or bool(_lat.get("reasoning_ms")),
            )
            if not pipeline.intent:
                _intent_final = (irp_dump or {}).get("intent") or (client or {}).get("intent") or ask_orchestration.get("intent")
                if _intent_final:
                    pipeline.intent = str(_intent_final)
            # Note: pipeline.complete() is deferred until after the Executive Composer
            # rewrites below, so the debug trace / developer console reflect the final
            # user-visible executive rather than a pre-rewrite scaffold snapshot.
        except Exception:
            pass
        try:
            import logging

            logging.getLogger("agi.ui.search").info(
                "ask_orchestration %s", ask_orchestration.get("trace_summary")
            )
        except Exception:
            pass
        degradation["ask_orchestration"] = ask_orchestration
        if isinstance(answer, dict):
            answer["ask_orchestration"] = ask_orchestration

        if briefing.get("executive_summary") and not (
            isinstance(answer_meta_institutional, dict) and answer_meta_institutional.get("enabled")
        ):
            # Never let a late briefing stomp a good executive with framework meta.
            candidate = scrub_text(briefing["executive_summary"])
            if candidate and not looks_like_framework_meta_executive(candidate):
                executive = candidate or executive
            answer["summary"] = executive
            answer["executive_summary"] = executive
            if house_label:
                answer["house_view_label"] = house_label
        elif isinstance(answer_meta_institutional, dict) and answer_meta_institutional.get("enabled"):
            answer["summary"] = executive
            answer["executive_summary"] = executive
            answer["institutional_answer"] = answer_meta_institutional
            answer["policy"] = "agib_institutional_intelligence_concise_recommendation"

        # Executive Composer contract — question → answer → evidence (never planning text).
        try:
            _why_list = why if isinstance(why, list) else []
            _needs_compose = (
                is_planning_scaffold(executive or "")
                or looks_like_framework_meta_executive(executive or "")
                or any(is_planning_scaffold(str(w)) for w in _why_list[:4])
            )
            if _needs_compose:
                composed = compose_executive(
                    q,
                    detected_ticker=detected_ticker,
                    evidence_used=evidence_used if isinstance(evidence_used, list) else [],
                    supporting=supporting if isinstance(supporting, list) else [],
                    packs={
                        "company_analysis": company_analysis if isinstance(company_analysis, dict) else {},
                        "company_dossier": company_dossier if isinstance(company_dossier, dict) else {},
                        "knowledge_bundle": knowledge_bundle if isinstance(knowledge_bundle, dict) else {},
                    },
                    candidates=[
                        executive or "",
                        scrub_text((answer_construction or {}).get("executive"))
                        if isinstance(answer_construction, dict)
                        else "",
                        scrub_text((briefing or {}).get("executive_summary") or ""),
                    ],
                    why=_why_list,
                )
                executive = composed.get("executive") or executive
                if composed.get("why"):
                    why = list(composed["why"])
                answer["summary"] = executive
                answer["executive_summary"] = executive
                answer["why"] = why
                ask_orchestration["executive_source"] = composed.get("source") or "executive_composer"
                ask_orchestration["executive_composer"] = {
                    "replaced_scaffold": bool(composed.get("replaced_scaffold")),
                    "tickers": composed.get("tickers") or [],
                }
                briefing["executive_summary"] = executive
        except Exception:
            # Never fail the desk if composer faults — keep prior executive.
            pass

        irp_meta = {}
        if isinstance(irp_dump, dict) and irp_dump:
            irp_meta = {
                "irp_id": irp_dump.get("irp_id"),
                "version": irp_dump.get("version"),
                "intent": irp_dump.get("intent"),
                "domain": irp_dump.get("domain"),
                "validation": irp_dump.get("validation") or {},
                "research_plan": {
                    "plan_id": (irp_dump.get("research_plan") or {}).get("plan_id"),
                    "steps": [
                        {
                            "order": s.get("order"),
                            "source_class": s.get("source_class"),
                            "query": s.get("query"),
                        }
                        for s in ((irp_dump.get("research_plan") or {}).get("steps") or [])[:10]
                        if isinstance(s, dict)
                    ],
                },
                "rejected_count": len(irp_dump.get("rejected_evidence") or []),
                "answer_policy": irp_dump.get("answer_policy"),
            }
            workspace = {
                **workspace,
                "mode": "institutional_reasoning_pipeline",
                "programme": "Institutional Research",
                "think_before_answer": True,
            }
        if kf_hits:
            workspace = {
                **workspace,
                "knowledge_first": True,
                "knowledge_hits": len(kf_hits),
                "knowledge_corpus": True if knowledge_corpus else False,
                "primary_source_of_truth": "knowledge_objects",
            }

        # IB soft emit — Ask AGI activity becomes a bus event when enabled.
        if self.ib and q:
            try:
                emitted = soft(
                    self.ib.emit_ask_agi_activity,
                    query=q,
                    ticker=detected_ticker,
                    used_cae=used_cae,
                )
                if isinstance(emitted, dict) and emitted.get("event"):
                    intelligence_bus = {
                        "answer_policy": "event_driven_backbone",
                        "emitted": True,
                        "event": emitted.get("event") or {},
                        "deliveries": emitted.get("deliveries") or [],
                        "correlation_id": (emitted.get("event") or {}).get("correlation_id"),
                    }
            except Exception:
                intelligence_bus = {}

        degradation["reasoning"] = "completed"
        desk_status = "degraded" if any(
            str(v).endswith("timeout_cached") or v == "unavailable"
            for v in degradation.values()
        ) else "ok"

        # Executive Composer Rule 6 — final validation + single rewrite from existing evidence.
        try:
            _rej_names = []
            if isinstance(ere_body, dict):
                for r in ere_body.get("rejected_candidates") or ere_body.get("rejected") or []:
                    if isinstance(r, dict):
                        _rej_names.append(str(r.get("ticker") or r.get("raw") or r.get("name") or ""))
                    elif r:
                        _rej_names.append(str(r))
            _rej_names = [x for x in _rej_names if x]
            _cmp_tickers = ask_orchestration.get("comparison_tickers") or []
            _final = finalize_executive(
                q,
                executive or "",
                why=why if isinstance(why, list) else [],
                evidence_used=evidence_used if isinstance(evidence_used, list) else [],
                supporting=supporting if isinstance(supporting, list) else [],
                packs={
                    "company_analysis": company_analysis if isinstance(company_analysis, dict) else {},
                    "company_dossier": company_dossier if isinstance(company_dossier, dict) else {},
                    "knowledge_bundle": knowledge_bundle if isinstance(knowledge_bundle, dict) else {},
                },
                detected_ticker=detected_ticker,
                tickers=_cmp_tickers or ([detected_ticker] if detected_ticker else []),
                rejected=_rej_names,
                is_unknown_stop=False,
                is_comparison=bool(_cmp_tickers) or is_comparison_question(q),
            )
            if _final.get("rewritten"):
                executive = _final["executive"]
                why = _final["why"]
                answer["summary"] = executive
                answer["executive_summary"] = executive
                answer["why"] = why
                ask_orchestration["executive_source"] = "executive_composer_rule6_rewrite"
            ask_orchestration["executive_validation"] = _final.get("validation")
        except Exception:
            pass

        # Phase-1 observability finalize — deferred until after all Executive Composer
        # rewrites so the debug trace / developer console show the final user-visible
        # executive, not a pre-rewrite scaffold snapshot.
        try:
            pipeline.complete(status="success")
            ask_orchestration["request_id"] = pipeline.request_id
            ask_orchestration["pipeline_debug"] = {
                "request_id": pipeline.request_id,
                "intent": pipeline.intent,
                "intent_confidence": pipeline.intent_confidence,
                "entities": pipeline.entities,
                "sources": pipeline.sources,
                "evidence_count": pipeline.evidence_count,
                "evidence_used": pipeline.evidence_used,
                "prompt_tokens": pipeline.prompt.get("estimated_tokens"),
                "completion_tokens": (pipeline.llm or {}).get("completion_tokens"),
                "llm_latency_ms": (pipeline.llm or {}).get("latency_ms"),
                "fallback_used": pipeline.fallback_used,
                "fallback_reason": pipeline.fallback_reason,
                "total_latency_ms": pipeline.elapsed_ms(),
                "latency_breakdown": pipeline.latency_breakdown,
                "status": pipeline.status,
                "executive_excerpt": (executive or "")[:280],
            }
        except Exception:
            pass

        stage_timer.mark("serialization")
        # Refresh latency block with serialization after funnel finalize.
        if isinstance(ask_orchestration, dict):
            try:
                ask_orchestration["latency"] = stage_timer.as_latency_block()
                ask_orchestration["latency_ms"] = stage_timer.as_dict()
                ask_orchestration["trace_summary"] = format_trace_summary(ask_orchestration)
            except Exception:
                pass

        return SearchView(
            meta=UiMeta(
                surface="search",
                sources=[
                    "knowledge",
                    "research_committee",
                    "composite_view",
                    "model_portfolio",
                    "irp",
                    "multi_source",
                    "private_markets",
                    "nifty_research",
                    "valuation_monitor",
                ],
            ),
            question=q,
            status=desk_status,
            degradation=degradation,
            ask_orchestration=ask_orchestration,
            intent=(irp_dump or {}).get("intent") or (client or {}).get("intent"),
            entities={
                "ticker": detected_ticker,
                "companies": related,
                "themes": related_themes,
                "sectors": related_sectors,
                "countries": list((irp_entities or {}).get("countries") or [])
                if isinstance(irp_entities, dict)
                else [],
                "currencies": list((irp_entities or {}).get("currencies") or [])
                if isinstance(irp_entities, dict)
                else [],
                "sector_key": (irp_entities or {}).get("sector_key")
                if isinstance(irp_entities, dict)
                else None,
            },
            answer=answer,
            executive_summary=executive,
            house_view=house if isinstance(house, dict) else None,
            confidence=float(conf) if conf is not None else None,
            investment_thesis=scrub_text(thesis) if thesis else None,
            bull_case=bull,
            bear_case=bear,
            key_risks=risks,
            key_catalysts=catalysts,
            why=why,
            supporting_research=scrub(supporting)[:12],
            latest_articles=scrub(articles),
            latest_news=scrub(news)[:8] or _kip_news(self.kip, q, limit=5),
            conflicting_opinions=conflicting if isinstance(conflicting, list) else [],
            evidence_used=evidence_used if isinstance(evidence_used, list) else [],
            knowledge_timeline=timeline_enriched,
            knowledge_freshness=freshness,
            last_updated=str(last_updated) if last_updated else None,
            related_companies=related,
            related_themes=related_themes,
            related_sectors=related_sectors,
            recommendations=recommendations,
            follow_up_questions=followups,
            hits=hits,
            answer_policy="think_then_answer_institutional"
            if irp_meta
            else "institutional_evidence_pack",
            market_regime=regime_label,
            freshness_indicator=freshness_indicator,
            house_view_card=hv_card,
            whats_changed=changed,
            current_thesis=current_thesis,
            supporting_evidence=support_ev,
            conflicting_evidence=conflict_ev,
            research_panel=rpanel,
            knowledge_graph=kg,
            market_intelligence=mi,
            charts=charts,
            predictions=[p for p in preds if p][:12],
            related_ideas=ideas,
            portfolio_context=port_ctx,
            workspace=workspace,
            irp=scrub(irp_meta) or {},
            knowledge_foundation={
                "answer_policy": "knowledge_objects_before_documents",
                "hits": scrub(kf_hits)[:8],
                "count": len(kf_hits),
            },
            multi_source=scrub(multi_source_pack) if multi_source_pack else {},
            knowledge_bundle=scrub(knowledge_bundle) if knowledge_bundle else {},
            knowledge_corpus=scrub(knowledge_corpus)
            if knowledge_corpus
            else {
                "answer_policy": "knowledge_corpus_before_documents",
                "hits": scrub(kf_hits)[:8],
                "count": len(kf_hits),
                "primary_source_of_truth": "knowledge_objects",
            },
            open_intelligence=scrub(open_intelligence) if open_intelligence else {},
            finance_retrieval=scrub(finance_retrieval)
            if finance_retrieval
            else {
                "answer_policy": "authoritative_evidence_before_reasoning",
                "does_not_answer": True,
                "guidance": {
                    "use_retrieved_evidence_first": True,
                    "prefer_tier1_sources": True,
                    "never_hallucinate_without_provenance": True,
                },
            },
            evidence_verification=scrub(evidence_verification)
            if evidence_verification
            else {
                "answer_policy": "verified_evidence_before_raw_facts",
                "guidance": {
                    "use_highest_confidence_first": True,
                    "avoid_hallucinated_certainty": True,
                },
            },
            investment_intelligence=scrub(investment_intelligence)
            if investment_intelligence
            else {
                "answer_policy": "investment_intelligence_before_reasoning",
                "guidance": {
                    "use_structured_intelligence_first": True,
                    "trace_to_eve_evidence": True,
                    "preserve_uncertainty": True,
                    "never_hallucinate": True,
                },
            },
            forecast_learning=scrub(forecast_learning)
            if forecast_learning
            else {
                "answer_policy": "forecast_history_and_calibration_before_reasoning",
                "guidance": {
                    "use_forecast_history_first": True,
                    "reduce_certainty_if_miscalibrated": False,
                    "never_forget_predictions": True,
                },
            },
            research_intelligence=scrub(research_intelligence) if research_intelligence else {},
            semantic_research=scrub(semantic_research) if semantic_research else {},
            market_events=scrub(market_events)
            if market_events
            else {
                "answer_policy": "what_changed_before_reasoning",
                "guidance": {
                    "always_ask_what_changed": True,
                    "use_event_context_first": True,
                    "immutable_events": True,
                },
            },
            context_assembly=scrub(context_assembly)
            if context_assembly
            else {
                "answer_policy": "unified_context_before_reasoning",
                "guidance": {
                    "single_orchestration_call": False,
                    "fallback_multi_engine": True,
                },
            },
            intelligence_bus=scrub(intelligence_bus)
            if intelligence_bus
            else {
                "answer_policy": "event_driven_backbone",
                "guidance": {
                    "publish_subscribe": True,
                    "fallback_when_disabled": True,
                },
            },
            valuation=scrub(valuation)
            if valuation
            else {
                "answer_policy": "valuation_before_reasoning",
                "guidance": {
                    "use_intrinsic_value_first": True,
                    "never_execute_trades": True,
                },
            },
            finance_academy=scrub(finance_academy) if finance_academy else {},
            academy_books=scrub(academy_books) if academy_books else {},
            live_evidence=scrub(live_evidence) if live_evidence else {},
            company_dossier=scrub(company_dossier) if company_dossier else {},
            institutional_knowledge=scrub(institutional_knowledge) if institutional_knowledge else {},
            data_validation=scrub(data_validation) if data_validation else {},
            evidence_completion=scrub(evidence_completion) if evidence_completion else {},
            company_analysis=scrub(company_analysis) if company_analysis else {},
            company_monitor=scrub(company_monitor) if company_monitor else {},
            intelligence_construction=scrub(intelligence_construction) if intelligence_construction else {},
            answer_construction=scrub(answer_construction) if answer_construction else {},
            decision_engine=scrub(decision_engine) if decision_engine else {},
            intelligence_layer=scrub(intelligence_layer) if intelligence_layer else {},
            investment_office_os=scrub(
                (ask_pipeline_runtime or {}).get("investment_office_os")
                or {
                    "release": "AGI v4.0",
                    "investment_thesis": ((ask_pipeline_runtime or {}).get("context") or {}).get(
                        "investment_thesis"
                    )
                    or {},
                    "decision_office": ((ask_pipeline_runtime or {}).get("context") or {}).get(
                        "decision_office"
                    )
                    or {},
                    "portfolio_office": ((ask_pipeline_runtime or {}).get("context") or {}).get(
                        "portfolio_office"
                    )
                    or {},
                    "monitoring_office": ((ask_pipeline_runtime or {}).get("context") or {}).get(
                        "monitoring_office"
                    )
                    or {},
                    "learning_office": ((ask_pipeline_runtime or {}).get("context") or {}).get(
                        "learning_office"
                    )
                    or {},
                    "positions": False,
                    "orders": False,
                    "execution": False,
                }
            )
            or {},
            institutional_analysts=scrub(
                (answer_construction or {}).get("institutional_analysts")
                if isinstance(answer_construction, dict)
                else {}
            )
            or {},
            institutional_briefing=scrub(briefing) or {},
            institutional_stack=scrub(
                (answer_construction or {}).get("institutional_stack")
                if isinstance(answer_construction, dict)
                else {}
            )
            or scrub(
                ((answer_construction or {}).get("institutional_analysts") or {}).get(
                    "institutional_stack"
                )
                if isinstance(answer_construction, dict)
                else {}
            )
            or {},
            # Prefer live SIF/Ask-AGI sector pack; fall back to IRP sector pack
            sector_intelligence=scrub(sector_intelligence)
            if sector_intelligence
            else (
                scrub((irp_dump or {}).get("sector_intelligence") or {})
                if isinstance(irp_dump, dict)
                else {}
            ),
            company_intelligence=scrub((irp_dump or {}).get("company_intelligence") or {})
            if isinstance(irp_dump, dict)
            else {},
            current_outlook=scrub_text(briefing.get("current_outlook")) if briefing else None,
            key_drivers=[str(x) for x in (briefing.get("key_drivers") or [])][:8],
            valuation_perspective=scrub_text(briefing.get("valuation_perspective"))
            if briefing
            else None,
            macro_drivers=[str(x) for x in (briefing.get("macro_drivers") or [])][:8],
            sector_drivers=[str(x) for x in (briefing.get("sector_drivers") or [])][:8],
            company_leaders=[str(x) for x in (briefing.get("company_leaders") or [])][:10],
            historical_comparison=scrub_text(briefing.get("historical_comparison"))
            if briefing
            else None,
            research_ontology=scrub(research_ontology) if research_ontology else {},
            entity_resolution=scrub(entity_resolution) if entity_resolution else {},
            market_indices=scrub(market_indices) if market_indices else {},
            research_objective=scrub(research_objective) if research_objective else {},
            context_intelligence=scrub(context_intelligence) if context_intelligence else {},
            analyst_router=scrub(analyst_router) if analyst_router else {},
            layer_router=scrub(layer_router) if layer_router else {},
            acquisition_planner=scrub(acquisition_planner) if acquisition_planner else {},
            research_blueprint=scrub(research_blueprint) if research_blueprint else {},
            validation_engine=scrub(validation_engine) if validation_engine else {},
            research_execution=scrub(research_execution) if research_execution else {},
            hypothesis_engine=scrub(hypothesis_engine) if hypothesis_engine else {},
            research_questions=scrub(research_questions) if research_questions else {},
            hypothesis_testing=scrub(hypothesis_testing) if hypothesis_testing else {},
            belief_engine=scrub(belief_engine) if belief_engine else {},
            thesis_engine=scrub(thesis_engine) if thesis_engine else {},
            debate_engine=scrub(debate_engine) if debate_engine else {},
            decision_readiness=scrub(decision_readiness) if decision_readiness else {},
            reasoning_audit=scrub(reasoning_audit) if reasoning_audit else {},
            execution_policy=scrub(execution_policy) if execution_policy else {},
            execution_governance=scrub(execution_governance) if execution_governance else {},
        )

    def timeline(self, entity: str) -> TimelineView:
        self._require()
        ent = (entity or "").strip()
        events: list[dict[str, Any]] = []
        preds: list[dict[str, Any]] = []
        if self.kip and ent:
            events = enrich_timeline(_timeline_events(dump(soft(self.kip.timeline, ent.upper()))))
            for p in soft(self.kip.predictions, ent.upper(), default=[]) or []:
                d = dump(p)
                if d:
                    preds.append(scrub(d))
            # soft-add news
            for n in _kip_news(self.kip, ent, limit=8):
                events.append(
                    {
                        "as_of": n.get("date"),
                        "type": "news",
                        "title": n.get("title"),
                        "summary": n.get("snippet"),
                        "source": "knowledge",
                    }
                )
            events = enrich_timeline(events)
        return TimelineView(
            meta=UiMeta(surface="timeline", sources=["knowledge"]),
            entity=ent.upper() if ent else ent,
            events=events,
            predictions=preds[:20],
        )

    def autocomplete(self, query: str) -> AutocompleteView:
        self._require()
        q = (query or "").strip()
        home = self.home()
        companies = [c.get("ticker") for c in (home.top_companies or []) if c.get("ticker")]
        # Also pull from search hits for typed query
        if q and self.aws:
            sr = dump(soft(self.aws.search, q, limit=10)) or {}
            for h in sr.get("hits") or []:
                if h.get("kind") == "company" and h.get("id"):
                    companies.append(str(h["id"]).upper())
                if h.get("ticker"):
                    companies.append(str(h["ticker"]).upper())
        companies = sorted({c for c in companies if c})
        pack = build_autocomplete(
            q,
            companies=companies,
            themes=home.market_themes,
            sectors=["Financials", "Technology", "Energy", "Healthcare", "Defence", "Auto"],
            articles=home.todays_research,
            popular=home.popular_questions,
        )
        return AutocompleteView(
            meta=UiMeta(surface="autocomplete", sources=["knowledge", "research_desk"]),
            query=q,
            companies=pack.get("companies") or [],
            themes=pack.get("themes") or [],
            sectors=pack.get("sectors") or [],
            articles=pack.get("articles") or [],
            questions=pack.get("questions") or [],
            popular_searches=pack.get("popular_searches") or [],
        )

    def article(self, article_id: str, *, ticker: str | None = None) -> ArticleView:
        self._require()
        aid = str(article_id)
        # Prefer RMS research id; also accept ticker-linked knowledge
        research = dump(soft(self.aws.research, aid)) if self.aws else None
        research = research or {}
        current = scrub(research.get("current_draft")) or {}
        tickers = list(current.get("tickers") or ([] if not ticker else [ticker.upper()]))
        themes = list(current.get("themes") or [])
        primary = tickers[0].upper() if tickers else (ticker.upper() if ticker else None)

        house = None
        conf = None
        graph = None
        timeline: list[dict[str, Any]] = []
        previous: list[dict[str, Any]] = []
        updates: list[dict[str, Any]] = []
        if primary and self.kip:
            house = scrub(dump(soft(self.kip.house_view, primary)))
            if isinstance(house, dict):
                conf = house.get("confidence")
            graph = scrub(dump(soft(self.kip.graph, primary)))
            timeline = scrub(_timeline_events(dump(soft(self.kip.timeline, primary))))[:20]
            hist = dump(soft(self.kip.research_history, primary)) or {}
            previous = scrub(hist.get("agi_reports") or [])[:8]
            updates = _kip_news(self.kip, primary, limit=5)

        status = thesis_status(house=house if isinstance(house, dict) else None)
        preds: list[dict[str, Any]] = []
        if primary and self.kip:
            for p in soft(self.kip.predictions, primary, default=[]) or []:
                pr = prediction_row(dump(p), ticker=primary)
                if pr:
                    preds.append(pr)
        qs = follow_up_questions(
            question=f"Summarise research {aid}",
            intent="research",
            related_companies=[str(t).upper() for t in tickers],
            related_themes=[str(t) for t in themes],
            house_label=str((house or {}).get("current_view") or (house or {}).get("stance") or "")
            if isinstance(house, dict)
            else None,
            recent_research_titles=[str(x.get("title")) for x in previous[:3] if isinstance(x, dict)],
        )
        # AGIB v4.0 — soft-assemble Research Intelligence Hub (never rebuilds stores)
        intelligence_hub: dict[str, Any] = {}
        try:
            from research_intelligence_hub.production import build as rih_build
            from research_intelligence_hub.production import hub as rih_hub

            existing = rih_hub(aid)
            if existing.get("mode") == "published" or existing.get("companies"):
                intelligence_hub = existing
            else:
                headline = (
                    scrub_text(current.get("title"))
                    or scrub_text(research.get("title"))
                    or aid
                )
                body = scrub_text(current.get("draft_body") or current.get("idea_summary") or "")
                intelligence_hub = rih_build(
                    note_id=aid,
                    headline=str(headline),
                    body=str(body),
                    tickers=[str(t).upper() for t in tickers],
                    persist=False,
                )
        except Exception:
            intelligence_hub = {}

        hub_companies = [
            str(c.get("id")).upper()
            for c in (intelligence_hub.get("companies") or [])
            if c.get("id")
        ]
        related_companies = list(
            dict.fromkeys([str(t).upper() for t in tickers] + hub_companies)
        )
        hub_evidence = [
            {
                "id": e.get("kind"),
                "title": e.get("summary"),
                "refs": e.get("refs"),
            }
            for e in (intelligence_hub.get("supporting_evidence") or [])
        ]

        return ArticleView(
            meta=UiMeta(
                surface="article",
                sources=["knowledge", "research_desk", "research_committee", "research_intelligence_hub"],
            ),
            article_id=aid,
            related_companies=related_companies,
            related_themes=[str(t) for t in themes],
            knowledge_graph=graph if isinstance(graph, dict) else None,
            research_timeline=timeline if isinstance(timeline, list) else [],
            previous_agi_articles=previous if isinstance(previous, list) else [],
            house_view=house if isinstance(house, dict) else None,
            confidence=float(conf) if conf is not None else (
                float((intelligence_hub.get("confidence") or {}).get("overall_pct") or 0) / 100.0
                if (intelligence_hub.get("confidence") or {}).get("overall_pct") is not None
                else None
            ),
            latest_updates=updates,
            supporting_evidence=(
                _as_docs(scrub(research.get("supporting_documents") or []))[:20] or hub_evidence
            ),
            whats_changed_since_publication=status.get("whats_changed_since_publication") or [],
            thesis_still_holds=status.get("thesis_still_holds"),
            thesis_status=status,
            prediction_status=preds[:8],
            latest_news=updates,
            discovery=discovery_pack(
                companies=related_companies,
                themes=[str(t) for t in themes],
                research=previous,
                questions=qs,
            ),
            follow_up_questions=qs,
            intelligence_hub=intelligence_hub if isinstance(intelligence_hub, dict) else {},
        )

    def research(self, research_id: str) -> ResearchView:
        self._require()
        ws = dump(soft(self.aws.research, research_id)) if self.aws else None
        ws = ws or {}
        current = scrub(ws.get("current_draft")) or {}
        tickers = list(current.get("tickers") or [])
        themes = list(current.get("themes") or [])
        sectors = list(current.get("sectors") or [])

        related = []
        if self.aws:
            for t in tickers[:3]:
                hits = dump(soft(self.aws.search, t, limit=5)) or {}
                for h in hits.get("hits") or []:
                    if h.get("kind") in {"research", "report"} and h.get("id") != research_id:
                        related.append(
                            {
                                "id": h.get("id"),
                                "title": scrub_text(h.get("title")),
                                "ticker": h.get("ticker"),
                            }
                        )

        news = _kip_news(self.kip, " ".join(tickers) or research_id, limit=5)
        timeline = scrub(_timeline_events(ws.get("research_timeline")))
        preds = []
        if self.kip and tickers:
            for t in tickers[:2]:
                for p in soft(self.kip.predictions, t, default=[]) or []:
                    d = dump(p)
                    if d:
                        preds.append(scrub(d))

        workflow = {
            "status": current.get("status"),
            "review_status": ws.get("review_status"),
            "approval_status": ws.get("approval_status"),
            "publishing_status": ws.get("publishing_status"),
            "stages": _workflow_stages(current.get("status")),
        }

        return ResearchView(
            meta=UiMeta(surface="research", sources=["research_desk", "knowledge", "research_committee"]),
            research_id=research_id,
            article=current,
            related_research=related[:10],
            related_companies=[str(x).upper() for x in tickers],
            related_themes=[str(x) for x in themes],
            related_sectors=[str(x) for x in sectors],
            latest_news=news,
            knowledge_timeline=timeline,
            research_timeline=timeline,
            supporting_evidence=_as_docs(scrub(ws.get("supporting_documents") or []))[:20],
            prediction_tracker=preds[:20],
            workflow=workflow,
        )

    def theme(self, theme_id: str) -> ThemeView:
        self._require()
        ws = dump(soft(self.aws.theme, theme_id)) if self.aws else None
        ws = ws or {}
        theme = scrub(ws.get("theme")) or {}
        docs = _as_docs(scrub(ws.get("documents") or ws.get("search_hits") or []))
        companies = [str(c).upper() for c in (ws.get("related_companies") or theme.get("tickers") or [])]
        risks = list(theme.get("risks") or [])[:10]
        catalysts = list(theme.get("catalysts") or [])[:10]
        thesis = theme.get("thesis") or theme.get("summary") or theme.get("theme")
        house = None
        graph = None
        if companies and self.kip:
            house = scrub(dump(soft(self.kip.house_view, str(companies[0]).upper())))
            graph = scrub(dump(soft(self.kip.graph, str(companies[0]).upper())))
        timeline = _timeline_events(ws.get("knowledge_graph") or ws.get("timeline"))
        intel = theme_intelligence(
            theme_id=theme_id,
            thesis=scrub_text(thesis) if thesis else None,
            companies=companies,
            risks=[scrub_text(str(r)) or "" for r in risks],
            catalysts=[scrub_text(str(c)) or "" for c in catalysts],
            research=docs[:15],
            house=house if isinstance(house, dict) else None,
            graph=graph if isinstance(graph, dict) else None,
            timeline=timeline,
            macro_themes=list(theme.get("related_macro") or theme.get("macro_themes") or [])[:6],
        )
        return ThemeView(
            meta=UiMeta(surface="theme", sources=["knowledge"]),
            theme_id=theme_id,
            current_thesis=scrub_text(thesis) if thesis else None,
            related_companies=companies,
            related_research=docs[:15],
            current_risks=[scrub_text(str(r)) or "" for r in risks],
            current_catalysts=[scrub_text(str(c)) or "" for c in catalysts],
            house_view=house,
            timeline=timeline,
            confidence=intel.get("confidence"),
            stance=intel.get("stance"),
            related_macro=intel.get("related_macro") or [],
            knowledge_graph=intel.get("knowledge_graph") or {},
            research_timeline=intel.get("research_timeline") or [],
            follow_up_questions=intel.get("follow_up_questions") or [],
            discovery=intel.get("discovery") or {},
            product_meta=intel.get("product_meta") or {},
        )

    def sector(self, sector_id: str) -> SectorView:
        self._require()
        ws = dump(soft(self.aws.sector, sector_id)) if self.aws else None
        ws = ws or {}
        coverage = ws.get("company_coverage") or {}
        ranked = sorted(
            ((str(k).upper(), int(v)) for k, v in coverage.items()),
            key=lambda kv: kv[1],
            reverse=True,
        )
        leaders = [k for k, _ in ranked[:5]]
        laggards = [k for k, _ in ranked[-3:]] if len(ranked) > 3 else []
        research = scrub(ws.get("rms_research") or ws.get("documents") or [])[:12]
        if not isinstance(research, list):
            research = []
        health = "Active coverage" if ranked else "Limited coverage"
        valuation = scrub(ws.get("portfolio_exposure") or {})
        risks = [scrub_text(str(r)) or "" for r in (ws.get("risks") or [])][:8]
        opportunities = [scrub_text(str(o)) or "" for o in (ws.get("opportunities") or [])][:8]
        macro_drivers = [scrub_text(str(m)) or "" for m in (ws.get("macro_drivers") or [])][:8]
        intel = sector_intelligence(
            sector_id=sector_id,
            health=health,
            leaders=leaders,
            laggards=laggards,
            research=research,
            valuation=valuation if isinstance(valuation, dict) else {},
            risks=risks,
            opportunities=opportunities,
            macro_drivers=macro_drivers,
            timeline=_as_docs(research),
        )
        return SectorView(
            meta=UiMeta(surface="sector", sources=["knowledge", "research_desk", "model_portfolio"]),
            sector_id=sector_id,
            sector_health=health,
            leaders=leaders,
            laggards=laggards,
            current_theme=sector_id,
            current_risks=intel.get("current_risks") or risks,
            current_research=research,
            valuation_snapshot=valuation if isinstance(valuation, dict) else {},
            current_outlook=intel.get("current_outlook"),
            current_opportunities=intel.get("current_opportunities") or [],
            macro_drivers=intel.get("macro_drivers") or [],
            sector_timeline=intel.get("sector_timeline") or [],
            valuation_summary=intel.get("valuation_summary") or {},
            follow_up_questions=intel.get("follow_up_questions") or [],
            discovery=intel.get("discovery") or {},
            product_meta=intel.get("product_meta") or {},
        )

    def dashboard(self) -> DashboardView:
        self._require()
        home = self.home()
        return DashboardView(
            meta=UiMeta(surface="dashboard", sources=home.meta.sources),
            market_brief=home.market_brief,
            market_regime=home.market_regime,
            market_risk=home.market_risk,
            todays_events=home.economic_calendar,
            research_queue=home.research_queue,
            latest_reports=home.latest_published or home.todays_research,
            system_health=home.system_health,
            sentiment={"themes": home.market_themes[:6]},
        )

    def macro(self) -> MacroView:
        self._require()
        ws = dump(soft(self.aws.macro)) if self.aws else None
        ws = ws or {}
        regime = scrub(ws.get("e01") or ws.get("market_regime") or {})
        risk = scrub(ws.get("e14") or ws.get("market_risk") or {})
        docs = scrub(ws.get("macro_documents") or [])
        themes = list(ws.get("themes") or [])
        events = [
            {"title": t, "category": "theme"}
            for t in themes[:8]
        ]
        events += [
            d
            for d in docs
            if isinstance(d, dict)
            and any(x in str(d.get("title") or "").lower() for x in ("rbi", "fed", "ecb", "central"))
        ][:8]
        theme_names: list[str] = []
        for t in themes or []:
            if isinstance(t, dict):
                name = t.get("name") or t.get("id")
                if name:
                    theme_names.append(str(name))
            elif t:
                theme_names.append(str(t))
        related_companies: list[str] = []
        port = dump(soft(self.aws.portfolio)) if self.aws else None
        book = (port or {}).get("l4_book") or {}
        if isinstance(book, dict):
            related_companies = [str(k).upper() for k in list(book.keys())[:8]]
        intel = macro_intelligence(
            regime=regime if isinstance(regime, dict) else None,
            risk=risk if isinstance(risk, dict) else None,
            events=scrub(events)[:10],
            research=_as_docs(docs)[:15],
            themes=theme_names,
            related_companies=related_companies,
        )
        return MacroView(
            meta=UiMeta(surface="macro", sources=["market_regime", "market_risk", "knowledge"]),
            current_regime={
                "label": pick_label(regime if isinstance(regime, dict) else None, "regime", "label")
                or "Unavailable",
                "detail": regime if isinstance(regime, dict) else {},
            },
            macro_dashboard={
                "regime": regime,
                "risk": risk,
                "themes": themes,
            },
            regime_history=[],
            macro_timeline=_as_docs(docs)[:15],
            macro_research=_as_docs(docs)[:15],
            central_bank_events=scrub(events)[:10],
            market_risk=risk if isinstance(risk, dict) else {},
            intelligence=intel,
            follow_up_questions=intel.get("follow_up_questions") or [],
            discovery=intel.get("discovery") or {},
        )

    def predictions(self) -> PredictionCentreView:
        self._require()
        preds: list[dict[str, Any]] = []
        home = self.home()
        tickers = [str(c.get("ticker")).upper() for c in (home.top_companies or []) if c.get("ticker")]
        if self.kip:
            for tk in tickers[:12]:
                for p in soft(self.kip.predictions, tk, default=[]) or []:
                    pr = prediction_row(dump(p), ticker=tk)
                    if pr:
                        preds.append(pr)
        # de-dupe by id
        seen: set[str] = set()
        uniq: list[dict[str, Any]] = []
        for p in preds:
            pid = str(p.get("id"))
            if pid in seen:
                continue
            seen.add(pid)
            uniq.append(p)
        acc = accuracy_summary(uniq)
        qs = follow_up_questions(
            question="How accurate are AGI predictions?",
            intent="prediction",
            related_companies=tickers[:6],
            related_themes=[str(t.get("id") or t.get("name")) for t in (home.market_themes or [])][:4],
            house_label=None,
        )
        timeline = [
            {
                "as_of": p.get("publication_date"),
                "type": "prediction",
                "title": p.get("thesis") or p.get("ticker"),
                "summary": f"{p.get('current_status')} · {p.get('target_horizon')}",
            }
            for p in uniq[:20]
        ]
        return PredictionCentreView(
            meta=UiMeta(surface="predictions", sources=["knowledge", "evaluation"]),
            predictions=uniq[:40],
            accuracy=acc,
            prediction_timeline=enrich_timeline(timeline),
            discovery=discovery_pack(
                companies=tickers,
                themes=[str(t.get("id") or t.get("name")) for t in (home.market_themes or [])][:6],
                questions=qs,
            ),
            follow_up_questions=qs,
        )

    def portfolio(self) -> PortfolioView:
        self._require()
        ws = dump(soft(self.aws.portfolio)) if self.aws else None
        ws = ws or {}
        current = scrub(ws.get("current_portfolio"))
        conf = None
        if isinstance(current, dict):
            conf = pick_number(current, "confidence", "average_confidence")
        book = scrub(ws.get("l4_book") or {})
        return PortfolioView(
            meta=UiMeta(
                surface="portfolio",
                sources=["model_portfolio", "market_risk", "composite_view", "evaluation"],
            ),
            current_portfolio=current,
            historical_portfolio=scrub(ws.get("historical_portfolio") or []),
            sector_allocation=scrub(ws.get("sector_exposure") or {}),
            risk=scrub(ws.get("risk")),
            performance=scrub(ws.get("performance")),
            attribution=scrub(ws.get("attribution")),
            confidence=conf,
            composite_book=book if isinstance(book, dict) else {},
        )

    def copilot(
        self,
        *,
        page: str = "home",
        question: str = "",
        ticker: str | None = None,
        theme_id: str | None = None,
        sector_id: str | None = None,
        research_id: str | None = None,
    ) -> CopilotView:
        self._require()
        raw = (
            dump(
                soft(
                    self.aws.copilot,
                    workspace=_page_to_workspace(page),
                    question=question,
                    ticker=ticker,
                    theme_id=theme_id,
                    sector_id=sector_id,
                    research_id=research_id,
                )
            )
            if self.aws
            else None
        )
        raw = raw or {}
        ctx = {
            "page": page,
            "house_view": scrub(raw.get("house_view")),
            "knowledge": scrub(raw.get("kip")),
            "research_committee": scrub(raw.get("rsp")),
            "composite_view": scrub(raw.get("l4")),
            "portfolio": scrub(raw.get("portfolio")),
            "research": scrub(raw.get("research")),
            "model_evidence": scrub(raw.get("engines") or raw.get("model_evidence") or {}),
            "latest_news": _kip_news(self.kip, question or ticker or page, limit=4),
        }
        return CopilotView(
            meta=UiMeta(surface="copilot", sources=["knowledge", "research_committee", "composite_view"]),
            page=page,
            question=question or f"Assist with {page}",
            context=ctx,
            answer_policy="context_aware_never_empty",
        )

    def workflow(self) -> WorkflowView:
        self._require()
        dash = dump(soft(self.rms.dashboard)) if self.rms else None
        dash = dash or {}
        stages = [
            {"id": "idea", "label": "Idea"},
            {"id": "draft", "label": "Draft"},
            {"id": "review", "label": "Review"},
            {"id": "compliance", "label": "Compliance"},
            {"id": "approval", "label": "Approval"},
            {"id": "published", "label": "Published"},
            {"id": "knowledge_ingested", "label": "Knowledge Ingested"},
            {"id": "prediction_tracking", "label": "Prediction Tracking"},
        ]
        pipeline = []
        for r in soft(self.rms.store.list_all, default=[]) or []:
            pipeline.append(
                {
                    "research_id": r.research_id,
                    "title": scrub_text(r.title),
                    "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                    "tickers": r.tickers,
                    "stages": _workflow_stages(
                        r.status.value if hasattr(r.status, "value") else str(r.status)
                    ),
                }
            )
        return WorkflowView(
            meta=UiMeta(surface="workflow", sources=["research_desk", "knowledge"]),
            stages=stages,
            pipeline=scrub(pipeline)[:40],
            draft_queue=scrub(dash.get("draft_queue") or []),
            review_queue=scrub(dash.get("review_queue") or []),
            published=[
                p for p in pipeline if str(p.get("status")).lower() == "published"
            ][:20],
        )

    def _hydrate_evidence(self, items: list[Any]) -> list[dict[str, Any]]:
        """Resolve bare doc_ ids into real titles/snippets from KIP when possible."""
        out: list[dict[str, Any]] = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            row = dict(item)
            doc_id = row.get("id") or row.get("document_id")
            title = str(row.get("title") or "").strip()
            needs_title = (not title) or title.startswith("doc_") or (
                doc_id and title == str(doc_id)
            )
            needs_summary = not (row.get("snippet") or row.get("summary"))
            if self.kip and doc_id and (needs_title or needs_summary):
                src = soft(self.kip.get_document, str(doc_id))
                if src is not None:
                    doc_title = getattr(getattr(src, "document", None), "title", None)
                    research = getattr(src, "research", None)
                    knowledge = getattr(src, "knowledge", None)
                    if needs_title and doc_title:
                        row["title"] = scrub_text(doc_title) or doc_title
                    if needs_summary:
                        summary = None
                        if knowledge is not None:
                            summary = getattr(knowledge, "summary", None)
                        if not summary and research is not None:
                            summary = getattr(research, "investment_thesis", None)
                        if summary:
                            row["summary"] = scrub_text(str(summary)[:320]) or str(summary)[:320]
                            row.setdefault("snippet", row["summary"])
                    if research is not None and not row.get("tickers"):
                        inv = getattr(src, "investment", None)
                        tickers = list(getattr(inv, "tickers", None) or [])
                        row["tickers"] = [
                            str(t).upper()
                            for t in tickers
                            if str(t).upper() in KNOWN_TICKERS or str(t).upper().endswith("BANK")
                        ]
            # Final ticker scrub for already-populated noisy lists
            if isinstance(row.get("tickers"), list):
                row["tickers"] = [
                    str(t).upper()
                    for t in row["tickers"]
                    if str(t).upper() in KNOWN_TICKERS or str(t).upper().endswith("BANK")
                ]
            out.append(row)
        return out

    def _require(self) -> None:
        if not self.flags.ui:
            raise RuntimeError("UI aggregation disabled (UI=false)")


def _sample_book(book: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    if not isinstance(book, dict):
        return out
    for sym, opinion in list(book.items())[:8]:
        if not isinstance(opinion, dict):
            continue
        out.append(
            {
                "ticker": str(sym).upper(),
                "label": pick_label(opinion, "label", "side") or "Neutral",
                "score": pick_number(opinion, "composite_score", "score"),
                "confidence": pick_number(opinion, "confidence"),
            }
        )
    return out


def _iso_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _brief_summary(regime: dict, risk: dict, composite: dict) -> str:
    n = composite.get("n_names") or 0
    coverage = f"{n} names in the composite book" if n else "selective institutional coverage"
    return (
        f"{regime.get('label')} regime with {risk.get('label')} risk — "
        f"{coverage}. Stay selective into the next policy window."
    )


def _system_health(ioc: dict | None, dash: dict | None) -> dict[str, Any]:
    if ioc:
        return {
            "overall": ioc.get("overall") or ioc.get("status") or "unknown",
            "readiness": ioc.get("readiness") or ioc.get("morning_readiness"),
            "alerts": len(ioc.get("alerts") or []),
            "detail": scrub(
                {
                    k: v
                    for k, v in ioc.items()
                    if k in {"overall", "status", "platforms", "engines", "queues"}
                }
            ),
        }
    if dash:
        return {"overall": "degraded" if not dash.get("platform_health") else "ok", "detail": scrub(dash.get("platform_health"))}
    return {"overall": "unknown"}


def _kip_news(kip: Any, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    if not kip:
        return []
    sr = soft(kip.search, query or "markets", mode="hybrid", limit=limit)
    if not sr:
        return []
    out = []
    for h in getattr(sr, "hits", []) or []:
        d = dump(h) or {}
        out.append(
            {
                "id": d.get("document_id"),
                "title": scrub_text(d.get("title")),
                "snippet": scrub_text(d.get("snippet")),
                "tickers": d.get("tickers") or [],
                "type": d.get("document_type"),
            }
        )
    return out


def _kip_themes(kip: Any, *, limit: int = 8) -> list[dict[str, Any]]:
    if not kip:
        return []
    # Derive from recent search / store themes if available
    out: list[dict[str, Any]] = []
    store = getattr(kip, "store", None)
    theme_map = getattr(store, "themes", None) if store else None
    if isinstance(theme_map, dict):
        for theme_id in list(theme_map.keys())[:limit]:
            out.append(
                {
                    "id": str(theme_id),
                    "name": scrub_text(str(theme_id).replace("_", " ").title()),
                    "tickers": [],
                }
            )
    if out:
        return out
    # Fallback: scan search hits for theme tags
    sr = soft(kip.search, "theme investment", mode="hybrid", limit=limit)
    for h in getattr(sr, "hits", []) or []:
        d = dump(h) or {}
        for t in d.get("themes") or []:
            out.append({"id": str(t), "name": scrub_text(str(t)), "tickers": d.get("tickers") or []})
        if len(out) >= limit:
            break
    # de-dupe
    seen = set()
    uniq = []
    for row in out:
        key = row.get("id") or row.get("name")
        if key in seen:
            continue
        seen.add(key)
        uniq.append(row)
    return uniq[:limit]


def _event_items(aws: Any) -> list[dict[str, Any]]:
    """Soft calendar pull — empty means caller fills institutional defaults."""
    if not aws:
        return []
    try:
        macro = dump(soft(aws.macro)) if aws else None
        events = []
        if isinstance(macro, dict):
            for key in ("calendar", "economic_calendar", "events", "upcoming_events"):
                rows = macro.get(key)
                if isinstance(rows, list) and rows:
                    events = rows
                    break
        out: list[dict[str, Any]] = []
        for ev in events[:12]:
            if not isinstance(ev, dict):
                continue
            title = ev.get("title") or ev.get("name") or ev.get("event")
            if not title:
                continue
            out.append(
                {
                    "id": ev.get("id") or f"cal-{len(out)}",
                    "title": scrub_text(title),
                    "name": scrub_text(title),
                    "country": ev.get("country") or ev.get("region") or "IN",
                    "region": ev.get("region") or ev.get("country") or "India",
                    "importance": ev.get("importance") or ev.get("impact") or "Medium",
                    "expected_impact": scrub_text(ev.get("expected_impact") or ev.get("note") or ""),
                    "affected_sectors": ev.get("affected_sectors") or ev.get("sectors") or [],
                    "affected_companies": ev.get("affected_companies") or ev.get("tickers") or [],
                    "as_of": ev.get("as_of") or ev.get("date") or ev.get("time"),
                    "date": ev.get("date") or ev.get("as_of") or ev.get("time"),
                }
            )
        return out
    except Exception:
        return []


def _timeline_events(timeline: Any) -> list[dict[str, Any]]:
    if timeline is None:
        return []
    if isinstance(timeline, list):
        return timeline[:30]
    if isinstance(timeline, dict):
        for key in ("events", "points", "items", "nodes", "entries"):
            if isinstance(timeline.get(key), list):
                return timeline[key][:30]
        return [timeline]
    return []


def _filter_docs(docs: list, needle: str) -> list[dict[str, Any]]:
    out = []
    for d in docs:
        if not isinstance(d, dict):
            continue
        blob = f"{d.get('title')} {d.get('document_type')}".lower()
        if needle in blob:
            out.append(d)
    return out[:10]


def _as_docs(items: Any) -> list[dict[str, Any]]:
    return _evidence_dicts(items)


def _evidence_dicts(items: Any) -> list[dict[str, Any]]:
    if not items:
        return []
    out: list[dict[str, Any]] = []
    for x in items:
        if isinstance(x, dict):
            row = dict(x)
            # Normalize RagEvidenceItem dumps
            if not row.get("id") and row.get("document_id"):
                row["id"] = row["document_id"]
            if not row.get("title") and row.get("document_id"):
                # Avoid showing bare ids as titles when snippet exists
                row["title"] = row.get("snippet") or row["document_id"]
            if row.get("snippet") and not row.get("summary"):
                row["summary"] = row["snippet"]
            # Sanitize noisy tickers on evidence cards
            if isinstance(row.get("tickers"), list):
                row["tickers"] = [
                    str(t).upper()
                    for t in row["tickers"]
                    if str(t).upper() in KNOWN_TICKERS or str(t).upper().endswith("BANK")
                ]
            out.append(row)
        else:
            sid = str(x)
            # Skip bare doc ids without metadata — they render as useless cards.
            if sid.startswith("doc_") and len(sid) < 40:
                continue
            out.append({"id": sid, "title": scrub_text(sid)})
    return out


_JUNK_EVIDENCE_TITLES = {
    "hello world",
    "sample private research",
    "test",
    "asdf",
    "lorem ipsum",
    "untitled",
    "demo",
}


def _filter_junk_docs(items: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        title_l = title.lower()
        if not title or title_l in _JUNK_EVIDENCE_TITLES:
            continue
        if title.startswith("doc_") and not (item.get("snippet") or item.get("summary")):
            continue
        if title_l.startswith(("test ", "demo ", "sample ", "hello ")):
            continue
        out.append(item)
    return out


def _search_answer_summary(
    question: str,
    house: dict | None,
    confidence: float | None,
    supporting: list,
    house_label: str | None = None,
) -> str:
    house = flatten_house_view(house) if house else None
    label = normalize_stance(
        house_label
        or (house.get("stance") if house else None)
        or (house.get("current_view_label") if house else None)
        or (house.get("label") if house else None)
    )
    thesis = clean_thesis_text((house or {}).get("thesis") or (house or {}).get("summary") or "")
    if not thesis and supporting:
        top = supporting[0] if isinstance(supporting[0], dict) else {}
        thesis = clean_thesis_text(top.get("snippet") or top.get("summary") or top.get("title") or "")
    if house and (thesis or label != "Neutral" or house.get("current_view")):
        conf_val = confidence if confidence is not None else (house or {}).get("confidence")
        if isinstance(conf_val, (int, float)) and conf_val > 1:
            conf = f" Confidence {conf_val:.0f}%."
        elif isinstance(conf_val, (int, float)):
            conf = f" Confidence {conf_val:.0%}."
        else:
            conf = ""
        thesis_bit = f" {thesis[:220]}" if thesis else ""
        return (
            f"AGI institutional view on “{question}”: {label}.{conf}"
            f"{thesis_bit} "
            f"Evidence pack includes {len(supporting)} supporting research items. "
            "Not investment advice."
        )
    if supporting:
        top = supporting[0] if isinstance(supporting[0], dict) else {}
        title = scrub_text(top.get("title")) if isinstance(top, dict) else None
        if title and str(title).startswith("doc_"):
            title = None
        snip = scrub_text(top.get("snippet") or top.get("summary")) if isinstance(top, dict) else None
        lead = f" Latest note: {title}." if title else ""
        detail = f" {snip[:200]}" if snip else ""
        return (
            f"Institutional evidence pack for “{question}”.{lead}{detail} "
            f"{len(supporting)} research items retrieved. Not investment advice."
        )
    return (
        f"Institutional evidence pack for “{question}”. "
        "House view not yet established for the detected subject. "
        "Review supporting research and conflicting opinions below. "
        "Not investment advice."
    )


def _why_bullets(
    house: dict | None,
    supporting: list,
    news: list,
    house_label: str | None,
) -> list[str]:
    out: list[str] = []
    house = flatten_house_view(house) if house else None
    label = normalize_stance(
        house_label or (house.get("stance") if house else None)
    )
    if label:
        out.append(f"Current AGI house view is {label}.")
    thesis = clean_thesis_text((house or {}).get("thesis") or "")
    if thesis:
        out.append(thesis[:200])
    elif supporting:
        top = supporting[0] if isinstance(supporting[0], dict) else {}
        snip = clean_thesis_text(top.get("snippet") or top.get("summary") or top.get("title") or "")
        if snip and not snip.startswith("doc_"):
            out.append(snip[:200])
    if supporting:
        out.append(f"{len(supporting)} supporting AGI / institutional research items retrieved.")
    if news:
        out.append(f"{len(news)} related news items included for freshness.")
    if house and house.get("changed_assumptions"):
        out.append("Recent thesis assumptions have changed — see knowledge timeline.")
    if not out:
        out.append("Answer assembled from AGI knowledge, research committee reasoning, and live desk context.")
    # Never surface raw object dumps in Why chips.
    cleaned: list[str] = []
    for x in out[:6]:
        s = scrub_text(x) or str(x)
        if s.startswith("{") or "document_id" in s:
            continue
        cleaned.append(s)
    return cleaned or ["Answer assembled from AGI knowledge and live desk context."]


def _workflow_stages(status: str | None) -> list[dict[str, Any]]:
    order = [
        "idea",
        "requested",
        "draft",
        "internal_review",
        "compliance_review",
        "approved",
        "published",
        "ingested",
        "prediction_tracking",
    ]
    aliases = {
        "request": "requested",
        "review": "internal_review",
        "compliance": "compliance_review",
        "approval": "approved",
        "knowledge_ingested": "ingested",
    }
    cur = aliases.get(str(status or "").lower(), str(status or "").lower())
    reached = True
    out = []
    # Map coarse status into pipeline
    status_rank = {
        "idea": 0,
        "requested": 1,
        "draft": 2,
        "internal_review": 3,
        "compliance_review": 4,
        "approved": 5,
        "published": 6,
        "ingested": 7,
        "prediction_tracking": 8,
    }
    rank = status_rank.get(cur, 0)
    labels = {
        "idea": "Idea",
        "requested": "Request",
        "draft": "Draft",
        "internal_review": "Review",
        "compliance_review": "Compliance",
        "approved": "Approval",
        "published": "Published",
        "ingested": "Knowledge Ingested",
        "prediction_tracking": "Prediction Tracking",
    }
    for i, sid in enumerate(order):
        out.append(
            {
                "id": sid,
                "label": labels[sid],
                "state": "done" if i <= rank else "pending",
                "current": i == rank,
            }
        )
    return out


def _page_to_workspace(page: str) -> str:
    p = (page or "home").lower()
    if p in {"company", "sector", "theme", "macro", "portfolio", "research", "replay", "cre"}:
        return p
    if p in {"home", "dashboard", "market"}:
        return "company"
    return "company"
