"""IDS-01 — Institutional Decision System constants."""

from __future__ import annotations

IDS_WORKSTREAM_ID = "IDS-01"
IDS_PRODUCT = "Institutional Decision System"
IDS_VERSION = "ids-01-v1.0.0"
IDS_SPEC = "docs/AGI_IDS_01_INSTITUTIONAL_DECISION.md"
IDS_ROLE = "deterministic_institutional_decision"
DECISION_ENGINE_VERSION = "ids-01-decision-engine-v1"
DECISION_VALIDATOR_VERSION = "ids-01-decision-validator-v1"
DECISION_GRAPH_VERSION = "ids-01-decision-graph-v1"

RECOMMENDATIONS = ("BUY", "HOLD", "SELL", "AVOID", "WATCH")
CONVICTIONS = ("LOW", "MEDIUM", "HIGH")
HORIZONS = ("Short", "Medium", "Long")

# Ordered decision graph nodes (stored with every decision).
DECISION_GRAPH_NODES = (
    "business_quality",
    "financial_quality",
    "valuation",
    "risk",
    "macro",
    "management",
    "recommendation",
)

DEFAULT_MONITORING = (
    "Quarterly earnings",
    "Conference calls",
    "Corporate actions",
    "Management guidance",
    "Macro developments",
)
