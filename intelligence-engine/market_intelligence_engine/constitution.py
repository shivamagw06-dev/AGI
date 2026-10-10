"""MIE Constitution v2.0 — product rules enforced in code, not LLM prompts."""

from __future__ import annotations

from typing import Any

CONSTITUTION_VERSION = "2.0"
ENGINE_VERSION = "2.0"

FORBIDDEN_ADVICE_TOKENS = (
    "buy",
    "sell",
    "hold",
    "strong buy",
    "strong sell",
    "accumulate",
    "trim",
    "investment advice",
    "you should",
    "we recommend",
)

CONFIDENCE_METHODOLOGY = (
    "Confidence measures evidence reliability — not expected return. "
    "Components: evidence completeness, financial statement coverage, "
    "historical observation depth, peer benchmark availability, and data quality (DQIV). "
    "Scores are deterministic; no LLM assignment."
)

VALIDATION_RULES: tuple[str, ...] = (
    "Every statistic has a source",
    "Every percentile has a historical baseline or explicit unavailability reason",
    "Every confidence score references defined methodology",
    "Every premium/discount identifies its comparison benchmark (premium_basis)",
    "Every research priority includes a transparent selection reason",
    "Every unavailable metric explains why it is unavailable",
    "Every widget includes coverage information",
    "No statement can be interpreted as investment advice",
    "Every conclusion is reproducible from warehouse data",
    "Every output is auditable",
)


def widget_provenance(
    *,
    source: str,
    engine: str = "market_intelligence_engine",
    version: str = ENGINE_VERSION,
    table: str | None = None,
    coverage: Any = None,
    snapshot_date: str | None = None,
    quality: str = "warehouse_validated",
) -> dict[str, Any]:
    return {
        "source": source,
        "engine": engine,
        "version": version,
        "warehouse_table": table,
        "coverage": coverage,
        "snapshot_date": snapshot_date,
        "data_quality": quality,
        "constitution": CONSTITUTION_VERSION,
    }
