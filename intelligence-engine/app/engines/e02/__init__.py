"""E02 Factor & Style Engine — P0 exposures (E02-001–005).

Consumes FeatureSnapshot + E01State + E14State only. No MarketDataClient.
Timing/rotation/ML remain feature-flagged placeholders.
"""

from app.engines.e02.service import E02Service

__all__ = ["E02Service"]
