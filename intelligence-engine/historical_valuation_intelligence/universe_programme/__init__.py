"""HVIE Universe Completion Programme (Phase 8.3A).

Persisted queue + eligibility + full-universe bootstrap + continuous runtime.
Never downloads vendor historical PE/PB/EV — reconstructs from warehouse inputs.
"""

from historical_valuation_intelligence.universe_programme import production
from historical_valuation_intelligence.universe_programme.models import (
    PROGRAMME_CODE,
    PROGRAMME_VERSION,
)

__all__ = [
    "PROGRAMME_CODE",
    "PROGRAMME_VERSION",
    "production",
]
