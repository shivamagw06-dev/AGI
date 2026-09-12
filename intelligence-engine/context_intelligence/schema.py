"""Context Intelligence Engine (CIE) V1 — RQ1 Sprint 4 constitution."""

from __future__ import annotations

from typing import Any

CIE_VERSION = "1.0.0"
PROGRAMME = "RQ1 — Research Ontology"
PROGRAMME_SHORT = "CIE"
SPRINT = 4
SPRINT_NAME = "Context Intelligence Engine (CIE) V1"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
CONFIDENCE_THRESHOLD = 0.85
MAX_RUNTIME_MS_TARGET = 25

CONTEXT_DIMENSIONS: tuple[str, ...] = (
    "entity_context",
    "market_context",
    "macro_context",
    "historical_context",
    "time_context",
    "geographic_context",
    "industry_context",
    "portfolio_context",
    "expectation_context",
    "catalyst_context",
    "comparison_context",
    "scenario_context",
    "event_context",
    "user_context",
)

TIME_HORIZONS: tuple[str, ...] = (
    "Intraday",
    "Today",
    "This Week",
    "Quarter",
    "Year",
    "5 Years",
    "10 Years",
    "Long Term",
)

MARKET_REGIMES: tuple[str, ...] = (
    "Bull Market",
    "Bear Market",
    "Correction",
    "Recovery",
    "High Volatility",
    "Low Volatility",
    "Late-cycle expansion",
    "Early-cycle recovery",
    "Neutral",
)

MANDATORY_OUTPUT_FIELDS: tuple[str, ...] = (
    "question",
    "entity_context",
    "market_context",
    "macro_context",
    "historical_context",
    "time_context",
    "portfolio_context",
    "comparison_context",
    "event_context",
    "expectation_context",
    "scenario_context",
    "user_context",
    "context_importance",
    "research_context_card",
    "confidence",
    "executed_layers",
)


def constitution_dict() -> dict[str, Any]:
    return {
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": CIE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "extends": "Intent Intelligence / Entity Resolution / Research Objective Engine",
        "primary_question": "What surrounding context is required to answer this correctly?",
        "law": (
            "Institutional analysts never analyse a question in isolation. "
            "CIE discovers surrounding context before analysts begin reasoning."
        ),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_runtime_ms_target": MAX_RUNTIME_MS_TARGET,
        "context_dimensions": list(CONTEXT_DIMENSIONS),
        "mandatory_output_fields": list(MANDATORY_OUTPUT_FIELDS),
        "research_context_card": True,
        "success_criteria": {
            "context_accuracy": 0.98,
            "time_horizon_detection": 0.99,
            "market_context_detection": 0.95,
            "comparison_context_accuracy": 0.98,
            "portfolio_context_accuracy": 0.99,
            "average_runtime_ms": MAX_RUNTIME_MS_TARGET,
            "benchmark_minimum": 1000,
        },
    }
