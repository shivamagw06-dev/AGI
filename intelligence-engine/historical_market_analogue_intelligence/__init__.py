"""Historical Market Analogue Intelligence (HMKAI) — Sprint 12.4.

Deterministic, explainable ranking of historical market environments most
similar to the current market across regime, breadth, liquidity, volatility,
flows, leadership and macro context.

Programme short is HMKAI to avoid collision with Historical Macro Analogue
Intelligence (HMAI).
"""

from historical_market_analogue_intelligence.engine import (
    HistoricalMarketAnalogueIntelligenceEngine,
)

__all__ = ["HistoricalMarketAnalogueIntelligenceEngine"]
