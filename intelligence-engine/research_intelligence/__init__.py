"""Phase 3.4 — Research Intelligence Engine.

Institutional research workspace and long-lived research memory authority.
Extends AGI Core. Consumes Investment + Portfolio context conceptually.
Ask/KUL integration deferred until Acceptance = 100%.
Never issues BUY/SELL recommendations.
"""

from research_intelligence.schema import (
    ASK_WIRED,
    KNOWLEDGE_AUTHORITY,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    RI_VERSION,
    SPEC,
)

__all__ = [
    "RI_VERSION",
    "PROGRAMME",
    "SPEC",
    "ASK_WIRED",
    "RECOMMENDATION_POLICY",
    "KNOWLEDGE_AUTHORITY",
]
