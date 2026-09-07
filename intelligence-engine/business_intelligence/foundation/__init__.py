"""Phase 3.0 — Business Intelligence Foundation.

Deterministic business reasoning layer. Ask wiring is intentionally disabled
until `ask_product_test/bi_acceptance_v1.py` passes ≥95%.
"""

from business_intelligence.foundation.production import (
    analyse,
    company,
    compare,
    dashboard,
    graph,
    health,
    industry,
    moat,
)

__all__ = [
    "analyse",
    "company",
    "compare",
    "dashboard",
    "graph",
    "health",
    "industry",
    "moat",
]
