"""Macroeconomic Forecast Intelligence (MFI) — Sprint 10.5.

Evidence-based Bull / Base / Bear macro scenarios from the Macro Knowledge Platform.
Never calls external providers. Does not predict a single future.
"""

from macroeconomic_forecast_intelligence.engine import (
    MacroeconomicForecastIntelligenceEngine,
)

__all__ = ["MacroeconomicForecastIntelligenceEngine"]
