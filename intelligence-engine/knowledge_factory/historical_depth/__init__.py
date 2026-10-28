"""Historical Depth — Knowledge Factory enrichment (Sprint 4).

Reasoning Architecture Frozen v1.0. No new engines. Point-in-time integrity
is mandatory: queries never use evidence with available_from > as_of.
"""

from __future__ import annotations

from knowledge_factory.historical_depth.dashboard import historical_depth_dashboard
from knowledge_factory.historical_depth.pipeline import run_historical_pipeline
from knowledge_factory.historical_depth.queries import (
    largest_crisis_drawdown,
    pe_above_percentile,
    performance_across_rate_hiking_cycles,
    valuation_during,
)
from knowledge_factory.historical_depth.schema import HD_VERSION
from knowledge_factory.historical_depth.time_travel import compare_as_of, state_as_of

__all__ = [
    "HD_VERSION",
    "compare_as_of",
    "historical_depth_dashboard",
    "largest_crisis_drawdown",
    "pe_above_percentile",
    "performance_across_rate_hiking_cycles",
    "run_historical_pipeline",
    "state_as_of",
    "valuation_during",
]
