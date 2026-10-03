"""IO-01 — Institutional Observation Engine constants."""

from __future__ import annotations

IO_WORKSTREAM_ID = "IO-01"
IO_PRODUCT = "Institutional Observation Engine"
IO_VERSION = "io-01-v1.0.0"
IO_SPEC = "docs/AGI_IO_01_INSTITUTIONAL_OBSERVATION.md"
IO_ROLE = "deterministic_institutional_monitoring"
OBSERVATION_ENGINE_VERSION = "io-01-observation-engine-v1"
DETECTOR_VERSION = "io-01-detector-v1"
CLASSIFIER_VERSION = "io-01-classifier-v1"
SIGNIFICANCE_VERSION = "io-01-significance-v1"

OBSERVATION_CATEGORIES = (
    "Quarterly Results",
    "Management Commentary",
    "Corporate Actions",
    "Shareholding",
    "Regulation",
    "Macro",
    "Valuation",
    "Forecast",
    "Risk",
    "Governance",
    "Sector",
    "News",
    "Market Structure",
    "Evidence",
    "Decision",
)

SEVERITIES = ("critical", "high", "medium", "low", "ignore")

RECOMMENDED_ACTIONS = (
    "Monitor",
    "Re-run valuation",
    "Re-run forecast",
    "Analyst review",
    "Portfolio review",
    "No action",
    "Recompute decision",
    "Refresh report",
)
