"""Soft collectors — Phase-1 curated seeds + optional prior-layer context."""

from __future__ import annotations

from typing import Any

from knowledge_factory.alternative_data_intelligence.fixtures.series import (
    curated_observation_series,
)
from knowledge_factory.alternative_data_intelligence.registry.catalog import DATASET_REGISTRY


def collect_phase1_bundle() -> dict[str, Any]:
    """Collect Phase-1 registry metadata + curated observation seeds."""
    return {
        "datasets": dict(DATASET_REGISTRY),
        "observations": curated_observation_series(),
        "fabricated": False,
        "live_scrape": False,
        "note": "Phase-1 curated seeds from authoritative provider categories.",
    }
