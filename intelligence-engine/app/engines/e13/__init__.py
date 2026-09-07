"""E13 Equity Fundamental L/S Engine — P0 (E13-001–005).

Consumes FeatureSnapshot + E01State + E14State only. No MarketDataClient.
No ML, analyst NLP, moat classifier, or fraud detection.
"""

from app.engines.e13.service import E13Service

__all__ = ["E13Service"]
