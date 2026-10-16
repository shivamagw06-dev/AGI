"""E05 Event-Driven & Special Situations — P0 (E05-001–005).

Consumes FeatureSnapshot + E01/E14 + available EVENT_* + PIT corporate event objects.
Calendar / CA / guidance / basic surprise / decay only.
No MarketDataClient, deal probability, transcripts, ML, or event forecasting.
"""

from app.engines.e05.service import E05Service

__all__ = ["E05Service"]
