"""E2E-01 — Institutional Product Experience Validation."""

from __future__ import annotations

from typing import Any

E2E_WORKSTREAM_ID = "E2E-01"
E2E_PRODUCT = "Institutional Product Experience Validation"
E2E_VERSION = "e2e-01-v1.0.0"
E2E_SUBSYSTEM = "product_experience_validation"
E2E_SPEC = "docs/AGI_E2E_01_PRODUCT_EXPERIENCE_VALIDATION.md"
E2E_ROLE = "end_to_end_product_experience_validation"

# Not an intelligence engine / not a benchmark suite for reasoning quality.
E2E_NOT_AN_ENGINE = True
E2E_NOT_A_BENCHMARK = True
E2E_NOT_AN_OFFICE = True

PASS_SCORE = 90.0

PRIMARY_TICKER = "KOTAKBANK"
PRIMARY_COMPANY = "Kotak Mahindra Bank"
PRODUCT_ENTRY = "/agi"
HISTORICAL_CUTOFF = "2024-05-15"
IBS_CASE_ID = "KOTAK_RBI"

# Rubric weights (sum = 100)
RUBRIC_WEIGHTS: dict[str, float] = {
    "navigation": 10.0,
    "dashboard": 5.0,
    "company_workspace": 15.0,
    "evidence_drilldown": 10.0,
    "ask_agi": 15.0,
    "research": 10.0,
    "portfolio": 10.0,
    "markets": 5.0,
    "context_awareness": 10.0,
    "performance": 5.0,
    "consistency": 5.0,
    "failure_handling": 5.0,
}

# Workflow IDs map to scoring dimensions (some dimensions cover multiple WFs)
WORKFLOWS: tuple[dict[str, Any], ...] = (
    {"id": "WF1", "name": "Morning Brief", "dimension": "dashboard"},
    {"id": "WF2", "name": "Company Research", "dimension": "company_workspace"},
    {"id": "WF3", "name": "Evidence Drill-down", "dimension": "evidence_drilldown"},
    {"id": "WF4", "name": "Ask AGI", "dimension": "ask_agi"},
    {"id": "WF5", "name": "Research", "dimension": "research"},
    {"id": "WF6", "name": "Portfolio", "dimension": "portfolio"},
    {"id": "WF7", "name": "Markets", "dimension": "markets"},
    {"id": "WF8", "name": "Watchlists", "dimension": "portfolio"},  # watchlist ops score into portfolio surface readiness
    {"id": "WF9", "name": "Context Awareness", "dimension": "context_awareness"},
    {"id": "WF10", "name": "Navigation", "dimension": "navigation"},
    {"id": "WF11", "name": "Performance", "dimension": "performance"},
    {"id": "WF12", "name": "Failure Handling", "dimension": "failure_handling"},
    {"id": "WF13", "name": "Consistency", "dimension": "consistency"},
    {"id": "WF14", "name": "Historical Blind", "dimension": "consistency"},
    {"id": "WF15", "name": "Benchmark", "dimension": "ask_agi"},
)

FAILURE_CODES: tuple[str, ...] = (
    "BROKEN_NAVIGATION",
    "BROKEN_CONTEXT",
    "MISSING_RESEARCH",
    "MISSING_EVIDENCE",
    "BROKEN_PROVENANCE",
    "SLOW_PAGE",
    "HALLUCINATED_FACT",
    "NO_UNKNOWNS",
    "CONFIDENCE_MISMATCH",
    "TIMELINE_FAILURE",
    "BROKEN_PORTFOLIO",
    "BROKEN_WATCHLIST",
    "SEARCH_FAILURE",
    "CONTEXT_LOST",
    "CONSISTENCY_FAILURE",
    "ENGINE_JARGON_LEAK",
    "EMPTY_DASHBOARD",
    "MISSING_SECTION",
    "PLACEHOLDER_SURFACE",
)

# Soft latency targets (ms) — FAIL only when clearly sluggish
LATENCY_TARGETS_MS: dict[str, float] = {
    "dashboard_probe": 800.0,
    "company_load": 2500.0,
    "evidence_load": 1500.0,
    "timeline_load": 1500.0,
    "ask_probe": 3000.0,
    "research_probe": 1500.0,
    "search_latency": 1500.0,
}

# Product language — must NOT appear in AGI product UI sources
FORBIDDEN_UI_JARGON: tuple[str, ...] = (
    "FIRE-01",
    "FIRE-02",
    "FIRE-03",
    "FIRE-04",
    "FIRE-05",
    "FIRE-06",
    "Office SDK",
    "PEB-01",
    "CW-01",
    "CIO-01",
    "IO-01",
    "WO-01",
    "PO-01",
)

REQUIRED_NAV: tuple[str, ...] = (
    "Dashboard",
    "Ask AGI",
    "Companies",
    "Portfolio",
    "Markets",
    "Research",
    "Watchlists",
)

REQUIRED_DASHBOARD_MARKERS: tuple[str, ...] = (
    "Global Markets",
    "Today",
    "Watchlist",
    "Portfolio",
    "Research",
    "Alerts",
)

REQUIRED_COMPANY_TABS: tuple[str, ...] = (
    "Overview",
    "Business Quality",
    "Financials",
    "Evidence",
    "Timeline",
    "Research Notes",
    "Portfolio",
    "Watchlists",
)

REQUIRED_RESEARCH_SECTIONS: tuple[str, ...] = (
    "Executive Summary",
    "Financial",
    "Business",
    "Evidence",
    "Risks",
    "Unknowns",
    "Monitoring",
    "Confidence",
    "Appendix",
)

REQUIRED_PORTFOLIO_MARKERS: tuple[str, ...] = (
    "Portfolio Health",
    "Research Coverage",
    "Business Quality",
    "Concentration",
    "Recent Changes",
    "Watchlist",
)

REQUIRED_MARKETS_MARKERS: tuple[str, ...] = (
    "Global",
    "India",
    "Macro",
    "FX",
    "Rates",
    "Commodities",
    "Calendar",
    "Corporate Actions",
)

PRODUCT_UI_FILES: tuple[str, ...] = (
    "src/pages/agi/AgiRoutes.jsx",
    "src/pages/agi/AgiLayout.jsx",
    "src/pages/agi/DashboardPage.jsx",
    "src/pages/agi/AskAgiProductPage.jsx",
    "src/pages/agi/CompaniesIndexPage.jsx",
    "src/pages/agi/CompanyWorkspacePage.jsx",
    "src/pages/agi/PortfolioWorkspacePage.jsx",
    "src/pages/agi/MarketsWorkspacePage.jsx",
    "src/pages/agi/ResearchWorkspacePage.jsx",
    "src/pages/agi/WatchlistsWorkspacePage.jsx",
    "src/pages/agi/helpers.js",
    "src/App.jsx",
)

FREEZE_LOCKS: dict[str, Any] = {
    "not_an_engine": True,
    "not_a_benchmark": True,
    "product_language_only": True,
    "no_buy_sell_from_validation": True,
    "pass_score": PASS_SCORE,
}
