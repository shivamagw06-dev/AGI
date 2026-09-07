"""E09 CTA Trend Engine — P0 (E09-001–005).

Consumes FeatureSnapshot + E01State + E14State + TECH_*/VOL_* registry features.
No MarketDataClient, ML, adaptive optimisation, or portfolio/cross-asset logic.
"""

from app.engines.e09.service import E09Service

__all__ = ["E09Service"]
