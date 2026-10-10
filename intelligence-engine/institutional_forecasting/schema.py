"""FG-01 — Forecast & Scenario Graph constants."""

from __future__ import annotations

FG_WORKSTREAM_ID = "FG-01"
FG_PRODUCT = "Forecast & Scenario Graph"
FG_VERSION = "fg-01-v1.0.0"
FG_SPEC = "docs/AGI_FG_01_FORECAST_SCENARIO_GRAPH.md"
FG_ROLE = "deterministic_scenario_propagation"
SCENARIO_ENGINE_VERSION = "fg-01-scenario-engine-v1"
PROPAGATION_VERSION = "fg-01-propagation-v1"
SENSITIVITY_VERSION = "fg-01-sensitivity-v1"
FORECAST_GRAPH_VERSION = "fg-01-forecast-graph-v1"

SCENARIO_NAMES = (
    "base",
    "bull",
    "bear",
    "stress",
    "optimistic",
    "custom",
)

DEFAULT_HORIZON = "12M"

# Explicit default probability mass (must sum to 1.0 for the standard set)
DEFAULT_PROBABILITIES = {
    "base": 0.50,
    "bull": 0.25,
    "bear": 0.25,
}
