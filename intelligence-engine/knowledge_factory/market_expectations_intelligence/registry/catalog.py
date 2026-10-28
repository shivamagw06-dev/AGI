"""Expectation registry — metrics, sources, phase boundaries."""

from __future__ import annotations

from typing import Any

from knowledge_factory.market_expectations_intelligence.schema import (
    EXPECTATION_KINDS,
    IMEI_VERSION,
    METRICS,
    PHASE_1_SOURCES,
    PHASE_2_SOURCES,
)


def registry_snapshot() -> dict[str, Any]:
    return {
        "version": IMEI_VERSION,
        "delivery_phase": "phase_1_public_auditable",
        "metrics": list(METRICS),
        "expectation_kinds": list(EXPECTATION_KINDS),
        "phase_1_sources": list(PHASE_1_SOURCES),
        "phase_2_sources": list(PHASE_2_SOURCES),
        "phase_2_status": "optional_modular_collector",
        "forbidden": [
            "broker_report_scraping",
            "proprietary_research_reproduction",
            "fabricated_consensus",
            "recommendation_aggregation",
            "sentiment_analysis",
        ],
        "principle": "Markets price expectations, not reality.",
    }
