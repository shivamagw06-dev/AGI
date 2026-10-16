"""MPC-01 — Multi-Portfolio & Client Platform constants."""

from __future__ import annotations

MPC_WORKSTREAM_ID = "MPC-01"
MPC_PRODUCT = "Multi-Portfolio & Client Platform"
MPC_VERSION = "mpc-01-v1.0.0"
MPC_SPEC = "docs/AGI_MPC_01_MULTI_PORTFOLIO.md"
MPC_ROLE = "tenancy_workflow_not_intelligence"
PLATFORM_ENGINE_VERSION = "mpc-01-platform-v1"

# Intelligence is global; tenancy/workflow are local
OWNS_INTELLIGENCE = False
INTELLIGENCE_IS_GLOBAL = True
PORTFOLIOS_ARE_LOCAL = True

ROLES = (
    "analyst",
    "senior_analyst",
    "portfolio_manager",
    "cio",
    "compliance",
    "administrator",
)

PERMISSIONS = (
    "view_research",
    "create_notes",
    "generate_publications",
    "approve_committee",
    "manage_portfolio",
    "manage_users",
    "distribute_publications",
    "manage_clients",
    "view_workspace",
)

# Role → permissions (workflow only — never gates company truth)
ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "analyst": ("view_research", "create_notes", "view_workspace"),
    "senior_analyst": (
        "view_research",
        "create_notes",
        "generate_publications",
        "view_workspace",
        "distribute_publications",
    ),
    "portfolio_manager": (
        "view_research",
        "create_notes",
        "generate_publications",
        "manage_portfolio",
        "view_workspace",
        "distribute_publications",
    ),
    "cio": (
        "view_research",
        "create_notes",
        "generate_publications",
        "approve_committee",
        "manage_portfolio",
        "view_workspace",
        "distribute_publications",
        "manage_clients",
    ),
    "compliance": (
        "view_research",
        "view_workspace",
        "approve_committee",
        "distribute_publications",
    ),
    "administrator": PERMISSIONS,
}

MANDATE_PROFILES = (
    "conservative",
    "balanced",
    "growth",
    "income",
    "institutional",
    "family_office",
)

# Map MPC mandates → PCE-01 policy profiles (soft; PCE remains SoR for policy)
MANDATE_TO_POLICY: dict[str, str] = {
    "conservative": "conservative",
    "balanced": "balanced",
    "growth": "growth",
    "income": "balanced",
    "institutional": "pms",
    "family_office": "family_office",
}

PUBLICATION_SCOPES = (
    "global",
    "portfolio",
    "client",
    "committee",
    "private",
)

SEED_PORTFOLIOS = (
    ("growth-portfolio", "Growth Portfolio", "growth"),
    ("income-portfolio", "Income Portfolio", "income"),
    ("banking-strategy", "Banking Strategy", "institutional"),
    ("family-office", "Family Office", "family_office"),
    ("pms-model", "PMS Model", "balanced"),
    ("research-sandbox", "Research Sandbox", "balanced"),
    ("agi-core-equity", "AGI Core Equity", "family_office"),
)

SEED_CLIENTS = (
    ("client-alpha", "Client Alpha", ("growth-portfolio", "agi-core-equity"), "family_office"),
    ("client-beta", "Client Beta", ("income-portfolio", "banking-strategy"), "conservative"),
    ("client-institutional", "Institutional Desk", ("pms-model", "banking-strategy"), "institutional"),
)
