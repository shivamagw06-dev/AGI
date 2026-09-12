"""E2E-01 workflow validators — product experience as an institutional user."""

from __future__ import annotations

from typing import Any

from product_experience_validation import probes
from product_experience_validation.schema import (
    FORBIDDEN_UI_JARGON,
    HISTORICAL_CUTOFF,
    LATENCY_TARGETS_MS,
    PRIMARY_TICKER,
    PRODUCT_ENTRY,
    PRODUCT_UI_FILES,
    REQUIRED_COMPANY_TABS,
    REQUIRED_DASHBOARD_MARKERS,
    REQUIRED_MARKETS_MARKERS,
    REQUIRED_NAV,
    REQUIRED_PORTFOLIO_MARKERS,
    REQUIRED_RESEARCH_SECTIONS,
)


def _check(ok: bool, code: str, detail: str) -> dict[str, Any]:
    return {"ok": bool(ok), "code": None if ok else code, "detail": detail}


def wf1_morning_brief() -> dict[str, Any]:
    text = probes.read_text("src/pages/agi/DashboardPage.jsx")
    routes = probes.read_text("src/pages/agi/AgiRoutes.jsx")
    app = probes.read_text("src/App.jsx")
    missing = probes.contains_all(text, REQUIRED_DASHBOARD_MARKERS)
    checks = [
        _check(bool(text), "EMPTY_DASHBOARD", "Dashboard page missing"),
        _check("/agi" in app or 'path="/agi/*"' in app, "BROKEN_NAVIGATION", "App shell missing /agi"),
        _check("DashboardPage" in routes, "BROKEN_NAVIGATION", "Dashboard not routed"),
        _check(not missing, "EMPTY_DASHBOARD", f"Missing dashboard widgets: {missing}"),
        _check("pickMarketStrip" in text or "Global Markets" in text, "EMPTY_DASHBOARD", "Markets strip absent"),
        _check("ComingSoonPage" not in text, "PLACEHOLDER_SURFACE", "Dashboard must not be a placeholder"),
    ]
    return {"workflow": "WF1", "name": "Morning Brief", "checks": checks}


def wf2_company_research() -> dict[str, Any]:
    page = probes.read_text("src/pages/agi/CompanyWorkspacePage.jsx")
    helpers = probes.read_text("src/pages/agi/helpers.js")
    missing_tabs = [t for t in REQUIRED_COMPANY_TABS if t not in helpers and t not in page]
    ws, ms = probes.timed(probes.assemble_company, PRIMARY_TICKER)
    keys = probes.section_keys(ws)
    required_keys = [
        "overview",
        "business_quality",
        "financial_trends",
        "evidence_references",
        "historical_timeline",
        "research_notes",
        "portfolio_references",
        "watchlist_status",
    ]
    missing_keys = [k for k in required_keys if k not in keys]
    overview = probes.board_for(ws, "overview")
    checks = [
        _check(bool(page), "MISSING_SECTION", "Company Workspace page missing"),
        _check("getCompanyWorkspace" in page, "BROKEN_NAVIGATION", "CW API not wired"),
        _check(not missing_tabs, "MISSING_SECTION", f"Missing company tabs: {missing_tabs}"),
        _check(ws.get("ok") is not False, "MISSING_SECTION", "Workspace assemble failed"),
        _check(not missing_keys, "MISSING_SECTION", f"Missing workspace sections: {missing_keys}"),
        _check("coverage" in overview or overview.get("ticker"), "MISSING_SECTION", "Coverage/overview board empty"),
        _check("confidence" in overview, "CONFIDENCE_MISMATCH", "Confidence missing from overview"),
        _check(ms <= LATENCY_TARGETS_MS["company_load"] * 2, "SLOW_PAGE", f"Company load {ms}ms"),
    ]
    return {
        "workflow": "WF2",
        "name": "Company Research",
        "checks": checks,
        "metrics": {"company_load_ms": ms, "sections": keys},
    }


