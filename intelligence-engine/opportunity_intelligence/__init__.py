"""P4.5 Opportunity Intelligence Engine — institutional research prioritisation."""

from opportunity_intelligence.production import analyse, health, top, watchlist
from opportunity_intelligence.schema import ENGINE_CODE, VERSION

__all__ = ["ENGINE_CODE", "VERSION", "analyse", "health", "top", "watchlist"]
