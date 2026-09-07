"""AGIB Phase 2 — Financial Statement Intelligence.

The bridge between accounting (Phase 1 — how statements are BUILT) and
investment analysis (how statements are READ). This package interprets
a multi-period series of financial statements the way a first-year
equity research / IB analyst would: computing ratios and trends,
detecting earnings-quality issues and red flags, scoring financial
health, and generating evidence-grounded analyst narratives.

No LLM, no market data fetching, no valuation/recommendation logic —
every interpretation is deterministic and traceable to the numbers that
produced it.
"""

from __future__ import annotations

from financial_statement_intelligence.schema import FSI_VERSION, MODULE_CODE, PROGRAMME

__all__ = ["FSI_VERSION", "MODULE_CODE", "PROGRAMME"]