def wf3_evidence_drilldown() -> dict[str, Any]:
    page = probes.read_text("src/pages/agi/CompanyWorkspacePage.jsx")
    ws = probes.assemble_company(PRIMARY_TICKER)
    eids = probes.evidence_ids(ws)
    timeline = probes.board_for(ws, "historical_timeline").get("events") or []
    # Evidence chain: IDs present OR outstanding questions explain gaps (honest unknowns)
    unknowns = probes.board_for(ws, "outstanding_questions").get("questions") or []
    provenance_ok = bool(eids) or bool(unknowns)
    checks = [
        _check("evidence" in page.lower(), "MISSING_EVIDENCE", "Evidence UI absent"),
        _check("getCompanyWorkspaceEvidence" in page or "evidence_references" in page, "BROKEN_PROVENANCE", "Evidence API/tab missing"),
        _check(provenance_ok, "BROKEN_PROVENANCE", "No evidence IDs and no unknowns — provenance broken"),
        _check("Filing" in page or "evidence_id" in page or "Evidence" in page, "MISSING_EVIDENCE", "Filing drill-down affordance missing"),
        _check(isinstance(timeline, list), "TIMELINE_FAILURE", "Timeline board invalid"),
    ]
    return {
        "workflow": "WF3",
        "name": "Evidence Drill-down",
        "checks": checks,
        "metrics": {"evidence_ids": len(eids), "timeline_events": len(timeline)},
    }


def wf4_ask_agi() -> dict[str, Any]:
    page = probes.read_text("src/pages/agi/AskAgiProductPage.jsx")
    company = probes.read_text("src/pages/agi/CompanyWorkspacePage.jsx")
    chat = probes.read_text("src/components/AskAgi/InstitutionalChatWorkspace.jsx")
    checks = [
        _check(bool(page), "BROKEN_CONTEXT", "Ask AGI product page missing"),
        _check("InstitutionalChatWorkspace" in page, "BROKEN_CONTEXT", "Chat workspace not embedded"),
        _check("/agi/ask" in page, "BROKEN_NAVIGATION", "Ask AGI not under /agi/ask"),
        _check("embedded" in page, "BROKEN_CONTEXT", "Ask AGI must embed in product shell"),
        _check("What changed" in page or "ASK_PROMPTS" in page or "confidence" in chat.lower(), "MISSING_RESEARCH", "Ask prompts/confidence absent"),
        _check(
            "ticker" in page or "context" in page or "/agi/ask?q=" in company,
            "CONTEXT_LOST",
            "No company→Ask AGI handoff",
        ),
        _check("AGIB" not in page and "AGIB" not in chat, "ENGINE_JARGON_LEAK", "Legacy AGIB branding in Ask UI"),
    ]
    return {"workflow": "WF4", "name": "Ask AGI", "checks": checks}


def wf5_research() -> dict[str, Any]:
    page = probes.read_text("src/pages/agi/ResearchWorkspacePage.jsx")
    routes = probes.read_text("src/pages/agi/AgiRoutes.jsx")
    missing = probes.contains_all(page, REQUIRED_RESEARCH_SECTIONS)
    checks = [
        _check(bool(page), "MISSING_RESEARCH", "Research workspace page missing"),
        _check("ResearchWorkspacePage" in routes, "BROKEN_NAVIGATION", "Research not routed"),
        _check("ComingSoonPage area=\"research\"" not in routes, "PLACEHOLDER_SURFACE", "Research still a placeholder"),
        _check(not missing, "MISSING_RESEARCH", f"Missing research sections: {missing}"),
        _check("Evidence" in page and "Unknowns" in page, "MISSING_EVIDENCE", "Research evidence/unknowns incomplete"),
    ]
    return {"workflow": "WF5", "name": "Research", "checks": checks}


