"""Historical Market Intelligence Platform (HMKIP) — Sprint 12.2.

Immutable historical market memory for cycles, breadth, liquidity, volatility,
institutional flows, leadership and cross-asset behaviour. Never overwrites;
never calls external providers on Ask paths.

Programme short is HMKIP to avoid collision with Historical Macro Intelligence (HMIP).
"""

from historical_market_intelligence.engine import HistoricalMarketIntelligenceEngine

__all__ = ["HistoricalMarketIntelligenceEngine"]
