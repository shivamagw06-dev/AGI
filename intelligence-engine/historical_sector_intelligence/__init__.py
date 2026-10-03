"""Historical Sector Intelligence Platform (HSIP) — Sprint 11.2.

Immutable historical sector memory derived from company, macro, market,
event and research tips. Never overwrites; never calls external providers.
"""

from historical_sector_intelligence.engine import HistoricalSectorIntelligenceEngine

__all__ = ["HistoricalSectorIntelligenceEngine"]
