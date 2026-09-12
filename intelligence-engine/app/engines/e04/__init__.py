"""E04 Statistical Arbitrage & Relative Value — P0 (E04-001–005).

Consumes FeatureSnapshot + E01/E14/E02/E03 + available RVAL_* metadata.
OLS/EG/half-life only. No MarketDataClient, Kalman, ML, ETF basis, or portfolio.
"""

from app.engines.e04.service import E04Service

__all__ = ["E04Service"]
