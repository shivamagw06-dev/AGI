"""E11 Sentiment & Alternative Data — P0 (E11-001–005).

Engineering WBS EPIC-015 / E11 Spec P0:
  entity map, news tone+decay, soft E11State envelope, API+ORCH, chaos kill-voter.

Consumes FeatureSnapshot + E01/E14 + SENT_*/NEWS_* PIT metadata only.
No MarketDataClient, social, transcripts, LLM, ML, broker/ownership (P1), altdata.
"""

from app.engines.e11.service import E11Service

__all__ = ["E11Service"]