def wf6_portfolio() -> dict[str, Any]:
    page = probes.read_text("src/pages/agi/PortfolioWorkspacePage.jsx")
    routes = probes.read_text("src/pages/agi/AgiRoutes.jsx")
    missing = probes.contains_all(page, REQUIRED_PORTFOLIO_MARKERS)
    pf = probes.seed_demo_portfolio()
    holdings = pf.get("holdings") or []
    checks = [
        _check(bool(page), "BROKEN_PORTFOLIO", "Portfolio workspace missing"),
        _check("PortfolioWorkspacePage" in routes, "BROKEN_NAVIGATION", "Portfolio not routed"),
        _check("ComingSoonPage area=\"portfolio\"" not in routes, "PLACEHOLDER_SURFACE", "Portfolio still a placeholder"),
        _check(not missing, "BROKEN_PORTFOLIO", f"Missing portfolio panels: {missing}"),
        _check("/agi/companies/" in page, "BROKEN_NAVIGATION", "Holdings must open Company Workspace"),
        _check(len(holdings) >= 1, "BROKEN_PORTFOLIO", "Demo portfolio has no holdings"),
    ]
    return {
        "workflow": "WF6",
        "name": "Portfolio",
        "checks": checks,
        "metrics": {"holdings": len(holdings), "portfolio_id": pf.get("portfolio_id")},
    }


def wf7_markets() -> dict[str, Any]:
    page = probes.read_text("src/pages/agi/MarketsWorkspacePage.jsx")
    routes = probes.read_text("src/pages/agi/AgiRoutes.jsx")
    missing = probes.contains_all(page, REQUIRED_MARKETS_MARKERS)
    checks = [
        _check(bool(page), "BROKEN_NAVIGATION", "Markets workspace missing"),
        _check("MarketsWorkspacePage" in routes, "BROKEN_NAVIGATION", "Markets not routed"),
        _check("ComingSoonPage area=\"markets\"" not in routes, "PLACEHOLDER_SURFACE", "Markets still a placeholder"),
        _check(not missing, "MISSING_SECTION", f"Missing markets panels: {missing}"),
        _check("/agi/research" in page or "/agi/ask" in page or "Research" in page, "BROKEN_NAVIGATION", "Markets→research links missing"),
    ]
    return {"workflow": "WF7", "name": "Markets", "checks": checks}


def wf8_watchlists() -> dict[str, Any]:
    page = probes.read_text("src/pages/agi/WatchlistsWorkspacePage.jsx")
    routes = probes.read_text("src/pages/agi/AgiRoutes.jsx")
    wl = probes.seed_demo_watchlist()
    life, ms = probes.timed(probes.exercise_watchlist_lifecycle, wl.get("watchlist_id") or "agi-research-queue")
    checks = [
        _check(bool(page), "BROKEN_WATCHLIST", "Watchlists workspace missing"),
        _check("WatchlistsWorkspacePage" in routes, "BROKEN_NAVIGATION", "Watchlists not routed"),
        _check("ComingSoonPage area=\"watchlists\"" not in routes, "PLACEHOLDER_SURFACE", "Watchlists still a placeholder"),
        _check("Archived" in page or "archive" in page.lower(), "BROKEN_WATCHLIST", "Archive affordance missing"),
        _check(life.get("added"), "BROKEN_WATCHLIST", "Add company failed"),
        _check(life.get("idempotent_add"), "BROKEN_WATCHLIST", "Duplicate entries allowed"),
        _check(life.get("removed"), "BROKEN_WATCHLIST", "Remove company failed"),
        _check(life.get("no_duplicate"), "BROKEN_WATCHLIST", "Probe ticker left duplicates"),
        _check(ms <= 3000, "SLOW_PAGE", f"Watchlist lifecycle {ms}ms"),
    ]
    return {
        "workflow": "WF8",
        "name": "Watchlists",
        "checks": checks,
        "metrics": {"lifecycle_ms": ms, **{k: life.get(k) for k in ("added", "removed", "idempotent_add")}},
    }


