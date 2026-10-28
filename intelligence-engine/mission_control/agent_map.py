"""AGIB Agent Map — Mission Control inventory of agents + working status.

Read-only diagnostics. Never modifies research / house views / recommendations.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Callable

AGENT_MAP_VERSION = "agent-map-v1.0.0"


def _env_truthy(name: str, default: str = "false") -> bool:
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_falsey(name: str, default: str = "false") -> bool:
    return not _env_truthy(name, default)


def _soft(fn: Callable[[], Any], default: Any = None) -> Any:
    try:
        return fn()
    except Exception:
        return default


def _probe_import(module: str, attr: str | None = None) -> tuple[bool, str | None]:
    try:
        mod = __import__(module, fromlist=[attr] if attr else ["__name__"])
        if attr:
            getattr(mod, attr)
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:160]


def _probe_health(module: str, fn_name: str = "health") -> tuple[str, dict[str, Any]]:
    ok, err = _probe_import(module, fn_name)
    if not ok:
        return "off", {"error": err or "import_failed"}
    try:
        mod = __import__(module, fromlist=[fn_name])
        body = getattr(mod, fn_name)()
        if not isinstance(body, dict):
            return "soft", {"probe": "non_dict"}
        status = str(body.get("status") or "").lower()
        if body.get("enabled") is False or status in {"disabled", "offline"}:
            return "off", body
        if status in {"ok", "healthy", "ready", "live"}:
            return "working", body
        if status in {"soft", "partial", "degraded", "warning"}:
            return "soft", body
        return "soft", body
    except Exception as exc:  # noqa: BLE001
        return "degraded", {"error": str(exc)[:160]}


def _registry_agents() -> list[str]:
    return _soft(
        lambda: list(
            __import__("app.agents.registry", fromlist=["list_agents"]).list_agents()  # type: ignore[attr-defined]
        ),
        [],
    ) or _soft(
        lambda: list(
            getattr(
                __import__("app.agents.registry", fromlist=["_REGISTRY"]),
                "_REGISTRY",
                {},
            ).keys()
        ),
        [],
    )


def _cio_status(agent_id: str) -> str:
    registered = set(_registry_agents() or [])
    # Ensure bootstrap ran
    if not registered:
        _soft(
            lambda: __import__(
                "app.agents.registry", fromlist=["bootstrap_registry"]
            ).bootstrap_registry()
        )
        registered = set(_registry_agents() or [])
    if agent_id in registered:
        return "working"
    # Source files present?
    path_map = {
        "macro_economist": "app.agents.cio_desk.macro_economist",
        "news_analyst": "app.agents.cio_desk.news_analyst",
        "market_analyst": "app.agents.cio_desk.market_analyst",
        "risk_manager": "app.agents.cio_desk.risk_manager",
        "cio": "app.agents.cio_synthesizer",
        "smoke_analyst": "app.agents.stubs",
    }
    mod = path_map.get(agent_id)
    if mod and _probe_import(mod)[0]:
        return "soft"
    return "orphan"


def _flag_status(enabled: bool, *, soft_when_on: bool = False) -> str:
    if not enabled:
        return "off"
    return "soft" if soft_when_on else "working"


# Catalog: static responsibilities + sources; status resolved at runtime.
_CATALOG: list[dict[str, Any]] = [
    # —— CIO desk ——
    {
        "id": "macro_economist",
        "name": "Macro Economist",
        "group": "cio_desk",
        "responsibility": "India macro transmission from the morning briefing cache.",
        "sources": ["AGIB macro briefing cache"],
        "kind": "cio_agent",
    },
    {
        "id": "news_analyst",
        "name": "News Analyst",
        "group": "cio_desk",
        "responsibility": "Explain why overnight news matters for the desk.",
        "sources": ["Market briefing", "Pre-market briefing"],
        "kind": "cio_agent",
    },
    {
        "id": "market_analyst",
        "name": "Market Analyst",
        "group": "cio_desk",
        "responsibility": "Overnight / global market tone for the CIO desk.",
        "sources": ["Pre-market briefing"],
        "kind": "cio_agent",
    },
    {
        "id": "risk_manager",
        "name": "Risk Manager",
        "group": "cio_desk",
        "responsibility": "Invalidators and scenario risks for the morning desk.",
        "sources": ["Macro risks", "Pre-market scenarios"],
        "kind": "cio_agent",
    },
    {
        "id": "cio",
        "name": "Chief Investment Officer",
        "group": "cio_desk",
        "responsibility": "Synthesize desk agent outputs into an institutional thesis.",
        "sources": ["Peer CIO-desk agent outputs", "LLM synthesizer"],
        "kind": "cio_agent",
    },
    {
        "id": "smoke_analyst",
        "name": "Smoke Analyst",
        "group": "cio_desk",
        "responsibility": "Pipeline smoke probe with cited evidence.",
        "sources": ["AGIB macro briefing cache"],
        "kind": "cio_agent",
    },
    # —— IAF specialists ——
    {
        "id": "iaf_business",
        "name": "Business Analyst",
        "group": "institutional_analysts",
        "responsibility": "Franchise quality and durable competitive advantages.",
        "sources": ["Company Analysis", "Academy", "Annual reports"],
        "kind": "iaf",
        "module": "institutional_analysts.production",
    },
    {
        "id": "iaf_financial",
        "name": "Financial Analyst",
        "group": "institutional_analysts",
        "responsibility": "Earnings quality, cash generation, balance-sheet resilience.",
        "sources": ["Financial Intelligence", "Data Validation & Consensus"],
        "kind": "iaf",
        "module": "institutional_analysts.production",
    },
    {
        "id": "iaf_valuation",
        "name": "Valuation Analyst",
        "group": "institutional_analysts",
        "responsibility": "Whether expectations already priced in look expensive or cheap.",
        "sources": ["Valuation engine", "Financial Intelligence", "Market pack"],
        "kind": "iaf",
        "module": "institutional_analysts.production",
    },
    {
        "id": "iaf_market",
        "name": "Market Specialist",
        "group": "institutional_analysts",
        "responsibility": "Price, volume and liquidity signals for the name.",
        "sources": ["Market tape", "Company dossier", "Live market pack"],
        "kind": "iaf",
        "module": "institutional_analysts.production",
    },
    {
        "id": "iaf_sector",
        "name": "Sector Specialist",
        "group": "institutional_analysts",
        "responsibility": "Industry attractiveness and competitive structure.",
        "sources": ["Sector Intelligence", "Knowledge Factory", "Academy"],
        "kind": "iaf",
        "module": "institutional_analysts.production",
    },
    {
        "id": "iaf_macro",
        "name": "Macro Specialist",
        "group": "institutional_analysts",
        "responsibility": "Rates, inflation and growth transmission to the company.",
        "sources": ["Macro briefing", "Policy series"],
        "kind": "iaf",
        "module": "institutional_analysts.production",
    },
    {
        "id": "iaf_risk",
        "name": "Risk Specialist",
        "group": "institutional_analysts",
        "responsibility": "What can impair the thesis before the base case arrives.",
        "sources": ["Company Monitor", "Risk models"],
        "kind": "iaf",
        "module": "institutional_analysts.production",
    },
    {
        "id": "iaf_management",
        "name": "Management Specialist",
        "group": "institutional_analysts",
        "responsibility": "Governance quality and capital-allocation trust.",
        "sources": ["Annual reports", "Earnings calls", "IR decks"],
        "kind": "iaf",
        "module": "institutional_analysts.production",
    },
    {
        "id": "iaf_ownership",
        "name": "Ownership Specialist",
        "group": "institutional_analysts",
        "responsibility": "Promoter, FI and insider alignment.",
        "sources": ["Shareholding data", "Company dossier"],
        "kind": "iaf",
        "module": "institutional_analysts.production",
    },
    {
        "id": "iaf_committee",
        "name": "Investment Committee",
        "group": "institutional_analysts",
        "responsibility": "Consensus, conflicts, votes and committee minutes.",
        "sources": ["Specialist opinions"],
        "kind": "iaf",
        "module": "institutional_analysts.production",
    },
    {
        "id": "iaf_cio_editor",
        "name": "IAF CIO Editor",
        "group": "institutional_analysts",
        "responsibility": "Institutional prose from the committee package.",
        "sources": ["Committee package"],
        "kind": "iaf",
        "module": "institutional_analysts.production",
    },
    # —— Acquisition / gather ——
    {
        "id": "faa",
        "name": "Finance Acquisition Agent",
        "group": "acquisition",
        "responsibility": "Discover → fetch → process → index public finance evidence into FRE.",
        "sources": [
            "Exa",
            "Firecrawl",
            "Browserbase",
            "Tavily",
            "Playwright",
            "NSE",
            "BSE",
            "SEBI",
            "RBI",
            "MCA",
            "PIB",
            "Company IR",
            "RSS/news",
        ],
        "kind": "faa",
    },
    {
        "id": "faa_background_collector",
        "name": "FAA Background Collector",
        "group": "acquisition",
        "responsibility": "Periodic FAA snapshot refresh off the Ask path.",
        "sources": ["FAA connectors"],
        "kind": "faa_bg",
    },
    {
        "id": "acquisition_planner",
        "name": "Acquisition & API Planner",
        "group": "acquisition",
        "responsibility": "Plans what evidence to fetch; does not collect itself.",
        "sources": ["Provider catalog", "Cache policy"],
        "kind": "planner",
        "module": "acquisition_planner.production",
    },
    # —— LIDI collectors ——
    {
        "id": "lidi_nse_bhavcopy",
        "name": "LIDI · NSE Bhavcopy",
        "group": "live_collectors",
        "responsibility": "Daily NSE prices and volumes.",
        "sources": ["NSE bhavcopy"],
        "kind": "lidi",
        "module": "live_data.collectors.nse_bhavcopy",
    },
    {
        "id": "lidi_nse_announcements",
        "name": "LIDI · NSE Announcements",
        "group": "live_collectors",
        "responsibility": "Corporate announcements from NSE.",
        "sources": ["NSE announcements"],
        "kind": "lidi",
        "module": "live_data.collectors.nse_announcements",
    },
    {
        "id": "lidi_bse_corporate_actions",
        "name": "LIDI · BSE Corporate Actions",
        "group": "live_collectors",
        "responsibility": "Splits, bonus and dividend actions from BSE.",
        "sources": ["BSE corporate actions"],
        "kind": "lidi",
        "module": "live_data.collectors.bse_corporate_actions",
    },
    {
        "id": "lidi_rbi_dbie",
        "name": "LIDI · RBI DBIE",
        "group": "live_collectors",
        "responsibility": "Repo, liquidity and macro series from RBI DBIE.",
        "sources": ["RBI DBIE"],
        "kind": "lidi",
        "module": "live_data.collectors.rbi_dbie",
    },
    {
        "id": "lidi_company_ir",
        "name": "LIDI · Company IR",
        "group": "live_collectors",
        "responsibility": "Company IR filings and guidance pages.",
        "sources": ["Company IR websites"],
        "kind": "lidi",
        "module": "live_data.collectors.company_ir",
    },
    # —— KF source clients ——
    {
        "id": "kf_yahoo",
        "name": "KF Yahoo Client",
        "group": "knowledge_factory",
        "responsibility": "Company/market history for Knowledge Factory (fixture-first).",
        "sources": ["Yahoo Finance", "KF fixtures"],
        "kind": "kf_client",
        "module": "knowledge_factory.collectors.yahoo.client",
    },
    {
        "id": "kf_groww",
        "name": "KF Groww Client",
        "group": "knowledge_factory",
        "responsibility": "India market series for Knowledge Factory.",
        "sources": ["Groww", "KF fixtures"],
        "kind": "kf_client",
        "module": "knowledge_factory.collectors.groww.client",
    },
    {
        "id": "kf_nse",
        "name": "KF NSE Client",
        "group": "knowledge_factory",
        "responsibility": "NSE series into Knowledge Factory.",
        "sources": ["NSE", "KF fixtures"],
        "kind": "kf_client",
        "module": "knowledge_factory.collectors.nse.client",
    },
    {
        "id": "kf_bse",
        "name": "KF BSE Client",
        "group": "knowledge_factory",
        "responsibility": "BSE series into Knowledge Factory.",
        "sources": ["BSE", "KF fixtures"],
        "kind": "kf_client",
        "module": "knowledge_factory.collectors.bse.client",
    },
    {
        "id": "kf_rbi",
        "name": "KF RBI Client",
        "group": "knowledge_factory",
        "responsibility": "RBI macro into Knowledge Factory.",
        "sources": ["RBI", "KF fixtures"],
        "kind": "kf_client",
        "module": "knowledge_factory.collectors.rbi.client",
    },
    {
        "id": "kf_fred",
        "name": "KF FRED Client",
        "group": "knowledge_factory",
        "responsibility": "Global macro series from FRED.",
        "sources": ["FRED", "KF fixtures"],
        "kind": "kf_client",
        "module": "knowledge_factory.collectors.fred.client",
    },
    {
        "id": "kf_world_bank",
        "name": "KF World Bank Client",
        "group": "knowledge_factory",
        "responsibility": "World Bank macro indicators.",
        "sources": ["World Bank", "KF fixtures"],
        "kind": "kf_client",
        "module": "knowledge_factory.collectors.world_bank.client",
    },
    # —— Offices ——
    {
        "id": "research_office",
        "name": "Research Office",
        "group": "offices",
        "responsibility": "Knowledge-only morning research desk / publications.",
        "sources": ["Knowledge Factory", "Institutional Scheduler"],
        "kind": "office",
        "module": "research_office.production",
    },
    {
        "id": "investment_office",
        "name": "Investment Office",
        "group": "offices",
        "responsibility": (
            "Executive operating cockpit — briefs, queues, coverage; "
            "IO-01 orchestrates FIRE-01…06 into Institutional Research Packages (no new analysis)."
        ),
        "sources": [
            "CMS",
            "CIO desks",
            "AGIB caches",
            "FIRE-01",
            "FIRE-02",
            "FIRE-03",
            "FIRE-04",
            "FIRE-05",
            "FIRE-06",
            "FKB",
        ],
        "kind": "office",
        "module": "investment_office.production",
    },
    {
        "id": "investment_office_irp",
        "name": "Investment Office IRP (IO-01)",
        "group": "ops",
        "responsibility": (
            "Question routing + research package assembly from existing FIRE evidence — "
            "never recalculates, rescores, or invents conclusions (no BUY/SELL)."
        ),
        "sources": [
            "Financial Warehouse",
            "Derived Metrics",
            "FIRE-01",
            "FIRE-02",
            "FIRE-03",
            "FIRE-04",
            "FIRE-05",
            "FIRE-06",
            "FKB",
        ],
        "kind": "office",
        "module": "investment_office.production",
    },
    {
        "id": "comparative_intelligence",
        "name": "Comparative Intelligence (CIO-01)",
        "group": "ops",
        "responsibility": (
            "Cross-company side-by-side Institutional Comparison Reports from existing FIRE "
            "outputs — comparison only; never recalculates or invents conclusions (no BUY/SELL)."
        ),
        "sources": [
            "FIRE-01",
            "FIRE-02",
            "FIRE-03",
            "FIRE-04",
            "FIRE-05",
            "FIRE-06",
            "IO-01 collectors",
            "FKB",
        ],
        "kind": "office",
        "module": "comparative_intelligence.production",
    },
    {
        "id": "office_sdk",
        "name": "Office SDK (shared contract)",
        "group": "ops",
        "responsibility": (
            "Shared OfficeRequest / OfficeResponse / EvidenceBlock contracts for Research, "
            "Portfolio, Market, Execution, and Knowledge domain offices."
        ),
        "sources": ["IO-01", "CIO-01", "PO-01", "WO-01", "future SO/VO/ITO"],
        "kind": "office",
        "module": "office_sdk.production",
    },
    {
        "id": "portfolio_office",
        "name": "Portfolio Office (PO-01)",
        "group": "ops",
        "responsibility": (
            "Canonical portfolio state — holdings, cash, exposures, quality/execution "
            "distributions from FIRE-05/06, concentration, immutable snapshots (no BUY/SELL)."
        ),
        "sources": ["Office SDK", "FIRE-05", "FIRE-06", "holdings", "company master"],
        "kind": "office",
        "module": "portfolio_office.production",
    },
    {
        "id": "platform_event_bus",
        "name": "Platform Event Bus (PEB-01)",
        "group": "ops",
        "responsibility": (
            "In-process typed pub/sub for loose coupling between offices — "
            "no business logic, no persistence, no broker (infrastructure only)."
        ),
        "sources": ["IO-01", "CIO-01", "PO-01", "WO-01", "Office SDK", "future Alerts/Monitoring"],
        "kind": "platform",
        "module": "platform_event_bus.production",
    },
    {
        "id": "watchlist_office",
        "name": "Watchlist Office (WO-01)",
        "group": "ops",
        "responsibility": (
            "Research-queue watchlists — publishes add/remove events and subscribes to "
            "research/quality/execution/comparison events (no research, no BUY/SELL)."
        ),
        "sources": ["Office SDK", "PEB-01", "IO-01 references", "FIRE references"],
        "kind": "office",
        "module": "watchlist_office.production",
    },
    {
        "id": "company_workspace",
        "name": "Company Workspace (CW-01)",
        "group": "ops",
        "responsibility": (
            "Primary company UX — assembles FIRE/IO/WO/PO into one workspace with provenance; "
            "never runs analysis, never BUY/SELL."
        ),
        "sources": [
            "FIRE-01",
            "FIRE-02",
            "FIRE-03",
            "FIRE-04",
            "FIRE-05",
            "FIRE-06",
            "IO-01",
            "WO-01",
            "PO-01",
            "Office SDK",
            "PEB-01",
        ],
        "kind": "ux_surface",
        "module": "company_workspace.production",
    },
    {
        "id": "institutional_stress_tests",
        "name": "Institutional Stress Tests (IST-01/IST-02)",
        "group": "ops",
        "responsibility": (
            "IST-01: orchestration exams (no single-module pass). "
            "IST-02: raw-evidence research validation (no fixture answers)."
        ),
        "sources": [
            "FSE",
            "FIL",
            "FIRE-01…06",
            "CIO-01",
            "WO-01",
            "CW-01",
            "Ask AGI",
            "raw corpus",
        ],
        "kind": "evaluation",
        "module": "institutional_stress_tests.production",
    },
    {
        "id": "institutional_benchmarks",
        "name": "AGI Institutional Benchmark Suite (IBS-01)",
        "group": "ops",
        "responsibility": (
            "Permanent multi-sector raw-evidence benchmarks for the AGI Intelligence Core — "
            "pytest for intelligence; release gates on score/hallucination/provenance/consistency."
        ),
        "sources": [
            "raw corpora",
            "FIRE-01…06",
            "IO-01",
            "CIO-01",
            "CW-01",
            "IST-02 pipeline",
        ],
        "kind": "evaluation",
        "module": "institutional_benchmarks.production",
    },
    {
        "id": "product_experience_validation",
        "name": "Institutional Product Experience Validation (E2E-01)",
        "group": "ops",
        "responsibility": (
            "End-to-end validation of the AGI product experience — Dashboard, Companies, Ask AGI, "
            "Research, Portfolio, Markets, Watchlists — as a real institutional user. Not an engine."
        ),
        "sources": [
            "Phase 2 /agi UI",
            "CW-01",
            "Ask AGI",
            "PO-01",
            "WO-01",
            "IBS-01",
        ],
        "kind": "evaluation",
        "module": "product_experience_validation.production",
    },
    {
        "id": "release_health",
        "name": "AGI Release Health (RH-01)",
        "group": "ops",
        "responsibility": (
            "Single release-gate dashboard: Build · Unit · Integration · IST · IBS · E2E · "
            "hallucinations · provenance · regression · Ready for Release."
        ),
        "sources": ["IST-01/02", "IBS-01", "E2E-01", "pytest", "product UI"],
        "kind": "evaluation",
        "module": "release_health.production",
    },
    {
        "id": "institutional_reporting",
        "name": "Institutional Reporting Engine (IRE-02)",
        "group": "publication",
        "responsibility": (
            "Deterministic Reason Composer + Company Recommendation Reports — "
            "Facts → Reasons → Decision → Report. No Gemini, no GPT, no external writer."
        ),
        "sources": [
            "InstitutionalReportInput facts",
            "Reason objects",
            "IDS-01 InstitutionalDecision",
            "FIRE evidence IDs",
            "Ask AGI",
        ],
        "kind": "reporting",
        "module": "institutional_reporting.production",
    },
    {
        "id": "institutional_decision",
        "name": "Institutional Decision System (IDS-01)",
        "group": "publication",
        "responsibility": (
            "Owns BUY/HOLD/SELL as a versioned InstitutionalDecision — "
            "reports only render the decision. Deterministic, no LLM."
        ),
        "sources": ["Reason graph", "Valuation", "Risk", "Business/Financial quality"],
        "kind": "decision",
        "module": "institutional_decision.production",
    },
    {
        "id": "institutional_calibration",
        "name": "Decision Calibration & Explainability (IDS-02)",
        "group": "publication",
        "responsibility": (
            "Computes calibrated confidence from a versioned CalibrationProfile — "
            "scorecard, contributors, drift, and full evidence lineage. No LLM."
        ),
        "sources": ["InstitutionalDecision", "Reason graph", "Evidence snapshot", "CalibrationProfile"],
        "kind": "decision",
        "module": "institutional_calibration.production",
    },
    {
        "id": "institutional_graph",
        "name": "Institutional Knowledge Graph (KG-01)",
        "group": "publication",
        "responsibility": (
            "Single-company knowledge graph connecting evidence, metrics, risks, "
            "reasons, decisions and calibration — deterministic inference & impact. No LLM."
        ),
        "sources": [
            "InstitutionalReportInput",
            "Reason graph",
            "InstitutionalDecision",
            "Calibration",
        ],
        "kind": "knowledge",
        "module": "institutional_graph.production",
    },
    {
        "id": "institutional_forecasting",
        "name": "Forecast & Scenario Graph (FG-01)",
        "group": "publication",
        "responsibility": (
            "Deterministic scenario propagation through the company knowledge graph — "
            "explicit assumptions, probabilities, sensitivity, decision evolution. No ML/LLM."
        ),
        "sources": ["InstitutionalKnowledgeGraph", "ScenarioAssumption", "InstitutionalDecision"],
        "kind": "forecast",
        "module": "institutional_forecasting.production",
    },
    {
        "id": "institutional_observation",
        "name": "Institutional Observation Engine (IO-01)",
        "group": "publication",
        "responsibility": (
            "Proactive institutional monitoring — detect material changes with hysteresis, "
            "classify significance, re-evaluate decisions when required, emit structured "
            "observations with full lineage. No LLM."
        ),
        "sources": [
            "Evidence snapshots",
            "Knowledge graph",
            "InstitutionalDecision",
            "Forecasts",
            "Watchlists",
        ],
        "kind": "observation",
        "module": "institutional_observation.production",
    },

    {
        "id": "institutional_portfolio",
        "name": "Portfolio Knowledge Graph (PKG-01 / PO-01)",
        "group": "publication",
        "responsibility": (
            "Phase 4.1 — Portfolio → Companies → Relationships. Builds InstitutionalPortfolio "
            "with allocations, exposures, concentration, and correlation proxies. "
            "Distinct from portfolio_office holdings state. No LLM / no optimisation."
        ),
        "sources": [
            "Holdings",
            "Company knowledge graphs",
            "InstitutionalDecision",
            "portfolio_office (optional)",
        ],
        "kind": "portfolio_intelligence",
        "module": "institutional_portfolio.production",
    },
    {
        "id": "institutional_portfolio_risk",
        "name": "Institutional Portfolio Risk Engine (PRE-01)",
        "group": "publication",
        "responsibility": (
            "Phase 4.3 — Authoritative InstitutionalPortfolioRisk from portfolio graph. "
            "Concentration, liquidity, correlation proxies, factor exposure, deterministic stress. "
            "Consumed by PCE-01 and CIO-01. No Monte Carlo / VaR / optimisation."
        ),
        "sources": [
            "InstitutionalPortfolio",
            "Holdings",
            "Exposures",
            "Company decisions (lineage)",
        ],
        "kind": "portfolio_risk",
        "module": "institutional_portfolio_risk.production",
    },
    {
        "id": "institutional_policy",
        "name": "Institutional Policy & Constraint Engine (PCE-01)",
        "group": "publication",
        "responsibility": (
            "Phase 4.4 — Deterministic mandate compliance. InstitutionalPolicyAssessment with "
            "position/sector/cash/diversification/liquidity/risk constraints. Consumed by CIO-01. "
            "No optimisation / no LLM."
        ),
        "sources": [
            "InstitutionalPortfolio",
            "InstitutionalPortfolioRisk (PRE-01)",
            "Policy profiles / mandates",
        ],
        "kind": "portfolio_policy",
        "module": "institutional_policy.production",
    },
    {
        "id": "institutional_portfolio_decision",
        "name": "Institutional Portfolio Decision System (CIO-01)",
        "group": "publication",
        "responsibility": (
            "Phase 4.2 — Deterministic InstitutionalPortfolioDecision from portfolio graph + "
            "PRE-01 risk + PCE-01 policy + referential company decisions. Allocation/exposure "
            "actions, portfolio calibration, monitoring plan. Never mutates company decisions."
        ),
        "sources": [
            "InstitutionalPortfolio",
            "InstitutionalPortfolioRisk (PRE-01)",
            "InstitutionalPolicyAssessment (PCE-01)",
            "Company InstitutionalDecision (referential)",
            "Exposures",
        ],
        "kind": "portfolio_decision",
        "module": "institutional_portfolio_decision.production",
    },
    {
        "id": "institutional_committee",
        "name": "Investment Committee Engine (ICE-01)",
        "group": "publication",
        "responsibility": (
            "Phase 4.5 — Deterministic InstitutionalCommitteeResolution governing CIO-01 decisions. "
            "Structured desk votes, agenda, action items, follow-ups. Never mutates risk, policy, "
            "or company decisions. Not predictive."
        ),
        "sources": [
            "InstitutionalPortfolioDecision (CIO-01)",
            "InstitutionalPortfolioRisk (PRE-01)",
            "InstitutionalPolicyAssessment (PCE-01)",
        ],
        "kind": "committee_governance",
        "module": "institutional_committee.production",
    },
    {
        "id": "institutional_orchestrator",
        "name": "Universal Ask AGI Orchestrator (UAG-01)",
        "group": "publication",
        "responsibility": (
            "Phase 5.1 — Stateless orchestration over registered institutional objects. "
            "Intent → plan → retrieve → assemble. Does not generate recommendations or own "
            "business state. Domain engines remain systems of record."
        ),
        "sources": [
            "Object Registry",
            "CompanyDecision",
            "PortfolioRisk",
            "PolicyAssessment",
            "PortfolioDecision",
            "CommitteeResolution",
        ],
        "kind": "orchestration",
        "module": "institutional_orchestrator.production",
    },
    {
        "id": "institutional_workspace",
        "name": "Institutional Research Workspace (RW-01)",
        "group": "publication",
        "responsibility": (
            "Phase 5.2 — Analyst workstation over linked institutional objects. Timeline, "
            "evidence browser, linked navigation, and research notes. Presentation only — "
            "does not mutate system intelligence. Ask AGI is the entry; workspace is primary."
        ),
        "sources": [
            "CompanyDecision",
            "PortfolioRisk",
            "PolicyAssessment",
            "PortfolioDecision",
            "CommitteeResolution",
            "Evidence",
            "ResearchNotes",
        ],
        "kind": "research_workspace",
        "module": "institutional_workspace.production",
    },
    {
        "id": "institutional_cross_company",
        "name": "Cross-Company Intelligence (CCI-01)",
        "group": "publication",
        "responsibility": (
            "Phase 5.3 — Relationship reasoning and dependency propagation over KG-01. "
            "Does not own or duplicate the graph. Provider registry for competitor, sector, "
            "macro, and portfolio relationships. Not predictive."
        ),
        "sources": [
            "KG-01 Institutional Knowledge Graph",
            "Peer Intelligence",
            "PKG-01 Portfolio Graph",
            "Macro dependency map",
        ],
        "kind": "cross_company_intelligence",
        "module": "institutional_cross_company.production",
    },
    {
        "id": "institutional_publishing",
        "name": "Publishing & Distribution (PUB-01)",
        "group": "publication",
        "responsibility": (
            "Phase 5.4 — Compose institutional deliverables from immutable objects. "
            "Never analyzes or invents recommendations. Templates format; manifests audit. "
            "Distribution decoupled from builders."
        ),
        "sources": [
            "CompanyDecision",
            "PortfolioRisk",
            "PolicyAssessment",
            "PortfolioDecision",
            "CommitteeResolution",
            "Observation",
            "Evidence",
        ],
        "kind": "publishing",
        "module": "institutional_publishing.production",
    },
    {
        "id": "institutional_multi_portfolio",
        "name": "Multi-Portfolio & Client Platform (MPC-01)",
        "group": "publication",
        "responsibility": (
            "Phase 5.5 — Tenancy and workflow for multiple portfolios, clients, and teams. "
            "Intelligence remains global; mandates, permissions, and workspaces are local. "
            "Explicit InstitutionalExecutionContext flows through orchestration."
        ),
        "sources": [
            "Portfolio registry",
            "Client registry",
            "Mandate → PCE policy profile",
            "Role permissions",
            "Workspace resolver",
        ],
        "kind": "multi_portfolio_platform",
        "module": "institutional_multi_portfolio.production",
    },
    {
        "id": "institutional_performance",
        "name": "Performance & Scale (PRP-01)",
        "group": "platform",
        "responsibility": (
            "Production Readiness Programme — distributed cache, query/workspace caches, "
            "parallel orchestration, async publication jobs, incremental graph updates, "
            "streaming, and Performance Center metrics. No new intelligence engines."
        ),
        "sources": [
            "Redis / in-memory cache",
            "Background job queue",
            "Latency samples",
            "UAG / RW / PUB soft hooks",
        ],
        "kind": "production_readiness",
        "module": "institutional_performance.production",
    },
    {
        "id": "institutional_security",
        "name": "Security & Governance (PRP-02)",
        "group": "platform",
        "responsibility": (
            "Production Readiness Programme — authentication, RBAC authorization, tenant "
            "isolation, API keys, sessions, immutable audit, encryption helpers, and "
            "Security Center. Wraps the platform; never enters the intelligence layer."
        ),
        "sources": [
            "InstitutionalSecurityContext",
            "InstitutionalAuditEvent",
            "Session / API key stores",
            "Correlation ID",
            "Security Gateway",
        ],
        "kind": "production_readiness",
        "module": "institutional_security.production",
    },
    {
        "id": "institutional_observability",
        "name": "Observability & Operations (PRP-03)",
        "group": "platform",
        "responsibility": (
            "Production Readiness Programme — distributed tracing, metrics, structured logs, "
            "health checks, alerting, dependency monitoring, and Operations Center. "
            "Explains platform behavior; never changes it. Complements Execution + Security contexts."
        ),
        "sources": [
            "InstitutionalObservabilityContext",
            "InstitutionalTrace / Metric / Health",
            "Correlation ID (PRP-02)",
            "Performance + Security gauges",
        ],
        "kind": "production_readiness",
        "module": "institutional_observability.production",
    },
    {
        "id": "institutional_architecture",
        "name": "Architecture Conformance (RC-01)",
        "group": "platform",
        "responsibility": (
            "Release Candidate quality gate — invariants, forbidden dependency rules, "
            "lineage validation, context propagation, publication/UAG gates, and "
            "Architecture Center. Not a feature; proves AGIB v1.0 principles hold."
        ),
        "sources": [
            "Ownership registry",
            "Import graph",
            "Canonical lineage",
            "Execution / Security / Observability contexts",
        ],
        "kind": "release_candidate",
        "module": "institutional_architecture.production",
    },
    {
        "id": "institutional_launch",
        "name": "Launch Phase (L-01)",
        "group": "platform",
        "responsibility": (
            "Post-GA usage validation — journey analytics, product metrics, feedback, "
            "operational SLAs, v1.1 feature flags (gated), and Launch Center. "
            "Driven by usage, not architecture expansion."
        ),
        "sources": [
            "Journey funnel",
            "Adoption metrics",
            "User feedback",
            "SLA targets",
            "Feature flag registry",
        ],
        "kind": "launch_validation",
        "module": "institutional_launch.production",
    },
    {
        "id": "institutional_acceptance",
        "name": "Production Acceptance Test (PAT-01)",
        "group": "platform",
        "responsibility": (
            "Break AGIB before onboarding users — 15-phase end-to-end production "
            "acceptance (boot→data→KG→intelligence→Ask→workspace→publish→security→"
            "performance→observability→RC-01→failure→workflow→stability). "
            "Certification gate; no new intelligence engines."
        ),
        "sources": [
            "Phase scenarios",
            "Stress runner",
            "Failure injection",
            "Analyst workflow",
            "RC-01 conformance",
            "Certification report",
        ],
        "kind": "production_acceptance",
        "module": "institutional_acceptance.production",
    },
    {
        "id": "institutional_evidence",
        "name": "Institutional Evidence Platform (IEP-01)",
        "group": "evidence",
        "responsibility": (
            "AGI v1.1.2 Knowledge OS — validates, versions, and preserves canonical "
            "knowledge produced by KIL from CGL. Durable institutional knowledge; "
            "intelligence engines are consumers."
        ),
        "sources": [
            "Knowledge Integration Layer",
            "Canonical domain models",
            "Evidence quality engine",
            "Evidence registry / graph / claims",
            "Company memory + timeline",
            "Decision eligibility",
            "Research lifecycle",
        ],
        "kind": "institutional_knowledge_os",
        "module": "institutional_evidence.production",
    },
    {
        "id": "knowledge_integration_layer",
        "name": "Knowledge Integration Layer (KIL-01)",
        "group": "evidence",
        "responsibility": (
            "AGI v1.1.2 bridge — CGL gathers; KIL transforms into canonical evidence, "
            "refreshes Company Memory, versions knowledge, invalidates stale research, "
            "and feeds IEP. One institutional knowledge pipeline. Nifty 500 expansion "
            "gated until Top-20 Institutional Coverage Complete."
        ),
        "sources": [
            "Continuous Gather → Learn",
            "Knowledge Factory Historical Depth",
            "Immutable CGL events",
            "Knowledge Snapshots",
            "Knowledge Confidence",
            "Coverage states",
            "Automatic repair",
        ],
        "kind": "knowledge_integration",
        "module": "institutional_evidence.integration.layer",
    },
    {
        "id": "ite_thesis",
        "name": "Investment Thesis Office",
        "group": "offices",
        "responsibility": "Why is this interesting? (ITE).",
        "sources": ["Research packages"],
        "kind": "v4_office",
        "module": "institutional_investment_thesis.production",
        "ask_flag": "AGI_V4_OFFICES_IN_ASK",
    },
    {
        "id": "ido_decision",
        "name": "Decision Office",
        "group": "offices",
        "responsibility": "Governance framing for institutional action (IDO).",
        "sources": ["Thesis", "Committee"],
        "kind": "v4_office",
        "module": "institutional_decision_office.production",
        "ask_flag": "AGI_V4_OFFICES_IN_ASK",
    },
    {
        "id": "ipo_portfolio",
        "name": "Portfolio Office",
        "group": "offices",
        "responsibility": "Idea comparison context — ideas ≠ positions (IPO).",
        "sources": ["Thesis", "Decision packages"],
        "kind": "v4_office",
        "module": "institutional_portfolio_office.production",
        "ask_flag": "AGI_V4_OFFICES_IN_ASK",
    },
    {
        "id": "imo_monitoring",
        "name": "Monitoring Office",
        "group": "offices",
        "responsibility": "What changed? Review queue for monitored names (IMO).",
        "sources": ["Events", "Company Monitor"],
        "kind": "v4_office",
        "module": "institutional_monitoring_office.production",
        "ask_flag": "AGI_V4_OFFICES_IN_ASK",
    },
    {
        "id": "ilo_learning",
        "name": "Learning Office",
        "group": "offices",
        "responsibility": "Process memory from decisions/outcomes — not KF facts (ILO).",
        "sources": ["Decisions", "Forecast validation outcomes"],
        "kind": "v4_office",
        "module": "institutional_learning_office.production",
        "ask_flag": "AGI_V4_OFFICES_IN_ASK",
    },
    {
        "id": "continuous_gather_learn",
        "name": "Continuous Gather → Learn",
        "group": "ops",
        "responsibility": (
            "Autonomous Collect→Validate→Store→Extract→Evaluate→Learn loop "
            "using LIDI, KF HD, FAA, Scheduler, FVL, FLE, ILO, CAL."
        ),
        "sources": [
            "LIDI",
            "Knowledge Factory Historical Depth",
            "FAA",
            "Institutional Scheduler",
            "FVL",
            "FLE",
            "ILO",
            "CAL",
        ],
        "kind": "cgl",
        "module": "continuous_gather_learn.production",
    },
    {
        "id": "financial_statements_engine",
        "name": "Financial Statements Engine",
        "group": "ops",
        "responsibility": (
            "Canonical financial statements pipeline — ingest → raw evidence → "
            "orchestrator → parse → validate → warehouse → DME."
        ),
        "sources": ["NSE", "BSE", "MCA", "Company IR", "FSE Raw Evidence"],
        "kind": "office",
        "module": "financial_statements_engine.production",
    },
    {
        "id": "financial_data_operations",
        "name": "Financial Data Operations (FDO)",
        "group": "ops",
        "responsibility": (
            "Coverage, completeness, gap scheduling, ingestion/source metrics, "
            "and FDO Mission Control over the existing FSE pipeline."
        ),
        "sources": ["FSE Raw Evidence", "Orchestrator", "Collection metrics"],
        "kind": "office",
        "module": "financial_statements_engine.fdo.production",
    },
    {
        "id": "financial_intelligence",
        "name": "Financial Intelligence (FIRE-01)",
        "group": "ops",
        "responsibility": (
            "Evidence-backed narrative & trend intelligence over warehouse facts — "
            "what happened financially (no BUY/SELL)."
        ),
        "sources": ["Financial Warehouse", "Derived Metrics", "Validation", "Coverage"],
        "kind": "office",
        "module": "financial_intelligence.production",
    },
    {
        "id": "financial_drivers",
        "name": "Financial Drivers (FIRE-02)",
        "group": "ops",
        "responsibility": (
            "Deterministic cross-statement relationship & driver analysis — "
            "which relationships explain financial changes (no BUY/SELL)."
        ),
        "sources": ["Financial Warehouse", "Derived Metrics", "Validation", "Coverage"],
        "kind": "office",
        "module": "financial_intelligence.drivers.production",
    },
    {
        "id": "financial_knowledge",
        "name": "Financial Knowledge Base (FKB-01)",
        "group": "ops",
        "responsibility": (
            "Canonical definitions for metrics, ratios, relationships, thresholds, "
            "glossary and sector guidance — knowledge only, no analysis."
        ),
        "sources": ["Institutional financial knowledge catalogs"],
        "kind": "office",
        "module": "financial_knowledge.production",
    },
    {
        "id": "business_intelligence",
        "name": "Business Intelligence (FIRE-03)",
        "group": "ops",
        "responsibility": (
            "Evidence extraction from official disclosures — what management says about "
            "the business, strategy, risks, opportunities, and guidance (no BUY/SELL)."
        ),
        "sources": ["Institutional Documents (IDI)", "FKB glossary (soft refs)"],
        "kind": "office",
        "module": "business_intelligence.production",
    },
    {
        "id": "evidence_fusion",
        "name": "Evidence Fusion (FIRE-04)",
        "group": "ops",
        "responsibility": (
            "Cross-evidence consistency — whether financial evidence and management "
            "statements support, partially support, or conflict (no BUY/SELL)."
        ),
        "sources": [
            "Financial Warehouse",
            "Derived Metrics",
            "FIRE-01",
            "FIRE-02",
            "FIRE-03",
            "FKB",
        ],
        "kind": "office",
        "module": "evidence_fusion.production",
    },
    {
        "id": "management_execution",
        "name": "Management Execution (FIRE-05)",
        "group": "ops",
        "responsibility": (
            "Temporal execution tracking — whether management delivered on prior "
            "disclosures using later financial evidence (no honesty judgment, no BUY/SELL)."
        ),
        "sources": [
            "FIRE-03",
            "FIRE-04",
            "Financial Warehouse",
            "Derived Metrics",
            "FKB",
        ],
        "kind": "office",
        "module": "management_execution.production",
    },
    {
        "id": "business_quality",
        "name": "Business Quality (FIRE-06)",
        "group": "ops",
        "responsibility": (
            "Pillar-primary synthesis of FIRE evidence into business quality scores — "
            "growth, profitability, cash, balance sheet, capital allocation, execution, model (no BUY/SELL)."
        ),
        "sources": [
            "Financial Warehouse",
            "Derived Metrics",
            "FIRE-01",
            "FIRE-02",
            "FIRE-03",
            "FIRE-04",
            "FIRE-05",
            "FKB quality weights",
        ],
        "kind": "office",
        "module": "business_quality.production",
    },
    # —— Learning / eval ——
    {
        "id": "forecast_validation_learning",
        "name": "Forecast Validation & Learning",
        "group": "learning",
        "responsibility": "Score forecasts against outcomes and emit learning records.",
        "sources": ["Forecasts", "Outcomes"],
        "kind": "learning",
        "module": "forecast_validation_learning.production",
    },
    {
        "id": "fle",
        "name": "Forecast Learning Engine",
        "group": "learning",
        "responsibility": "Calibration / learning consult for Ask (retrieval).",
        "sources": ["FLE store", "Forecast history"],
        "kind": "learning",
        "module": "app.fle.service",
    },
    {
        "id": "evaluation_agent",
        "name": "Evaluation Agent",
        "group": "learning",
        "responsibility": "Record predictions for later outcome scoring.",
        "sources": ["Local eval store"],
        "kind": "eval",
        "module": "app.eval.evaluation_agent",
    },
    {
        "id": "red_team",
        "name": "Red Team Lab",
        "group": "learning",
        "responsibility": "Blind adversarial evaluation — never trains reasoning.",
        "sources": ["Exam / probe suites"],
        "kind": "eval",
        "module": "red_team.production",
    },
    # —— Historical / continuous (seeded) ——
    {
        "id": "historical_market_intelligence",
        "name": "Historical Market Intelligence",
        "group": "historical",
        "responsibility": "Decades-scale market memory (seeded; Ask never collects).",
        "sources": ["Seeded market history"],
        "kind": "historical",
        "module": "historical_market_intelligence.production",
    },
    {
        "id": "historical_sector_intelligence",
        "name": "Historical Sector Intelligence",
        "group": "historical",
        "responsibility": "Immutable sector event memory (seeded).",
        "sources": ["Seeded sector history"],
        "kind": "historical",
        "module": "historical_sector_intelligence.production",
    },
    {
        "id": "historical_macro_intelligence",
        "name": "Historical Macro Intelligence",
        "group": "historical",
        "responsibility": "Long-run macro regime memory (seeded).",
        "sources": ["Seeded macro history"],
        "kind": "historical",
        "module": "historical_macro_intelligence.production",
    },
    {
        "id": "continuous_macro_knowledge",
        "name": "Continuous Macro Knowledge",
        "group": "historical",
        "responsibility": "Ongoing macro knowledge pipeline (seeded / ops).",
        "sources": ["RBI / global macro releases (seeded)"],
        "kind": "historical",
        "module": "continuous_macro_knowledge.production",
    },
    # —— Ops ——
    {
        "id": "cio_morning_scheduler",
        "name": "CIO Morning Scheduler",
        "group": "ops",
        "responsibility": "Node scheduler that triggers CIO desk research runs.",
        "sources": ["Node API → engine /v1/research/runs"],
        "kind": "ops_flag",
        "env": "CIO_MORNING_SCHEDULER",
    },
    {
        "id": "cms_ingest_worker",
        "name": "CMS Ingest Worker",
        "group": "ops",
        "responsibility": "Ingest CMS articles into institutional knowledge.",
        "sources": ["CMS / Supabase queue"],
        "kind": "ops_flag",
        "env": "CMS_INGEST_WORKER_MODE",
        "env_working_values": {"embedded", "external", "1", "true"},
    },
    {
        "id": "institutional_scheduler",
        "name": "Institutional Scheduler",
        "group": "ops",
        "responsibility": "Ops DAG soft-wire to LIDI / KF / Research Office.",
        "sources": ["Ops APIs"],
        "kind": "planner",
        "module": "institutional_scheduler.production",
    },
    {
        "id": "analyst_router",
        "name": "Institutional Analyst Router",
        "group": "ops",
        "responsibility": "Plans which analysts should participate for a question.",
        "sources": ["Research ontology"],
        "kind": "planner",
        "module": "analyst_router.production",
    },
]


GROUP_LABELS = {
    "cio_desk": "CIO Morning Desk",
    "institutional_analysts": "Institutional Analyst Framework",
    "acquisition": "Acquisition & Gathering",
    "live_collectors": "Live Collectors (LIDI)",
    "knowledge_factory": "Knowledge Factory Clients",
    "offices": "Investment / Research Offices",
    "learning": "Learning & Evaluation",
    "historical": "Historical & Continuous Knowledge",
    "ops": "Ops / Schedulers",
}


def _resolve_status(item: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """Return (status, detail, probe)."""
    kind = item.get("kind")
    probe: dict[str, Any] = {}

    if kind == "cio_agent":
        st = _cio_status(str(item["id"]))
        detail = {
            "working": "Registered and available for CIO desk runs.",
            "soft": "Source present but not registered in the live agent registry.",
            "orphan": "Source missing — packaging agent removed or not bootstrapped.",
        }.get(st, "")
        return st, detail, probe

    if kind == "iaf":
        flag_on = _env_truthy("INSTITUTIONAL_ANALYSTS", "true") or _env_truthy(
            "ASK_AGI_IAF", "true"
        )
        if not flag_on:
            return "off", "IAF flags disabled.", probe
        st, body = _probe_health(str(item.get("module") or "institutional_analysts.production"))
        # IAF is soft-wire by design even when healthy.
        if st == "working":
            st = "soft"
        return st, "Soft-wired into Ask Answer Construction; uses existing engines, not raw APIs.", body

    if kind == "faa":
        faa_on = _env_truthy("FAA", "true")
        live = _env_truthy("FAA_LIVE_FETCH", "false")
        ask_blocked = _env_falsey("AIL_LIVE_FAA", "false")  # false means Ask must not call unbound acquire
        if not faa_on:
            return "off", "FAA flag disabled.", {"FAA": False}
        if live:
            return (
                "working",
                "FAA live fetch enabled. Ask path blocked from unbound acquire."
                if ask_blocked
                else "FAA live fetch enabled; Ask may call live FAA.",
                {"FAA": True, "FAA_LIVE_FETCH": True, "AIL_LIVE_FAA": _env_truthy("AIL_LIVE_FAA", "false")},
            )
        return "soft", "FAA module on but live fetch off.", {"FAA": True, "FAA_LIVE_FETCH": False}

    if kind == "faa_bg":
        if _env_truthy("FAA_BACKGROUND_COLLECTOR", "false"):
            return "working", "Background collector enabled.", {}
        if _env_truthy("CONTINUOUS_FAA_REFRESH", "true"):
            return "soft", "FAA refresh runs inside CGL post-market/overnight phases (Ask-isolated).", {
                "CONTINUOUS_FAA_REFRESH": True
            }
        return "off", "FAA_BACKGROUND_COLLECTOR=false (enable flag or CONTINUOUS_FAA_REFRESH).", {}

    if kind == "lidi":
        mod = str(item.get("module") or "")
        ok, err = _probe_import(mod)
        if not ok:
            return "orphan", err or "Collector module missing.", {}
        if _env_truthy("CONTINUOUS_GATHER_LEARN", "true") and _env_truthy("CONTINUOUS_LIDI", "true"):
            return "working", "LIDI activated via Continuous Gather→Learn (Ask-isolated).", {
                "CONTINUOUS_LIDI": True
            }
        ask_slim = _env_truthy("ASK_SLIM", "true")
        if ask_slim:
            return "soft", "Collector code live-capable; Ask slim skips live fan-out. Ops/scheduler can still run.", {
                "ASK_SLIM": True
            }
        return "soft", "Live-capable collector soft-wired; enable CONTINUOUS_GATHER_LEARN for autonomous loop.", {}

    if kind == "kf_client":
        mod = str(item.get("module") or "")
        ok, err = _probe_import(mod)
        if not ok:
            return "orphan", err or "KF client missing.", {}
        return "soft", "Fixture-first Knowledge Factory client (live optional via KF flags).", {}

    if kind == "v4_office":
        mod = str(item.get("module") or "")
        ask_on = _env_truthy(str(item.get("ask_flag") or "AGI_V4_OFFICES_IN_ASK"), "0")
        st, body = _probe_health(mod) if mod else ("off", {})
        if st == "orphan" or (isinstance(body, dict) and body.get("error") and "import" in str(body.get("error")).lower()):
            ok, err = _probe_import(mod)
            if not ok:
                return "orphan", err or "Office package missing.", body
        if not ask_on:
            # Module may still work via Mission Control / dedicated APIs.
            if st in {"working", "soft", "degraded"} or _probe_import(mod)[0]:
                return "soft", "Office package available; off inside Ask (AGI_V4_OFFICES_IN_ASK=0).", {
                    "AGI_V4_OFFICES_IN_ASK": False
                }
            return "off", "v4 office off in Ask and package unavailable.", {}
        return "working" if st == "working" else st, "v4 office enabled in Ask.", body

    if kind == "office":
        mod = str(item.get("module") or "")
        st, body = _probe_health(mod)
        if st == "working":
            return "soft", "Office soft-wire available for ops / cockpit.", body
        if st == "off" and _probe_import(mod)[0]:
            return "soft", "Office module importable.", body
        return st, "Office probe result.", body

    if kind == "learning":
        mod = str(item.get("module") or "")
        cgl_learn = _env_truthy("CONTINUOUS_GATHER_LEARN", "true") and _env_truthy(
            "CONTINUOUS_LEARNING_LOOP", "true"
        )
        if item["id"] == "fle":
            ok, err = _probe_import(mod, "FleService") if mod else (False, "missing")
            # FleService class name may differ — try module only
            if not ok:
                ok, err = _probe_import(mod)
            ask_slim = _env_truthy("ASK_SLIM", "true")
            if not ok:
                return "orphan", err or "FLE missing.", {}
            if cgl_learn:
                return "working", "FLE activated in Continuous Gather→Learn cycle.", {"ASK_SLIM": ask_slim}
            return (
                "soft",
                "FLE consult soft-wired; Ask slim may skip heavy fan-out.",
                {"ASK_SLIM": ask_slim},
            )
        st, body = _probe_health(mod) if mod else ("off", {})
        if cgl_learn and (st in {"working", "soft"} or (mod and _probe_import(mod)[0])):
            return "working", "Learning loop activated via Continuous Gather→Learn (durable archive).", body
        if st == "working":
            st = "soft"
        if st in {"off", "degraded"} and mod and _probe_import(mod)[0]:
            return "soft", "Learning module present (in-memory / soft retrieval).", body
        return st, "Learning / validation soft-wire.", body

    if kind == "eval":
        mod = str(item.get("module") or "")
        ok, err = _probe_import(mod)
        if not ok:
            return "orphan", err or "Eval module missing.", {}
        return "soft", "Evaluation / red-team available for ops; not continuous prod learning.", {}

    if kind == "historical":
        mod = str(item.get("module") or "")
        st, body = _probe_health(mod) if mod else ("off", {})
        if mod and _probe_import(mod)[0]:
            return "soft", "Seeded historical memory available; Ask never triggers collectors.", body
        return "orphan", "Historical module missing.", body

    if kind == "planner":
        mod = str(item.get("module") or "")
        st, body = _probe_health(mod) if mod else ("off", {})
        if st == "working":
            st = "soft"
        if mod and _probe_import(mod)[0] and st == "off":
            return "soft", "Planner soft-wire importable.", body
        return st if st != "working" else "soft", "Planner soft-wire.", body

    if kind == "cgl":
        if not _env_truthy("CONTINUOUS_GATHER_LEARN", "true"):
            return "off", "CONTINUOUS_GATHER_LEARN=false.", {}
        st, body = _probe_health("continuous_gather_learn.production")
        if st in {"working", "soft"}:
            return "working", "Continuous gather→learn loop enabled (Ask-isolated).", body
        if _probe_import("continuous_gather_learn.production")[0]:
            return "working", "CGL package available; background starts with engine lifespan.", body
        return "orphan", "CGL package missing.", body

    if kind == "knowledge_integration":
        mod = str(item.get("module") or "institutional_evidence.integration.layer")
        st, body = _probe_health(mod, "health")
        if st == "off":
            # Legacy probe: older deploys only exposed kil_status()
            ok, err = _probe_import(mod, "kil_status")
            if ok:
                try:
                    m = __import__(mod, fromlist=["kil_status"])
                    body = m.kil_status()
                    st = "working" if isinstance(body, dict) and body.get("ok") else "soft"
                except Exception as exc:  # noqa: BLE001
                    return "degraded", f"KIL kil_status failed: {exc}"[:160], {}
            else:
                return "orphan", err or "KIL module missing.", {}
        if isinstance(body, dict) and (
            body.get("enabled") is not False
            and str(body.get("status") or "").lower()
            in {"ok", "healthy", "ready", "live", "ok_via_sidecar", ""}
        ):
            n = body.get("companies_integrated")
            detail = (
                f"KIL-01 live — {n} companies integrated (persisted)."
                if isinstance(n, int)
                else "KIL-01 live (CGL → canonical → IEP)."
            )
            return "working", detail, body
        if st in {"working", "soft", "degraded"}:
            return "working" if st != "degraded" else st, "KIL-01 probe result.", body
        if _probe_import(mod)[0]:
            return "working", "KIL package importable; soft-wired after each CGL cycle.", body
        return st, "KIL probe result.", body

    if kind == "ops_flag":
        env_name = str(item.get("env") or "")
        raw = os.getenv(env_name, "")
        allowed = item.get("env_working_values")
        if allowed:
            if str(raw).strip().lower() in {str(v).lower() for v in allowed} or _env_truthy(env_name, "false"):
                return "working", f"{env_name}={raw or 'set'}.", {env_name: raw}
            # CMS worker defaults to embedded on Node API even if unset in engine env
            if item["id"] == "cms_ingest_worker":
                return "soft", "CMS ingest typically runs on Node API (embedded); engine env may not mirror it.", {
                    env_name: raw or None
                }
            return "off", f"{env_name} not in working mode (value={raw or 'unset'}).", {env_name: raw}
        if _env_truthy(env_name, "false"):
            return "working", f"{env_name}=true.", {env_name: True}
        # CIO morning scheduler is on Node, not engine
        if item["id"] == "cio_morning_scheduler":
            return "soft", "Runs on Node API (CIO_MORNING_SCHEDULER); engine env may not mirror it.", {
                env_name: raw or None
            }
        return "off", f"{env_name} disabled or unset.", {env_name: raw}

    # Generic module probe
    mod = str(item.get("module") or "")
    if mod:
        st, body = _probe_health(mod)
        return st, "Module probe.", body
    return "unknown", "No probe configured.", {}


def build_agent_map() -> dict[str, Any]:
    agents: list[dict[str, Any]] = []
    counts = {"working": 0, "soft": 0, "off": 0, "orphan": 0, "degraded": 0, "unknown": 0}

    for item in _CATALOG:
        status, detail, probe = _resolve_status(item)
        if status not in counts:
            status = "unknown"
        counts[status] = counts.get(status, 0) + 1
        agents.append(
            {
                "id": item["id"],
                "name": item["name"],
                "group": item["group"],
                "group_label": GROUP_LABELS.get(item["group"], item["group"]),
                "responsibility": item["responsibility"],
                "sources": list(item.get("sources") or []),
                "status": status,
                "working": status == "working",
                "detail": detail,
                "probe": probe if isinstance(probe, dict) else {},
            }
        )

    groups: dict[str, dict[str, Any]] = {}
    for a in agents:
        g = a["group"]
        bucket = groups.setdefault(
            g,
            {
                "id": g,
                "label": a["group_label"],
                "agents": [],
                "counts": {"working": 0, "soft": 0, "off": 0, "orphan": 0, "degraded": 0, "unknown": 0},
            },
        )
        bucket["agents"].append(a)
        bucket["counts"][a["status"]] = bucket["counts"].get(a["status"], 0) + 1

    ask_slim = _env_truthy("ASK_SLIM", "true")
    faa_bg = _env_truthy("FAA_BACKGROUND_COLLECTOR", "false")
    offices_ask = _env_truthy("AGI_V4_OFFICES_IN_ASK", "0")

    return {
        "enabled": True,
        "read_only": True,
        "programme": "AGIB Agent Map",
        "version": AGENT_MAP_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": len(agents),
            **counts,
            "working_or_soft": counts["working"] + counts["soft"],
            "headline": (
                f"{counts['working']} working · {counts['soft']} soft-wire · "
                f"{counts['off']} off · {counts['orphan']} orphan"
            ),
        },
        "production_flags": {
            "ASK_SLIM": ask_slim,
            "FAA": _env_truthy("FAA", "true"),
            "FAA_LIVE_FETCH": _env_truthy("FAA_LIVE_FETCH", "false"),
            "FAA_BACKGROUND_COLLECTOR": faa_bg,
            "AIL_LIVE_FAA": _env_truthy("AIL_LIVE_FAA", "false"),
            "AGI_V4_OFFICES_IN_ASK": offices_ask,
            "AGI_V4_OFFICE_PERSIST": _env_truthy("AGI_V4_OFFICE_PERSIST", "0"),
            "CIO_MORNING_SCHEDULER": os.getenv("CIO_MORNING_SCHEDULER"),
            "INSTITUTIONAL_ANALYSTS": _env_truthy("INSTITUTIONAL_ANALYSTS", "true"),
        },
        "status_legend": {
            "working": "Intended to run in production and currently available.",
            "soft": "Code/path available as soft-wire, seeded, or ops-only — not a continuous primary loop.",
            "off": "Disabled by production flag or configuration.",
            "orphan": "Source missing or not importable.",
            "degraded": "Module present but health probe failed.",
            "unknown": "Could not determine status.",
        },
        "groups": list(groups.values()),
        "agents": agents,
    }
