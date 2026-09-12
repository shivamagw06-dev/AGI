"""Configurable institutional thresholds (FKB-01). Never hardcode inside FIRE."""

from __future__ import annotations

from typing import Any


def _t(
    id_: str,
    *,
    value: float,
    unit: str,
    description: str,
    sector_aware: bool = False,
    comparator: str = "absolute",
) -> dict[str, Any]:
    return {
        "id": id_,
        "value": value,
        "unit": unit,
        "description": description,
        "sector_aware": sector_aware,
        "comparator": comparator,
        "configurable": True,
        "performs_analysis": False,
    }


THRESHOLDS: dict[str, dict[str, Any]] = {
    "margin_expansion_bps": _t(
        "margin_expansion_bps",
        value=100.0,
        unit="bps",
        description="Minimum basis-point improvement to label margin expansion.",
        comparator="gte",
    ),
    "margin_compression_bps": _t(
        "margin_compression_bps",
        value=100.0,
        unit="bps",
        description="Minimum basis-point decline to label margin compression.",
        comparator="gte",
    ),
    "cash_conversion_strong": _t(
        "cash_conversion_strong",
        value=1.0,
        unit="ratio",
        description="OCF/PAT at or above this level indicates strong cash conversion.",
        comparator="gte",
    ),
    "cash_conversion_adequate": _t(
        "cash_conversion_adequate",
        value=0.8,
        unit="ratio",
        description="OCF/PAT at or above this level is adequate; below is weak.",
        comparator="gte",
    ),
    "cash_conversion_weak": _t(
        "cash_conversion_weak",
        value=0.7,
        unit="ratio",
        description="OCF/PAT below this level indicates weak cash conversion.",
        comparator="lt",
    ),
    "interest_coverage_warning": _t(
        "interest_coverage_warning",
        value=2.0,
        unit="x",
        description="Interest coverage below this level is a warning.",
        comparator="lt",
    ),
    "interest_coverage_stress": _t(
        "interest_coverage_stress",
        value=1.5,
        unit="x",
        description="Interest coverage below this level is stressed.",
        comparator="lt",
    ),
    "debt_to_ebitda_warning": _t(
        "debt_to_ebitda_warning",
        value=2.5,
        unit="x",
        description="Default Debt/EBITDA warning; override by sector when available.",
        sector_aware=True,
        comparator="gte",
    ),
    "debt_to_equity_high": _t(
        "debt_to_equity_high",
        value=1.5,
        unit="ratio",
        description="Debt/Equity at or above this level is high leverage.",
        comparator="gte",
    ),
    "debt_to_equity_low": _t(
        "debt_to_equity_low",
        value=0.5,
        unit="ratio",
        description="Debt/Equity at or below this level is low leverage.",
        comparator="lte",
    ),
    "roe_quality_default": _t(
        "roe_quality_default",
        value=15.0,
        unit="percent",
        description="Default ROE quality reference; sector-aware overrides apply.",
        sector_aware=True,
        comparator="gte",
    ),
    "roce_quality_default": _t(
        "roce_quality_default",
        value=15.0,
        unit="percent",
        description="Default ROCE quality reference; capital-intensive sectors may differ.",
        sector_aware=True,
        comparator="gte",
    ),
    "receivables_vs_revenue_excess_pct": _t(
        "receivables_vs_revenue_excess_pct",
        value=5.0,
        unit="percent_points",
        description="Receivables growth exceeding revenue growth by this amount flags WC deterioration.",
        comparator="gte",
    ),
    "operating_leverage_gap_pct": _t(
        "operating_leverage_gap_pct",
        value=1.0,
        unit="percent_points",
        description="Minimum EBIT vs revenue growth gap to label operating leverage change.",
        comparator="gte",
    ),
}


def all_thresholds() -> list[dict[str, Any]]:
    return [THRESHOLDS[k] for k in sorted(THRESHOLDS)]


def get_threshold(key: str, *, sector: str | None = None) -> dict[str, Any] | None:
    k = key.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "interestcoverage": "interest_coverage_warning",
        "interest_coverage": "interest_coverage_warning",
        "cash_conversion": "cash_conversion_adequate",
        "cashconversion": "cash_conversion_adequate",
        "marginexpansion": "margin_expansion_bps",
        "margincompression": "margin_compression_bps",
        "debt_ebitda": "debt_to_ebitda_warning",
    }
    # camelCase
    if k not in THRESHOLDS and any(c.isupper() for c in key):
        import re

        k = re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()
    k = aliases.get(k, k)
    row = THRESHOLDS.get(k)
    if not row:
        return None
    out = dict(row)
    if sector and out.get("sector_aware"):
        from financial_knowledge.sectors.overrides import sector_threshold

        ov = sector_threshold(sector, k)
        if ov is not None:
            out = {**out, **ov, "sector": sector.upper(), "overridden": True}
    return out
