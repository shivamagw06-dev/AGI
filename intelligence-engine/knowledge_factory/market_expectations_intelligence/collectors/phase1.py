"""Phase-1 collectors — company guidance, actuals, AGIB timestamped forecasts."""

from __future__ import annotations

from typing import Any

from knowledge_factory.market_expectations_intelligence.fixtures.seeds import (
    curated_expectation_seeds,
    curated_narrative_seeds,
)


def collect_phase1_expectations() -> dict[str, Any]:
    return {
        "expectations": curated_expectation_seeds(),
        "narratives": curated_narrative_seeds(),
        "phase": 1,
        "sources": [
            "company_guidance",
            "company_earnings_release",
            "exchange_disclosure",
            "investor_presentation",
            "agib_internal_forecast",
        ],
        "licensed_consensus": False,
        "fabricated": False,
        "broker_reports_scraped": False,
    }
