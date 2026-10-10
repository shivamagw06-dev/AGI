"""Historical Intelligence Engine — coverage-aware reasoning over warehouse history.

The warehouse stores what happened. This package explains what it meant, and it
is honest about where the evidence stops. No module here collects data: every
input arrives from the Institutional Data Warehouse.

The rule that governs everything: a conclusion may only be drawn inside the
observed window. Where history is missing, the answer says so rather than
extrapolating.
"""

from historical_intelligence.coverage import metric_coverage, company_coverage
from historical_intelligence.span_guard import guard

__all__ = ["metric_coverage", "company_coverage", "guard"]
