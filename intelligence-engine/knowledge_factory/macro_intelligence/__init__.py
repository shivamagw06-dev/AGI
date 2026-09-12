"""Institutional Macro Intelligence — Knowledge Factory enrichment (Sprint 6).

Teaches AGIB how the economy affects everything. Phases 1–7, Historical Depth,
and Sector Intelligence remain untouched.
"""

from __future__ import annotations

from knowledge_factory.macro_intelligence.dashboard import (
    institutional_macro_intelligence_dashboard,
    macro_intelligence_dashboard,
)
from knowledge_factory.macro_intelligence.pipeline import run_macro_intelligence_pipeline
from knowledge_factory.macro_intelligence.queries import (
    current_regime,
    macro_unavailable,
    most_similar_historical_regime,
    oil_shock_impacts,
    replay_2008,
    replay_covid,
    sectors_benefit_falling_rates,
    usd_strength_it,
)
from knowledge_factory.macro_intelligence.schema import IMI_VERSION, MACRO_UNIVERSE, REGIME_LABELS

__all__ = [
    "IMI_VERSION",
    "MACRO_UNIVERSE",
    "REGIME_LABELS",
    "current_regime",
    "institutional_macro_intelligence_dashboard",
    "macro_intelligence_dashboard",
    "macro_unavailable",
    "most_similar_historical_regime",
    "oil_shock_impacts",
    "replay_2008",
    "replay_covid",
    "run_macro_intelligence_pipeline",
    "sectors_benefit_falling_rates",
    "usd_strength_it",
]
