"""Canonical facade over AGI's existing industry and sector knowledge.

Industry DNA explains how an industry works. SIF explains how an analyst should
underwrite it. This module joins those stores without copying either one.
"""

from __future__ import annotations

from typing import Any

from industry_intelligence.dna_catalog import INDUSTRY_DNA
from industry_intelligence.registry import resolve_industry
from sif.frameworks import FRAMEWORKS


_SIF_TO_DNA = {
    "consumer_internet": "internet_platforms",
    "healthcare": "hospitals",
    "steel": "metals",
}
_DNA_TO_SIF = {value: key for key, value in _SIF_TO_DNA.items()}


def _resolve_key(value: str | None) -> str | None:
    resolved = resolve_industry(value)
    if resolved:
        return resolved
    raw = str(value or "").strip().lower().replace(" ", "_")
    if raw in FRAMEWORKS:
        return _SIF_TO_DNA.get(raw, raw)
    return None


def framework_for(industry: str | None) -> dict[str, Any]:
    """Return the complete governed analysis contract for an industry."""
    key = _resolve_key(industry)
    dna = INDUSTRY_DNA.get(key or "")
    sif_key = key if key in FRAMEWORKS else _DNA_TO_SIF.get(key or "")
    sector = FRAMEWORKS.get(sif_key or "")
    if dna is None and sector is None:
        return {
            "ok": False,
            "status": "INDUSTRY_UNAVAILABLE",
            "requested_industry": industry,
            "fabricated": False,
        }

    dna_payload = dna.to_dict() if dna else None
    sector_payload = sector.to_dict() if sector else None
    dna_kpis = [item.to_dict() for item in (dna.kpis if dna else [])]
    required_kpis = list(sector.required_kpis) if sector else [item["key"] for item in dna_kpis]
    valuation = list(sector.valuation_methodology) if sector else list(dna.valuation_methods if dna else [])
    risks = list(sector.risk_factors) if sector else list(dna.typical_risks if dna else [])
    monitoring = list(sector.monitoring_signals) if sector else [item["key"] for item in dna_kpis]

    missing_layers = []
    if dna is None:
        missing_layers.append("industry_dna")
    if sector is None:
        missing_layers.append("sector_analysis_framework")
    return {
        "ok": True,
        "status": "COMPLETE" if not missing_layers else "PARTIAL",
        "industry_key": key or (sector.sector_id if sector else None),
        "industry_name": dna.name if dna else sector.name,
        "classification": {
            "industry_dna_key": dna.key if dna else None,
            "sector_framework_key": sector.sector_id if sector else None,
        },
        "business_model": {
            "revenue_drivers": list(dna.revenue_drivers) if dna else [],
            "cost_drivers": list(dna.cost_drivers) if dna else [],
            "margin_drivers": list(dna.margin_drivers) if dna else [],
            "capital_intensity": dna.capital_intensity if dna else None,
            "working_capital": dna.working_capital if dna else None,
        },
        "kpis": {"required": required_kpis, "priority": list(sector.priority_metrics) if sector else required_kpis, "definitions": dna_kpis},
        "valuation": {"methods": valuation, "preferred_multiples": list(sector.preferred_multiples) if sector else [], "why": dna.valuation_why if dna else None},
        "forecast_drivers": list(sector.forecast_drivers) if sector else list(dna.value_drivers if dna else []),
        "causal_context": {
            "why_margins": dna.why_margins if dna else None,
            "why_roic": dna.why_roic if dna else None,
            "why_leverage": dna.why_leverage if dna else None,
            "macro_sensitivity": list(dna.macro_sensitivity) if dna else [],
        },
        "risks": risks,
        "monitoring": monitoring,
        "decision_framework": list(sector.decision_framework) if sector else [],
        "common_mistakes": list(sector.common_mistakes) if sector else [],
        "coverage": {"industry_dna": dna is not None, "sector_analysis_framework": sector is not None, "missing_layers": missing_layers},
        "sources": {"industry_dna": dna_payload, "sector_framework": sector_payload},
        "fabricated": False,
    }


def coverage_report() -> dict[str, Any]:
    keys = sorted(set(INDUSTRY_DNA) | {_SIF_TO_DNA.get(key, key) for key in FRAMEWORKS})
    rows = [framework_for(key) for key in keys]
    return {
        "industries": len(rows),
        "complete": sum(row.get("status") == "COMPLETE" for row in rows),
        "partial": sum(row.get("status") == "PARTIAL" for row in rows),
        "rows": [{"industry_key": row.get("industry_key"), "status": row.get("status"), **(row.get("coverage") or {})} for row in rows],
        "fabricated": False,
    }
