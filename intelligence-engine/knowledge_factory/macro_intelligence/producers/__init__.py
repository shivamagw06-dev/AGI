"""Macro derived producers (knowledge only)."""

from knowledge_factory.macro_intelligence.producers.impacts import (
    relationship,
    sectors_for_driver,
    shock_impact,
    usd_strength_it_impact,
)
from knowledge_factory.macro_intelligence.producers.regime import (
    classify_as_of,
    classify_current,
    classify_snapshot,
)
from knowledge_factory.macro_intelligence.producers.similarity import replay_crisis, similar_regimes

__all__ = [
    "classify_as_of",
    "classify_current",
    "classify_snapshot",
    "relationship",
    "replay_crisis",
    "sectors_for_driver",
    "shock_impact",
    "similar_regimes",
    "usd_strength_it_impact",
]