def wf9_context_awareness() -> dict[str, Any]:
    ask = probes.read_text("src/pages/agi/AskAgiProductPage.jsx")
    company = probes.read_text("src/pages/agi/CompanyWorkspacePage.jsx")
    portfolio = probes.read_text("src/pages/agi/PortfolioWorkspacePage.jsx")
    helpers = probes.read_text("src/pages/agi/helpers.js")
    # Company context: Ask link includes ticker; Ask page accepts context/ticker params
    company_ctx = "ticker" in company or "KOTAKBANK" in company or "/agi/ask?q=" in company
    ask_ctx = "context" in ask or "ticker" in ask or "params.get" in ask
    portfolio_ctx = "concern" in portfolio.lower() or "/agi/ask" in portfolio
    checks = [
        _check(company_ctx, "CONTEXT_LOST", "Company Workspace does not hand context to Ask AGI"),
        _check(ask_ctx, "BROKEN_CONTEXT", "Ask AGI does not read company/portfolio context"),
        _check(portfolio_ctx, "BROKEN_CONTEXT", "Portfolio does not supply Ask context"),
        _check("productizeText" in helpers, "ENGINE_JARGON_LEAK", "No productizeText guard for UI copy"),
    ]
    return {"workflow": "WF9", "name": "Context Awareness", "checks": checks}


def wf10_navigation() -> dict[str, Any]:
    helpers = probes.read_text("src/pages/agi/helpers.js")
    routes = probes.read_text("src/pages/agi/AgiRoutes.jsx")
    layout = probes.read_text("src/pages/agi/AgiLayout.jsx")
    missing_nav = [n for n in REQUIRED_NAV if n not in helpers and n not in layout]
    chain = [
        'path="ask"',
        "companies/:ticker",
        'path="research"',
        'path="portfolio"',
        "DashboardPage",
    ]
    missing_routes = [c for c in chain if c not in routes]
    checks = [
        _check(PRODUCT_ENTRY == "/agi", "BROKEN_NAVIGATION", "Product entry must be /agi"),
        _check(not missing_nav, "BROKEN_NAVIGATION", f"Missing nav labels: {missing_nav}"),
        _check(not missing_routes, "BROKEN_NAVIGATION", f"Missing routes: {missing_routes}"),
        _check("NAV_ITEMS" in helpers, "BROKEN_NAVIGATION", "NAV_ITEMS absent"),
        _check("ComingSoonPage" in routes or "WorkspacePage" in routes, "BROKEN_NAVIGATION", "Route table empty"),
        _check("Public site" in layout or 'to="/"' in layout, "BROKEN_NAVIGATION", "Escape hatch to public site missing"),
    ]
    return {"workflow": "WF10", "name": "Navigation", "checks": checks}


def wf11_performance() -> dict[str, Any]:
    _, dash_ms = probes.timed(probes.read_text, "src/pages/agi/DashboardPage.jsx")
    _, company_ms = probes.timed(probes.assemble_company, PRIMARY_TICKER)
    _, evidence_ms = probes.timed(lambda: probes.evidence_ids(probes.assemble_company(PRIMARY_TICKER)))
    metrics = {
        "dashboard_probe_ms": dash_ms,
        "company_load_ms": company_ms,
        "evidence_load_ms": evidence_ms,
    }
    checks = [
        _check(dash_ms <= LATENCY_TARGETS_MS["dashboard_probe"], "SLOW_PAGE", f"Dashboard probe {dash_ms}ms"),
        _check(company_ms <= LATENCY_TARGETS_MS["company_load"], "SLOW_PAGE", f"Company load {company_ms}ms"),
        _check(evidence_ms <= LATENCY_TARGETS_MS["evidence_load"], "SLOW_PAGE", f"Evidence load {evidence_ms}ms"),
    ]
    return {"workflow": "WF11", "name": "Performance", "checks": checks, "metrics": metrics}


def wf12_failure_handling() -> dict[str, Any]:
    result = probes.simulate_failure_handling(PRIMARY_TICKER)
    checks = [
        _check(result["confidence_decreased"], "CONFIDENCE_MISMATCH", "Confidence did not fall with missing coverage"),
        _check(result["unknowns_increased"] or result["missing_identified"], "NO_UNKNOWNS", "Unknowns not surfaced when evidence missing"),
        _check(result["missing_identified"], "MISSING_EVIDENCE", "Missing evidence not identified"),
        _check(result["no_fabricated_conclusions"], "HALLUCINATED_FACT", "Fabricated conclusions detected"),
    ]
    return {"workflow": "WF12", "name": "Failure Handling", "checks": checks, "metrics": result}


