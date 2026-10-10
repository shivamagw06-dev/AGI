"""Institutional dossier contract and deterministic completeness audit."""

from __future__ import annotations

from typing import Any

DOSSIER_SPEC_VERSION = "institutional-dossier-v2"

SECTIONS: tuple[str, ...] = (
    "company_identity",
    "business_model",
    "industry_economics",
    "competitive_position",
    "management_governance",
    "financial_performance",
    "sector_kpis",
    "earnings_quality",
    "capital_allocation",
    "balance_sheet_risk",
    "valuation",
    "scenarios",
    "catalysts",
    "risks",
    "causal_map",
    "market_implied_expectations",
    "thesis_change_conditions",
    "monitoring_dashboard",
    "evidence_gaps",
    "sources_provenance",
)


def audit_research(research: dict[str, Any] | None) -> dict[str, Any]:
    """Report section-level completeness without mistaking prose for evidence."""
    payload = research if isinstance(research, dict) else {}
    sections = payload.get("sections") if isinstance(payload.get("sections"), dict) else {}
    supported: list[str] = []
    partial: list[str] = []
    missing: list[str] = []
    for name in SECTIONS:
        section = sections.get(name) if isinstance(sections.get(name), dict) else {}
        has_text = bool(str(section.get("summary") or "").strip() or section.get("claims"))
        has_evidence = bool(section.get("evidence_ids"))
        declared = str(section.get("status") or "").upper()
        if has_text and has_evidence and declared not in {"DATA_REQUIRED", "CONFLICT", "STALE", "PIT_LIMITED"}:
            supported.append(name)
        elif has_text or has_evidence:
            partial.append(name)
        else:
            missing.append(name)
    score = len(supported) / len(SECTIONS) if SECTIONS else 0.0
    return {
        "spec_version": DOSSIER_SPEC_VERSION,
        "required_sections": len(SECTIONS),
        "supported_sections": supported,
        "partial_sections": partial,
        "missing_sections": missing,
        "section_coverage": round(score, 4),
        "status": "SUPPORTED" if not partial and not missing else ("PARTIAL" if supported else "DATA_REQUIRED"),
    }
