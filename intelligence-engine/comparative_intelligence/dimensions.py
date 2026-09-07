"""Comparison dimensions — module maps only (no analysis)."""

from __future__ import annotations

from typing import Any

from comparative_intelligence.schema import (
    COMPARISON_TYPES,
    DEFAULT_COMPARE_MODULES,
    MODULE_FIRE01,
    MODULE_FIRE02,
    MODULE_FIRE03,
    MODULE_FIRE04,
    MODULE_FIRE05,
    MODULE_FIRE06,
)

COMPARISON_MODULES: dict[str, tuple[str, ...]] = {
    "Institutional Comparison": DEFAULT_COMPARE_MODULES,
    "Business Quality Comparison": (MODULE_FIRE06, MODULE_FIRE01, MODULE_FIRE03),
    "Balance Sheet Comparison": (MODULE_FIRE02, MODULE_FIRE06),
    "Growth Comparison": (MODULE_FIRE01, MODULE_FIRE06),
    "Execution Comparison": (MODULE_FIRE05, MODULE_FIRE03),
    "Evidence Comparison": (MODULE_FIRE03, MODULE_FIRE04),
    "Cash Flow Comparison": (MODULE_FIRE01, MODULE_FIRE02, MODULE_FIRE06),
    "Financial Health Comparison": (MODULE_FIRE01, MODULE_FIRE02, MODULE_FIRE06),
}

# ICR section → how to pull comparable fields from FIRE payloads
DIMENSION_EXTRACTORS = {
    "business_quality_comparison": {
        "module": MODULE_FIRE06,
        "fields": ("overall_score", "quality_score", "overall_label", "pillars", "pillar_scores"),
    },
    "growth": {
        "module": MODULE_FIRE06,
        "pillar": "growth",
        "fallback_module": MODULE_FIRE01,
        "metric_hints": ("revenue", "growth"),
    },
    "margins": {
        "module": MODULE_FIRE01,
        "metric_hints": ("margin", "operating_margin", "gross_margin", "net_margin"),
        "pillar": "profitability",
        "pillar_module": MODULE_FIRE06,
    },
    "cash_flow": {
        "module": MODULE_FIRE06,
        "pillar": "cash",
        "fallback_module": MODULE_FIRE01,
        "metric_hints": ("cash", "fcf", "free_cash", "operating_cash"),
    },
    "balance_sheet": {
        "module": MODULE_FIRE06,
        "pillar": "balance_sheet",
        "fallback_module": MODULE_FIRE02,
        "metric_hints": ("debt", "leverage", "liquidity", "balance"),
    },
    "capital_allocation": {
        "module": MODULE_FIRE06,
        "pillar": "capital_allocation",
        "fallback_module": MODULE_FIRE01,
        "metric_hints": ("capex", "dividend", "buyback", "allocation"),
    },
    "management_execution": {
        "module": MODULE_FIRE05,
        "fields": ("objectives", "assessments", "summary", "score"),
    },
    "evidence_alignment": {
        "module": MODULE_FIRE04,
        "fields": ("assessments", "claims", "summary", "status"),
    },
}


def modules_for_comparison_type(comparison_type: str | None) -> tuple[str, ...]:
    raw = (comparison_type or "").strip()
    if raw in COMPARISON_MODULES:
        return COMPARISON_MODULES[raw]
    key = raw.lower().replace("_", " ").replace("-", " ").strip()
    for name in COMPARISON_TYPES:
        if name.lower() == key:
            return COMPARISON_MODULES[name]
    return DEFAULT_COMPARE_MODULES


def normalize_comparison_type(comparison_type: str | None) -> str:
    raw = (comparison_type or "").strip()
    if not raw:
        return "Institutional Comparison"
    if raw in COMPARISON_MODULES:
        return raw
    key = raw.lower().replace("_", " ").replace("-", " ").strip()
    for name in COMPARISON_TYPES:
        if name.lower() == key or name.lower().replace(" ", "") == key.replace(" ", ""):
            return name
    return "Institutional Comparison"


def comparison_catalog() -> list[dict[str, Any]]:
    return [
        {
            "comparison_type": name,
            "modules": list(COMPARISON_MODULES[name]),
            "compares_only": True,
        }
        for name in COMPARISON_MODULES
    ]
