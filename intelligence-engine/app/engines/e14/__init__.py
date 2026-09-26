"""E14 Risk & Crowding Overlay — P0 rule-based vertical slice (E14-001–005).

Consumes Feature Registry + E01State only. No MarketDataClient. No ML/Bayes/SHAP.
"""

from app.engines.e14.service import E14Service

__all__ = ["E14Service"]
