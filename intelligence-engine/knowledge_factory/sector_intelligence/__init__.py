"""Institutional Sector Intelligence — Knowledge Factory enrichment (Sprint 5).

Teaches AGIB how industries behave. Phases 1–7 and Historical Depth untouched.
"""

from __future__ import annotations

from knowledge_factory.sector_intelligence.dashboard import sector_intelligence_dashboard
from knowledge_factory.sector_intelligence.pipeline import run_sector_intelligence_pipeline
from knowledge_factory.sector_intelligence.queries import (
    is_expensive_vs_sector_history,
    sector_valuation_during,
    sectors_outperform_when_rates_fall,
    should_use_dcf,
    strongest_roic_sector,
)
from knowledge_factory.sector_intelligence.schema import ISI_VERSION, SECTOR_UNIVERSE

__all__ = [
    "ISI_VERSION",
    "SECTOR_UNIVERSE",
    "is_expensive_vs_sector_history",
    "run_sector_intelligence_pipeline",
    "sector_intelligence_dashboard",
    "sector_valuation_during",
    "sectors_outperform_when_rates_fall",
    "should_use_dcf",
    "strongest_roic_sector",
]
