"""WS03 Feature Registry (WBS FEAT-001–005).

Institutional feature engineering surface. Research engines must consume
FeatureRegistry outputs only — they may not compute RSI/EMA/ATR/etc. internally.
"""

from app.features.models import (
    FeatureMetadata,
    FeatureSnapshot,
    FeatureValue,
    HistoricalFeatureSeries,
)
from app.features.service import FeatureRegistryService

__all__ = [
    "FeatureMetadata",
    "FeatureValue",
    "FeatureSnapshot",
    "HistoricalFeatureSeries",
    "FeatureRegistryService",
]