def wf13_consistency() -> dict[str, Any]:
    jargon_hits: list[str] = []
    for rel in PRODUCT_UI_FILES:
        text = probes.read_text(rel)
        if not text:
            continue
        # Allow engine IDs only in comments? No — product UI must stay clean.
        hits = probes.find_jargon(text, FORBIDDEN_UI_JARGON)
        for h in hits:
            jargon_hits.append(f"{rel}:{h}")
    helpers = probes.read_text("src/pages/agi/helpers.js")
    checks = [
        _check(not jargon_hits, "ENGINE_JARGON_LEAK", f"Engine jargon in product UI: {jargon_hits[:8]}"),
        _check("productizeText" in helpers, "CONSISTENCY_FAILURE", "productizeText missing"),
        _check("Ask AGI" in helpers, "CONSISTENCY_FAILURE", "Ask AGI label missing from nav"),
        _check("Companies" in helpers and "Portfolio" in helpers, "CONSISTENCY_FAILURE", "Core nav labels incomplete"),
    ]
    return {
        "workflow": "WF13",
        "name": "Consistency",
        "checks": checks,
        "metrics": {"jargon_hits": len(jargon_hits)},
    }


def wf14_historical_blind() -> dict[str, Any]:
    result = probes.ibs_historical_blind(HISTORICAL_CUTOFF)
    checks = [
        _check(result["hidden"] >= 1, "CONSISTENCY_FAILURE", "No future documents hidden by cutoff"),
        _check(result["future_hidden"], "CONSISTENCY_FAILURE", "Future documents leaked past cutoff"),
        _check(result["research_ok"], "MISSING_RESEARCH", "No research under historical blind"),
        _check(result["blind_docs"] >= 1, "MISSING_EVIDENCE", "Blind corpus empty"),
    ]
    return {
        "workflow": "WF14",
        "name": "Historical Blind",
        "checks": checks,
        "metrics": {
            "cutoff": result["cutoff"],
            "hidden": result["hidden"],
            "blind_docs": result["blind_docs"],
            "ibs_score": result.get("score"),
        },
    }


def wf15_benchmark() -> dict[str, Any]:
    result, ms = probes.timed(probes.ibs_kotak_run)
    checks = [
        _check(bool(result.get("passed")), "HALLUCINATED_FACT", f"IBS KOTAK_RBI failed: {result.get('failure_codes')}"),
        _check(result.get("fixture_answers_used") is False, "HALLUCINATED_FACT", "Fixture answers used"),
        _check(result.get("raw_evidence_only") is True, "BROKEN_PROVENANCE", "Not raw-evidence-only"),
        _check(
            bool((result.get("institutional_report") or {}).get("sections", {}).get("outstanding_unknowns")),
            "NO_UNKNOWNS",
            "Benchmark report missing unknowns",
        ),
        _check(ms <= 20000, "SLOW_PAGE", f"IBS run {ms}ms"),
    ]
    return {
        "workflow": "WF15",
        "name": "Benchmark",
        "checks": checks,
        "metrics": {
            "score": result.get("research_quality_score"),
            "elapsed_ms": ms,
            "failure_codes": result.get("failure_codes"),
        },
    }


WORKFLOW_RUNNERS = (
    wf1_morning_brief,
    wf2_company_research,
    wf3_evidence_drilldown,
    wf4_ask_agi,
    wf5_research,
    wf6_portfolio,
    wf7_markets,
    wf8_watchlists,
    wf9_context_awareness,
    wf10_navigation,
    wf11_performance,
    wf12_failure_handling,
    wf13_consistency,
    wf14_historical_blind,
    wf15_benchmark,
)
