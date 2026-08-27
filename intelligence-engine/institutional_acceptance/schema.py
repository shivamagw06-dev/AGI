"""PAT-01 — Production Acceptance Test constants.

Break AGIB before onboarding users. Architecture remains frozen at v1.0 GA.
"""

from __future__ import annotations

PAT_WORKSTREAM_ID = "PAT-01"
PAT_01_ID = PAT_WORKSTREAM_ID
PAT_PRODUCT = "Production Acceptance Test"
PAT_VERSION = "pat-01-v1.0.0"
PAT_SPEC = "docs/AGI_PAT_01_PRODUCTION_ACCEPTANCE.md"
PAT_ROLE = "production_acceptance"
ACCEPTANCE_ENGINE_VERSION = "pat-01-acceptance-v1"

ADDS_INTELLIGENCE_ENGINES = False
ARCHITECTURE_FROZEN = True
AGIB_PLATFORM_VERSION = "1.0.0"
AGIB_GENERAL_AVAILABILITY = True

GUIDING_PRINCIPLE = (
    "Validate that every subsystem works together under realistic conditions "
    "before onboarding users. Try to break AGIB."
)

SUCCESS_CRITERIA = {
    "min_test_cases": 200,
    "pass_rate_pct": 100.0,
    "critical_failures": 0,
    "architecture_score": 100,
    "memory_leaks": 0,
    "security_violations": 0,
}

PHASES = (
    ("P01", "system_boot", "System Boot"),
    ("P02", "data_layer", "Data Layer"),
    ("P03", "knowledge_graph", "Knowledge Graph"),
    ("P04", "intelligence", "Intelligence"),
    ("P05", "ask_agi", "Ask AGI"),
    ("P06", "research_workspace", "Research Workspace"),
    ("P07", "publishing", "Publishing"),
    ("P08", "multi_portfolio", "Multi Portfolio"),
    ("P09", "security", "Security"),
    ("P10", "performance", "Performance"),
    ("P11", "observability", "Observability"),
    ("P12", "rc01", "RC-01 Architecture"),
    ("P13", "failure_injection", "Failure Injection"),
    ("P14", "end_to_end_workflow", "End-to-End Workflow"),
    ("P15", "long_running_stability", "Long-Running Stability"),
)

# Representative universe for intelligence / ask acceptance
PAT_COMPANIES = (
    "HDFCBANK",
    "ICICIBANK",
    "AXISBANK",
    "SBIN",
    "KOTAKBANK",
    "RELIANCE",
    "TCS",
    "INFY",
    "WIPRO",
    "HCLTECH",
    "BHARTIARTL",
    "ITC",
    "HINDUNILVR",
    "ASIANPAINT",
    "MARUTI",
    "TATAMOTORS",
    "M&M",
    "BAJFINANCE",
    "BAJAJFINSV",
    "LT",
    "SUNPHARMA",
    "DRREDDY",
    "CIPLA",
    "NESTLEIND",
    "TITAN",
    "ULTRACEMCO",
    "POWERGRID",
    "NTPC",
    "ONGC",
    "COALINDIA",
    "JSWSTEEL",
    "TATASTEEL",
    "ADANIENT",
    "ADANIPORTS",
    "DMART",
    "PIDILITIND",
    "BRITANNIA",
    "DIVISLAB",
    "TECHM",
    "INDUSINDBK",
    "GRASIM",
    "EICHERMOT",
    "HEROMOTOCO",
    "APOLLOHOSP",
    "SBILIFE",
    "HDFCLIFE",
    "BPCL",
    "IOC",
    "VEDL",
    "HINDALCO",
)

ASK_QUESTION_TEMPLATES = (
    "Why {ticker}?",
    "Compare {ticker} vs peer",
    "Portfolio risk for {ticker}",
    "Macro impact on {ticker}",
    "Oil prices effect on {ticker}",
    "Fed decision impact on {ticker}",
    "Valuation of {ticker}",
    "Credit quality of {ticker}",
    "What changed for {ticker}?",
    "Evidence for thesis on {ticker}",
)

INTELLIGENCE_ENGINES = (
    "observation",
    "forecast",
    "decision",
    "risk",
    "policy",
    "committee",
)

DATA_SOURCES = (
    "nse_data",
    "bse_announcements",
    "financial_statements",
    "corporate_actions",
    "shareholding",
    "ir_documents",
    "embeddings",
    "knowledge_graph",
)

DATA_CHECKS = (
    "coverage",
    "freshness",
    "duplicates",
    "missing_values",
    "hash_integrity",
)

KG_LAYERS = ("company", "sector", "industry", "macro", "portfolio")

PORTFOLIO_TENANTS = (
    "Growth",
    "Income",
    "Small Cap",
    "Client A",
    "Client B",
)

PUBLISH_FORMATS = ("pdf", "html", "markdown", "json")

SECURITY_ATTACKS = (
    "invalid_login",
    "expired_token",
    "revoked_key",
    "tenant_switch",
    "privilege_escalation",
    "sql_injection",
    "xss",
    "csrf",
    "path_traversal",
)

STRESS_USER_LEVELS = (10, 50, 100, 250, 500)

FAILURE_TARGETS = (
    "redis",
    "postgresql",
    "vector_db",
    "scheduler",
    "api",
    "worker",
)

WORKFLOW_STEPS = (
    "login",
    "ask_agi",
    "research_workspace",
    "review_evidence",
    "inspect_relationships",
    "portfolio_impact",
    "generate_publication",
    "export_report",
    "record_feedback",
)

STABILITY_WINDOWS = (
    ("24h", 24),
    ("48h", 48),
    ("7d", 168),
)

CONTEXT_KINDS = (
    "execution_context",
    "security_context",
    "observability_context",
)

CERTIFICATION_LABEL = "PRODUCTION CERTIFIED"
