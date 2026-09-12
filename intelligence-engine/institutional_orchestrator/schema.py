"""UAG-01 — Universal Ask AGI Orchestrator constants."""

from __future__ import annotations

UAG_WORKSTREAM_ID = "UAG-01"
UAG_PRODUCT = "Universal Ask AGI Orchestrator"
UAG_VERSION = "uag-01-v1.0.0"
UAG_SPEC = "docs/AGI_UAG_01_UNIVERSAL_ASK.md"
UAG_ROLE = "stateless_institutional_orchestration"
ORCHESTRATOR_VERSION = "uag-01-orchestrator-v1"
VALIDATOR_VERSION = "uag-01-validator-v1"

INTENTS = (
    "Company Analysis",
    "Portfolio Analysis",
    "Risk",
    "Policy",
    "Committee",
    "Observation",
    "Forecast",
    "Comparison",
    "Research",
    "Macro",
    "Market",
    "Search",
    "History",
    "Timeline",
)

LINEAGE_CHAIN = (
    "Evidence",
    "Reason",
    "Company Decision",
    "Portfolio Risk",
    "Policy Assessment",
    "Portfolio Decision",
    "Committee Resolution",
)
