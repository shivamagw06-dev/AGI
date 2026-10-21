"""Continuous Market Knowledge Platform (CMKTP) — Sprint 12.1.

Transforms live market tips into institutional Market Knowledge Objects.
Not a market data service. Ask never collects or constructs.
"""

from continuous_market_knowledge.engine import ContinuousMarketKnowledgeEngine

__all__ = ["ContinuousMarketKnowledgeEngine"]
