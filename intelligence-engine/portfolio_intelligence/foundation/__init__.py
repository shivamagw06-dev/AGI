"""Phase 3.3 — Portfolio Intelligence Engine (foundation).

Extends AGI Core. Consumes Investment Intelligence + Industry DNA.
Ask/KUL integration deferred until Acceptance = 100%.
Never issues BUY/SELL or trade recommendations.
Coexists with the legacy PIO soft layer under portfolio_intelligence.*.
"""

from portfolio_intelligence.foundation.schema import (
    ASK_WIRED,
    PI_VERSION,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    SPEC,
)

__all__ = ["PI_VERSION", "PROGRAMME", "SPEC", "ASK_WIRED", "RECOMMENDATION_POLICY"]
