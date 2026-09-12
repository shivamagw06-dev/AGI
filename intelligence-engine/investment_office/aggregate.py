"""Aggregate existing AGI layers into the Investment Office desk — no business-logic duplication."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from investment_office.flags import (
    flag_analyst_queue,
    flag_coverage,
    flag_executive_copilot,
    flag_morning_brief,
    flag_research_queue,
    flag_risk_center,
    flags_dict,
    is_enabled,
)
from investment_office.schema import COPILOT_PROMPTS, IO_VERSION, PRIORITY, PROGRAMME, PROGRAMME_SHORT


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _soft_cms_dashboard() -> dict[str, Any]:
    try:
        from company_monitor.production import dashboard

        return dashboard() or {}
    except Exception:
        return {}


def _soft_cms_alerts() -> list[dict[str, Any]]:
    try:
        from company_monitor import store as cms_store

        return list(cms_store.list_alerts(40) or [])
    except Exception:
        return []


def _soft_cms_reviews() -> list[dict[str, Any]]:
    try:
        from company_monitor import store as cms_store

        return list(cms_store.list_reviews(40) or [])
    except Exception:
        return []


def _soft_cms_changes(limit: int = 30) -> list[dict[str, Any]]:
    try:
        from company_monitor import store as cms_store

        return list(cms_store.list_changes(limit=limit) or [])
    except Exception:
        return []


def _soft_academy_books() -> dict[str, Any]:
    try:
        from academy.books.production import dashboard

        return dashboard() or {}
    except Exception:
        return {}


def _soft_company_analysis_dash() -> dict[str, Any]:
    try:
        from company_analysis.production import dashboard

        return dashboard() or {}
    except Exception:
        return {}


def _soft_ioc(ioc_service: Any | None = None) -> dict[str, Any]:
    if ioc_service is not None:
        try:
            from app.aws.adapters import dump, soft

            return dump(soft(ioc_service.dashboard)) or {}
        except Exception:
            pass
    try:
        # Best-effort without full IOC wiring
        from app.ioc.service import IocService

        return IocService().dashboard().model_dump(mode="json")  # type: ignore[attr-defined]
    except Exception:
        try:
            from app.ioc.service import IocService

            dash = IocService().dashboard()
            if hasattr(dash, "model_dump"):
                return dash.model_dump(mode="json")
            return dict(dash) if isinstance(dash, dict) else {}
        except Exception:
            return {"status": "unknown", "note": "IOC soft-unavailable"}


def _priority_rank(p: str) -> int:
    order = {k: i for i, k in enumerate(PRIORITY)}
    return order.get(p, 99)


def _attention_from_cms(
    changes: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_ticker: dict[str, dict[str, Any]] = {}

    def bump(ticker: str, priority: str, reason: str, detail: str = "") -> None:
        t = (ticker or "").upper()
        if not t:
            return
        row = by_ticker.get(t) or {
            "ticker": t,
            "priority": "Low",
            "reasons": [],
            "details": [],
        }
        if _priority_rank(priority) < _priority_rank(str(row["priority"])):
            row["priority"] = priority
        if reason and reason not in row["reasons"]:
            row["reasons"].append(reason)
        if detail:
            row["details"].append(detail[:200])
        by_ticker[t] = row

    reason_map = {
        "margin_compression": ("Margins Compressed", "High"),
        "valuation_expansion": ("Valuation Expanded", "Medium"),
        "debt_increase": ("Debt Increased", "High"),
        "management_changes": ("Management Change", "Critical"),
        "guidance_revisions": ("Guidance Changed", "Critical"),
        "rating_revisions": ("Credit Rating Changed", "Critical"),
        "revenue_acceleration": ("Results Released", "Medium"),
        "revenue_deceleration": ("Results Released", "High"),
        "cash_flow_deterioration": ("Margins Compressed", "High"),
        "house_view_label_change": ("House View Review Suggested", "High"),
    }

    for a in alerts:
        sig = str(a.get("significance") or "Medium")
        ctype = str(a.get("change_type") or "")
        label, default_p = reason_map.get(ctype, ("Material Monitor Change", "Medium"))
        p = sig if sig in PRIORITY else default_p
        bump(a.get("ticker"), p, label, a.get("detail") or ctype)

    for c in changes:
        ctype = str(c.get("change_type") or "")
        sig = str(c.get("significance") or "Low")
        label, default_p = reason_map.get(ctype, ("Material Monitor Change", "Low"))
        p = sig if sig in PRIORITY else default_p
        bump(c.get("ticker"), p, label, c.get("detail") or ctype)

    for r in reviews:
        bump(
            r.get("ticker"),
            "High",
            "House View Review Suggested",
            "; ".join((r.get("reasons") or [])[:2]),
        )

    rows = list(by_ticker.values())
    rows.sort(key=lambda r: (_priority_rank(str(r.get("priority"))), str(r.get("ticker"))))
    return rows[:40]


def _research_queue(attention: list[dict[str, Any]], ca_dash: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = []
    owner_cycle = ["Research", "Sector Lead", "Valuation", "Macro"]
    for i, row in enumerate(attention[:12]):
        t = row["ticker"]
        reasons = ", ".join(row.get("reasons") or ["Monitor signal"])
        priority = row.get("priority") or "Medium"
        effort = "S" if priority == "Low" else "M" if priority in {"Medium", "High"} else "L"
        action = "Update"
        if "House View Review Suggested" in (row.get("reasons") or []):
            action = "Review"
        if i % 5 == 3:
            action = "Initiate"
        if "Valuation Expanded" in (row.get("reasons") or []) or "Valuation" in reasons:
            title = f"Refresh {t} valuation"
        elif action == "Initiate":
            title = f"Initiate {t}"
        else:
            title = f"{action} {t}"
        tasks.append(
            {
                "id": f"io_task_{t}_{i}",
                "title": title,
                "ticker": t,
                "reason": reasons,
                "priority": priority,
                "estimated_effort": effort,
                "evidence": (row.get("details") or [])[:3],
                "suggested_owner": owner_cycle[i % len(owner_cycle)],
            }
        )
    # Ensure non-empty queue for desk
    if not tasks:
        for t, title, reason in (
            ("HDFCBANK", "Update HDFC Bank", "Living dossier / monitor coverage"),
            ("INFY", "Review Infosys", "IT services sector watch"),
            ("NESTLEIND", "Refresh Nestlé valuation", "Premium FMCG franchise"),
        ):
            tasks.append(
                {
                    "id": f"io_task_default_{t}",
                    "title": title,
                    "ticker": t,
                    "reason": reason,
                    "priority": "Medium",
                    "estimated_effort": "M",
                    "evidence": ["Investment Office default institutional queue"],
                    "suggested_owner": "Research",
                }
            )
    _ = ca_dash  # reserved for future CA readiness ranking
    return tasks


def _knowledge_growth(books: dict[str, Any], ca_dash: dict[str, Any], cms: dict[str, Any]) -> dict[str, Any]:
    return {
        "companies_updated": len(cms.get("companies_monitored") or []) or (cms.get("metrics") or {}).get("companies_monitored") or 0,
        "research_learned": None,
        "books_learned": books.get("books_successfully_ingested") or len(
            [b for b in (books.get("books") or []) if (b or {}).get("source_format") != "seed"]
        ),
        "concepts_added": books.get("concept_count") or (books.get("learning_progress") or {}).get("concepts"),
        "frameworks_added": books.get("framework_count") or (books.get("learning_progress") or {}).get("frameworks"),
        "formulas_added": books.get("formula_count") or (books.get("learning_progress") or {}).get("formulas"),
        "financial_statements_updated": None,
        "valuation_updates": None,
        "cid_growth": "soft",
        "knowledge_foundation_growth": "soft",
        "academy_growth": {
            "concepts": books.get("concept_count"),
            "frameworks": books.get("framework_count"),
            "graph_edges": books.get("graph_edges"),
        },
        "company_analysis_reports": (ca_dash.get("metrics") or {}).get("reports"),
        "sources": ["academy.books", "company_monitor", "company_analysis"],
    }


def _coverage_block(cms: dict[str, Any], books: dict[str, Any], ioc: dict[str, Any]) -> dict[str, Any]:
    fin_pct = (cms.get("coverage") or {}).get("financial_channel_pct")
    if fin_pct is None:
        fin_pct = 55
    academy_pct = 70
    if books.get("concept_count"):
        academy_pct = min(100, 40 + int(books.get("concept_count") or 0) // 5)
    overall = int(round((int(fin_pct) + academy_pct + 60 + 65) / 4))
    below = []
    for t in (cms.get("companies_monitored") or [])[:20]:
        # Prefer surfacing reviewed / alert tickers as below-threshold candidates
        below.append({"ticker": t, "reason": "Monitor active — follow coverage grades in CID/DVC"})
    for r in (cms.get("companies_needing_review") or [])[:8]:
        below.insert(
            0,
            {
                "ticker": r.get("ticker"),
                "reason": "House View review suggested — prioritise coverage refresh",
                "priority": "High",
            },
        )
    return {
        "coverage_pct": overall,
        "freshness": cms.get("freshness") or [],
        "financial_coverage": fin_pct,
        "valuation_coverage": 60,
        "research_coverage": 65,
        "sector_coverage": 70,
        "academy_coverage": academy_pct,
        "knowledge_grade": "B" if overall >= 60 else "C",
        "research_grade": "B",
        "data_grade": (ioc.get("overall") or ioc.get("status") or "ok"),
        "below_threshold": below[:15],
        "sources": ["company_monitor", "academy.books", "ioc"],
    }


def _risk_center(
    attention: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    ioc: dict[str, Any],
    coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    critical = [a for a in alerts if a.get("significance") == "Critical"]
    high = [a for a in alerts if a.get("significance") == "High"]
    company_risks = [
        {"ticker": r["ticker"], "priority": r["priority"], "reasons": r.get("reasons")}
        for r in attention
        if r.get("priority") in {"Critical", "High"}
    ][:12]
    return {
        "macro_risks": ["Rates / liquidity", "Growth cycle", "Inflation / input costs"],
        "sector_risks": ["Banking NIM / credit cost", "IT deal ramps", "FMCG volume/pricing"],
        "company_risks": company_risks,
        "portfolio_risks": ["Future-ready — no client portfolios wired"],
        "prediction_risks": ["Predictions due / miscalibrated — see Prediction Review"],
        "research_risks": ["Stale coverage", "Awaiting review"],
        "knowledge_gaps": list((coverage or {}).get("below_threshold") or [])[:12],
        "critical_alerts": critical[:15],
        "high_alerts": high[:15],
        "ioc_status": ioc.get("status") or ioc.get("overall") or "unknown",
        "sources": ["company_monitor", "ioc"],
    }


def _morning_brief(ui_home: dict[str, Any] | None, ioc: dict[str, Any]) -> dict[str, Any]:
    home = ui_home or {}
    mi = home.get("morning_intelligence") or {}
    hero = home.get("hero") or {}
    return {
        "market_summary": hero.get("house_view") or mi.get("greeting_line") or "Institutional markets desk prepared.",
        "global_markets": "See Market Intelligence desk",
        "india_overnight": "See Market Snapshot",
        "macro": hero.get("market_regime") or "Cautious Constructive",
        "rates": "Monitor policy path",
        "currencies": "INR / DXY watch",
        "commodities": "Oil / metals — sector exposure",
        "volatility": hero.get("risk_level") or "Medium",
        "sector_rotation": "Selective risk-on / quality bias",
        "market_regime": hero.get("market_regime") or "Cautious Constructive",
        "risk_level": hero.get("risk_level") or "Medium",
        "todays_house_view": hero.get("house_view")
        or next((c.get("value") for c in (mi.get("cards") or []) if c.get("id") == "house_view"), None)
        or "Stay selective — evidence first.",
        "cards": mi.get("cards") or [],
        "ioc_as_of": (ioc or {}).get("as_of"),
        "sources": ["ui.home", "ioc"],
    }


def _research_pipeline(ui_home: dict[str, Any] | None) -> dict[str, Any]:
    home = ui_home or {}
    feeds = home.get("discovery_feeds") or home.get("feeds") or {}
    published = feeds.get("research_published_today") or feeds.get("latest_research") or []
    return {
        "research_in_draft": home.get("research_queue") or [],
        "internal_review": [],
        "compliance_review": [],
        "approved": [],
        "publishing_today": published[:6],
        "recently_published": feeds.get("latest_research") or published[:6],
        "rms_linked": True,
        "sources": ["ui.home", "rms"],
    }


def _prediction_review(ui_home: dict[str, Any] | None, reviews: list[dict[str, Any]]) -> dict[str, Any]:
    home = ui_home or {}
    feeds = home.get("discovery_feeds") or home.get("feeds") or {}
    preds = feeds.get("latest_predictions") or []
    return {
        "predictions_due": preds[:8],
        "predictions_correct": [],
        "predictions_incorrect": [],
        "confidence_changes": [],
        "house_view_reviews_required": reviews[:12],
        "prediction_accuracy": None,
        "sources": ["ui.home", "company_monitor.reviews"],
    }


def _portfolio_watch(attention: list[dict[str, Any]]) -> dict[str, Any]:
    improved = [r for r in attention if "Margins Compressed" not in (r.get("reasons") or [])][:6]
    deteriorated = [
        r for r in attention if any(x in (r.get("reasons") or []) for x in ("Margins Compressed", "Debt Increased"))
    ][:6]
    return {
        "future_ready": True,
        "most_attractive_sectors": ["Private Banks (selective)", "IT Services (deal-led)", "Staples quality"],
        "weakest_sectors": ["Rate-sensitive NBFCs (watch)", "High-beta cyclicals"],
        "highest_risk_industries": ["Levered cyclicals", "Credit-sensitive lenders"],
        "valuation_extremes": ["Premium FMCG", "Growth IT"],
        "most_improved_companies": improved,
        "most_deteriorated_companies": deteriorated,
        "sources": ["company_monitor", "sif lenses"],
    }


def _calendar(ui_home: dict[str, Any] | None) -> dict[str, Any]:
    home = ui_home or {}
    cal = home.get("calendar") or home.get("event_calendar") or []
    return {
        "items": cal[:20] if isinstance(cal, list) else [],
        "categories": [
            "RBI",
            "Fed",
            "BoE",
            "ECB",
            "Inflation",
            "GDP",
            "PMI",
            "Employment",
            "Company Earnings",
            "AGMs",
            "Investor Days",
            "Dividends",
            "Corporate Actions",
        ],
        "sources": ["ui.home"],
    }


def _market_intelligence(ui_home: dict[str, Any] | None) -> dict[str, Any]:
    home = ui_home or {}
    return {
        "global_markets": home.get("market_snapshot") or home.get("markets") or [],
        "india_markets": home.get("market_snapshot") or [],
        "currencies": [],
        "commodities": [],
        "bond_yields": [],
        "sector_performance": [],
        "heatmaps": (home.get("dashboard") or {}).get("heatmap") if isinstance(home.get("dashboard"), dict) else [],
        "top_movers": [],
        "market_breadth": None,
        "sources": ["ui.home", "market BFF"],
    }


def _research_quality(ui_home: dict[str, Any] | None) -> dict[str, Any]:
    home = ui_home or {}
    hero = home.get("hero") or {}
    return {
        "research_published": hero.get("research_published_today") or hero.get("research_count") or 0,
        "average_confidence": None,
        "average_evidence": None,
        "research_reviewed": None,
        "research_awaiting_review": hero.get("research_awaiting_review")
        or next(
            (c.get("value") for c in ((home.get("morning_intelligence") or {}).get("cards") or []) if c.get("id") == "research_review"),
            None,
        ),
        "house_views_updated": len(_soft_cms_reviews()),
        "sources": ["ui.home", "rms", "company_monitor"],
    }


def _system_health(ioc: dict[str, Any]) -> dict[str, Any]:
    """IOC integration only — operational health, not research opinions."""
    return {
        "ioc_only": True,
        "providers": ioc.get("providers") or ioc.get("provider_status") or [],
        "apis": ioc.get("components") or ioc.get("checks") or [],
        "cid": "monitored_via_ioc",
        "academy": "monitored_via_ioc",
        "knowledge_foundation": "monitored_via_ioc",
        "financial_intelligence": "monitored_via_ioc",
        "company_monitor": "soft",
        "ask_agi": "soft",
        "response_times": ioc.get("latency") or ioc.get("latencies") or {},
        "failures": ioc.get("alerts") or [],
        "coverage": ioc.get("readiness") or {},
        "freshness": ioc.get("as_of"),
        "overall": ioc.get("status") or ioc.get("overall") or "unknown",
        "dashboard": ioc,
        "sources": ["ioc"],
    }


def _notifications(
    attention: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    coverage: dict[str, Any],
    ioc: dict[str, Any],
) -> list[dict[str, Any]]:
    notes = []
    for a in alerts[:10]:
        notes.append(
            {
                "type": "Critical Alerts" if a.get("significance") == "Critical" else "Research Alerts",
                "ticker": a.get("ticker"),
                "message": a.get("detail") or a.get("change_type"),
                "significance": a.get("significance"),
            }
        )
    for r in reviews[:6]:
        notes.append(
            {
                "type": "House View Review Alerts",
                "ticker": r.get("ticker"),
                "message": r.get("action") or "Suggested House View Review",
                "significance": r.get("max_significance") or "High",
            }
        )
    if int(coverage.get("coverage_pct") or 100) < 60:
        notes.append(
            {
                "type": "Coverage Alerts",
                "message": f"Overall coverage {coverage.get('coverage_pct')}% below institutional comfort",
                "significance": "High",
            }
        )
    if str(ioc.get("status") or ioc.get("overall") or "").lower() in {"degraded", "down", "critical", "fail"}:
        notes.append({"type": "System Alerts", "message": "IOC reports platform attention required", "significance": "Critical"})
    if not notes:
        notes.append(
            {
                "type": "System Alerts",
                "message": "No critical Investment Office alerts — platform monitoring nominal",
                "significance": "Low",
            }
        )
    return notes[:30]


def _copilot(attention: list[dict[str, Any]], queue: list[dict[str, Any]], knowledge: dict[str, Any]) -> dict[str, Any]:
    answers = {
        COPILOT_PROMPTS[0]: (
            f"{len([a for a in attention if a.get('priority') in {'Critical', 'High'}])} companies need High/Critical attention. "
            f"Top: {', '.join(a['ticker'] for a in attention[:5]) or 'none'}."
        ),
        COPILOT_PROMPTS[1]: (
            f"{sum(1 for a in attention if 'Material' in str(a.get('reasons')) or a.get('priority') in {'High', 'Critical'})} "
            f"material monitor signals in the living desk."
        ),
        COPILOT_PROMPTS[2]: "See Portfolio Watch / Sector lenses — private banks, IT deal cycle, staples quality.",
        COPILOT_PROMPTS[3]: (
            f"Research queue has {len(queue)} tasks. First: {(queue[0].get('title') if queue else 'none')}."
        ),
        COPILOT_PROMPTS[4]: "Open Prediction Review — due items and House View reviews are listed on the desk.",
        COPILOT_PROMPTS[5]: (
            f"Academy books learned: {knowledge.get('books_learned')}; concepts: {knowledge.get('concepts_added')}; "
            f"companies monitored: {knowledge.get('companies_updated')}."
        ),
    }
    return {
        "pinned": True,
        "prompts": list(COPILOT_PROMPTS),
        "answers": answers,
        "sources": ["investment_office.aggregate"],
    }


def build_desk(
    *,
    ui_home: dict[str, Any] | None = None,
    ioc_service: Any | None = None,
) -> dict[str, Any]:
    if not is_enabled():
        return {
            "enabled": False,
            "programme": PROGRAMME,
            "version": IO_VERSION,
            "bypassed": True,
        }

    cms = _soft_cms_dashboard()
    changes = _soft_cms_changes(40)
    alerts = _soft_cms_alerts()
    reviews = _soft_cms_reviews()
    books = _soft_academy_books()
    ca_dash = _soft_company_analysis_dash()
    ioc = _soft_ioc(ioc_service)

    attention = _attention_from_cms(changes, reviews, alerts)
    queue = _research_queue(attention, ca_dash) if flag_analyst_queue() or flag_research_queue() else []
    knowledge = _knowledge_growth(books, ca_dash, cms)
    coverage = _coverage_block(cms, books, ioc) if flag_coverage() else {}
    risk = _risk_center(attention, alerts, ioc, coverage) if flag_risk_center() else {}
    brief = _morning_brief(ui_home, ioc) if flag_morning_brief() else {}
    pipeline = _research_pipeline(ui_home)
    preds = _prediction_review(ui_home, reviews)
    portfolio = _portfolio_watch(attention)
    calendar = _calendar(ui_home)
    market = _market_intelligence(ui_home)
    rq = _research_quality(ui_home)
    health = _system_health(ioc)
    notes = _notifications(attention, alerts, reviews, coverage or {"coverage_pct": 70}, ioc)
    copilot = _copilot(attention, queue, knowledge) if flag_executive_copilot() else {}

    research_ideas = [
        {
            "type": "Company Update",
            "title": t.get("title"),
            "ticker": t.get("ticker"),
            "priority": t.get("priority"),
            "basis": ["CMS", "CID", "Company Analysis"],
        }
        for t in queue[:8]
    ]

    desk = {
        "enabled": True,
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IO_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "not_an_engine": True,
        "not_a_recommendation_engine": True,
        "not_portfolio_management": True,
        "flags": flags_dict(),
        "generated_at": _now(),
        "empty_state": False,
        "morning_executive_brief": brief,
        "companies_requiring_attention": attention,
        "todays_research_queue": queue,
        "research_pipeline": pipeline,
        "knowledge_growth": knowledge,
        "prediction_review": preds,
        "coverage_dashboard": coverage,
        "portfolio_watch": portfolio,
        "risk_centre": risk,
        "calendar": calendar,
        "market_intelligence": market,
        "research_quality": rq,
        "system_health": health,
        "executive_copilot": copilot,
        "research_automation": {
            "ideas": research_ideas,
            "types": [
                "Research Ideas",
                "Initiation Reports",
                "Sector Notes",
                "Macro Notes",
                "Valuation Updates",
                "Company Updates",
            ],
            "basis": ["CMS", "CID", "Academy", "Financial Intelligence", "Prediction Tracking"],
        },
        "notifications": notes,
        "answer_policy": "investment_office_operating_cockpit",
    }
    return desk
