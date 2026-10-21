"""Market Forecast Intelligence (MKFI) — Sprint 12.5.

Evidence-based Bull/Base/Bear market scenarios from AGI-owned knowledge.
Never predicts a single path. Never calls external providers.
Programme short MKFI avoids collision with Macroeconomic Forecast Intelligence (MFI).
"""

from market_forecast_intelligence.engine import MarketForecastIntelligenceEngine
from market_forecast_intelligence.schema import MKFI_VERSION, MarketForecastBundle, MarketForecastReport

__all__ = [
    "MKFI_VERSION",
    "MarketForecastBundle",
    "MarketForecastIntelligenceEngine",
    "MarketForecastReport",
]
