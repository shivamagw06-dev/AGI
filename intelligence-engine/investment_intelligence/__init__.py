"""Phase 3.2 — Investment Intelligence Engine.

Extends AGI Core. Consumes Business Intelligence + Industry DNA.
Ask/KUL integration deferred until Acceptance = 100%.
Never issues BUY/SELL recommendations.
"""

from investment_intelligence.schema import (
    ASK_WIRED,
    IIE_VERSION,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    SPEC,
)

__all__ = ["IIE_VERSION", "PROGRAMME", "SPEC", "ASK_WIRED", "RECOMMENDATION_POLICY"]
