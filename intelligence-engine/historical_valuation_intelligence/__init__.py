"""Historical Valuation Intelligence Engine (HVIE) — Phase 8.3B.

Reconstructs historical multiples from warehouse prices + normalized financial
statements + corporate actions. Never downloads vendor historical PE/PB/EV.
Gated by Phase 8.2A VPAE.
"""

from historical_valuation_intelligence.models import ENGINE_CODE, VERSION
from historical_valuation_intelligence.production import (
    bands,
    company,
    coverage,
    coverage_dashboard,
    health,
    history,
    percentiles,
    reconstruct,
    regimes,
    rerating,
    runtime_run,
    runtime_start,
    runtime_status,
    runtime_stop,
    statistics,
)
from historical_valuation_intelligence.sector_percentile import (
    load_sector_median_series,
    sector_historical_percentile,
)

__all__ = [
    "ENGINE_CODE",
    "VERSION",
    "health",
    "company",
    "history",
    "statistics",
    "bands",
    "percentiles",
    "regimes",
    "rerating",
    "coverage",
    "coverage_dashboard",
    "reconstruct",
    "runtime_status",
    "runtime_run",
    "runtime_start",
    "runtime_stop",
    "sector_historical_percentile",
    "load_sector_median_series",
]
