"""Forecast Provider Integration — India-first providers via Knowledge Platform.

Groww = primary live market · Yahoo = research/fundamentals · NSE/BSE = disclosures · IR = documents.
Forecast Intelligence consumes AGI-owned knowledge; live snapshots refresh only when stale.
"""

from forecast_provider_integration.engine import ForecastProviderIntegrationEngine

__all__ = ["ForecastProviderIntegrationEngine"]
