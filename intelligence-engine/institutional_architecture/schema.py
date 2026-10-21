"""RC-01 — Architecture Conformance & Release Candidate constants."""

from __future__ import annotations

RC_WORKSTREAM_ID = "RC-01"
RC_01_ID = RC_WORKSTREAM_ID
RC_PRODUCT = "Architecture Conformance & Release Candidate"
RC_VERSION = "rc-01-v1.0.0"
RC_SPEC = "docs/AGI_RC_01_ARCHITECTURE_CONFORMANCE.md"
RC_ROLE = "architecture_quality_gate"
ARCH_ENGINE_VERSION = "rc-01-arch-v1"

ADDS_INTELLIGENCE_ENGINES = False
ARCHITECTURE_FROZEN = True
AGIB_PLATFORM_VERSION = "1.0.0"
AGIB_RELEASE_CANDIDATE = True
AGIB_GENERAL_AVAILABILITY = True
AGIB_GA_SPEC = "docs/AGIB_V1_0_GA.md"
AGIB_RELEASE_STATUS = "GENERAL_AVAILABILITY"

GUIDING_PRINCIPLE = (
    "Prove every future change preserves AGIB v1.0 architectural principles. "
    "This is a quality gate, not a feature. "
    "AGIB v1.0 is General Availability — architecture remains frozen."
)

# Canonical lineage (Evidence → … → Publication)
CANONICAL_LINEAGE = (
    "Evidence",
    "Decision",
    "Risk",
    "Policy",
    "Portfolio Decision",
    "Committee",
    "Publication",
)

# Ownership registry — package → architectural role
OWNERSHIP = {
    "institutional_graph": {
        "id": "KG-01",
        "owns": "knowledge_graph",
        "must_not": ("duplicate_graph", "workspace_ui"),
    },
    "institutional_cross_company": {
        "id": "CCI-01",
        "owns": "relationships",
        "must_not": ("graph_state",),
        "graph_sor": "KG-01",
    },
    "institutional_orchestrator": {
        "id": "UAG-01",
        "owns": "orchestration",
        "must_not": ("recommendations", "business_state"),
    },
    "institutional_publishing": {
        "id": "PUB-01",
        "owns": "composition",
        "must_not": ("reasoning", "analysis", "recommendations"),
    },
    "institutional_multi_portfolio": {
        "id": "MPC-01",
        "owns": "tenancy",
        "must_not": ("intelligence",),
    },
    "institutional_workspace": {
        "id": "RW-01",
        "owns": "presentation",
        "must_not": ("system_intelligence_mutation", "recommendations"),
    },
    "institutional_performance": {
        "id": "PRP-01",
        "owns": "performance",
        "must_not": ("business_logic", "intelligence"),
    },
    "institutional_security": {
        "id": "PRP-02",
        "owns": "security",
        "must_not": ("intelligence_mutation",),
    },
    "institutional_observability": {
        "id": "PRP-03",
        "owns": "observability",
        "must_not": ("execution_mutation", "intelligence"),
    },
}

# Forbidden import edges: (from_package, to_package)
# Domain intelligence must not depend on security/observability/workspace UI.
FORBIDDEN_IMPORTS = (
    ("institutional_decision", "institutional_security"),
    ("institutional_decision", "institutional_observability"),
    ("institutional_decision", "institutional_workspace"),
    ("institutional_graph", "institutional_workspace"),
    ("institutional_graph", "institutional_security"),
    ("institutional_graph", "institutional_observability"),
    ("institutional_graph", "institutional_publishing"),
    ("institutional_portfolio_risk", "institutional_security"),
    ("institutional_portfolio_risk", "institutional_observability"),
    ("institutional_policy", "institutional_security"),
    ("institutional_portfolio_decision", "institutional_security"),
    ("institutional_committee", "institutional_security"),
    ("institutional_forecasting", "institutional_security"),
    ("institutional_cross_company", "institutional_security"),
    ("institutional_cross_company", "institutional_observability"),
)

# Packages that must declare architecture freeze / no new engines (production layer)
PRODUCTION_FREEZE_PACKAGES = (
    "institutional_performance",
    "institutional_security",
    "institutional_observability",
)

REQUIRED_CONTEXTS = (
    "execution_context",
    "security_context",
    "observability_context",
)
