"""E08 Volatility & Options Intelligence — P0 (E08-001–005).

Consumes FeatureSnapshot + E01State + E14State + VOL_*/OPTIONS_* registry features.
No MarketDataClient, dealer positioning, options surface, gamma model, or ML.
"""

from app.engines.e08.service import E08Service

__all__ = ["E08Service"]
