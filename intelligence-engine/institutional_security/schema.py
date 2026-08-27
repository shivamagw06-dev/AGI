"""PRP-02 — Security & Governance constants."""

from __future__ import annotations

PRP_WORKSTREAM_ID = "PRP-02"
PRP_02_ID = PRP_WORKSTREAM_ID
PRP_PRODUCT = "Security & Governance"
PRP_VERSION = "prp-02-v1.0.0"
PRP_SPEC = "docs/AGI_PRP_02_SECURITY_GOVERNANCE.md"
PRP_ROLE = "production_readiness_security"
SECURITY_ENGINE_VERSION = "prp-02-sec-v1"

ADDS_INTELLIGENCE_ENGINES = False
ARCHITECTURE_FROZEN = True
AGIB_PLATFORM_VERSION = "1.0.0"

# Security decides who; intelligence decides what
GUIDING_PRINCIPLE = (
    "Security decides who can perform an operation. "
    "Intelligence decides what the operation means."
)

AUTH_METHODS = (
    "password",
    "sso",
    "oauth2",
    "oidc",
    "api_key",
    "service_account",
)

ROLES = (
    "administrator",
    "chief_investment_officer",
    "portfolio_manager",
    "research_analyst",
    "compliance",
    "read_only",
    "service_account",
)

PERMISSIONS = (
    "research.read",
    "research.note.write",
    "portfolio.manage",
    "publication.generate",
    "publication.distribute",
    "committee.approve",
    "policy.manage",
    "platform.admin",
    "security.manage",
    "audit.read",
)

ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "administrator": PERMISSIONS,
    "chief_investment_officer": (
        "research.read",
        "research.note.write",
        "portfolio.manage",
        "publication.generate",
        "publication.distribute",
        "committee.approve",
        "policy.manage",
        "audit.read",
    ),
    "portfolio_manager": (
        "research.read",
        "research.note.write",
        "portfolio.manage",
        "publication.generate",
        "publication.distribute",
        "audit.read",
    ),
    "research_analyst": (
        "research.read",
        "research.note.write",
        "publication.generate",
    ),
    "compliance": (
        "research.read",
        "policy.manage",
        "audit.read",
        "publication.distribute",
    ),
    "read_only": ("research.read", "audit.read"),
    "service_account": (
        "research.read",
        "publication.generate",
        "publication.distribute",
    ),
}

PRIVILEGED_ACTIONS = (
    "publication.generate",
    "publication.distribute",
    "committee.approve",
    "policy.manage",
    "platform.admin",
    "security.manage",
    "permission.change",
    "api_key.create",
    "api_key.revoke",
    "session.impersonate",
)

DEFAULT_SESSION_TTL_SECONDS = 3600
DEFAULT_API_KEY_TTL_SECONDS = 86400 * 90
