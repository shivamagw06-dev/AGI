"""L-01 — Launch Phase constants. Usage validation, not architecture expansion."""

from __future__ import annotations

L_WORKSTREAM_ID = "L-01"
L_01_ID = L_WORKSTREAM_ID
L_PRODUCT = "Launch Phase"
L_VERSION = "l-01-v1.0.0"
L_SPEC = "docs/AGI_L_01_LAUNCH.md"
L_ROLE = "usage_validation"
LAUNCH_ENGINE_VERSION = "l-01-launch-v1"

ADDS_INTELLIGENCE_ENGINES = False
ARCHITECTURE_FROZEN = True
AGIB_PLATFORM_VERSION = "1.0.0"
AGIB_GENERAL_AVAILABILITY = True

GUIDING_PRINCIPLE = (
    "Validate that AGIB solves real analyst workflows before expanding the product. "
    "Driven by usage, not architecture."
)

# User journey stages
JOURNEY_STAGES = (
    "login",
    "dashboard",
    "ask_agi",
    "research_workspace",
    "company",
    "portfolio",
    "publication",
    "export",
)

FEEDBACK_REACTIONS = ("helpful", "not_helpful")

FEEDBACK_TAGS = (
    "missing_data",
    "wrong_answer",
    "too_slow",
    "hard_to_understand",
    "wrong_entity",
    "stale_data",
    "missing_evidence",
    "unclear_reasoning",
    "too_long",
    "forecast_issue",
)

# v1.1 capabilities — off by default until Launch-01 is healthy
V11_FEATURE_FLAGS = (
    "AI_REPORTS",
    "COLLABORATION",
    "GLOBAL_MARKETS",
    "MACRO_LAB",
    "AUTOMATION",
    "EXTERNAL_INTEGRATIONS",
    "AI_PRODUCTIVITY",
)

SLA_TARGETS = {
    "ask_agi_p95_latency_ms": 3000,
    "data_freshness_minutes": 30,
    "availability_pct": 99.9,
    "architecture_conformance_pct": 100.0,
    "publication_success_pct": 99.0,
}
