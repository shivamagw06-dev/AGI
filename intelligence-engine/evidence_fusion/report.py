"""Evidence Fusion Report (EFR) assembly — sections 1–10."""

from __future__ import annotations

from typing import Any

from evidence_fusion.engine import build_fusion_pack
from evidence_fusion.schema import (
    ISSUES_RECOMMENDATIONS,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    REPORT_SECTIONS,
    RESULT_INSUFFICIENT,
    RESULT_NOT_SUPPORTED,
    RESULT_PARTIAL,
    RESULT_SUPPORTED,
    SPEC,
    VERSION,
    WORKSTREAM_ID,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _section(name: str, findings: list[dict[str, Any]], *, note: str | None = None) -> dict[str, Any]:
    return {
        "section": name,
        "n_findings": len(findings),
        "findings": findings,
        "narratives": [f.get("narrative") for f in findings if f.get("narrative")],
        "note": note,
        "uses_llm": False,
        "summarised": False,
    }


def build_report(
    ticker: str,
    *,
    pack: dict[str, Any] | None = None,
    series_map: dict[str, list[dict[str, Any]]] | None = None,
    fire01_findings: list[dict[str, Any]] | None = None,
    fire02_relationships: list[dict[str, Any]] | None = None,
    fire03_facts: list[dict[str, Any]] | None = None,
    coverage_pct: float | None = None,
    fire03_documents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    pack = pack or build_fusion_pack(
        ticker,
        series_map=series_map,
        fire01_findings=fire01_findings,
        fire02_relationships=fire02_relationships,
        fire03_facts=fire03_facts,
        coverage_pct=coverage_pct,
        fire03_documents=fire03_documents,
    )
    findings: list[dict[str, Any]] = list(pack.get("findings") or [])
    by = pack.get("by_result") or {}
    supported = by.get(RESULT_SUPPORTED) or [f for f in findings if f.get("fusion_result") == RESULT_SUPPORTED]
    partial = by.get(RESULT_PARTIAL) or [f for f in findings if f.get("fusion_result") == RESULT_PARTIAL]
    unsupported = by.get(RESULT_NOT_SUPPORTED) or [
        f for f in findings if f.get("fusion_result") == RESULT_NOT_SUPPORTED
    ]
    insufficient = by.get(RESULT_INSUFFICIENT) or [
        f for f in findings if f.get("fusion_result") == RESULT_INSUFFICIENT
    ]

    def _bucket(name: str) -> list[dict[str, Any]]:
        return [f for f in findings if f.get("consistency_bucket") == name]

    align = pack.get("alignment") or {}
    score = align.get("evidence_alignment_score")
    if score is None:
        alignment_prose = "Insufficient applicable fusion pairs to compute an evidence alignment score."
    elif score >= 70:
        alignment_prose = (
            f"Evidence alignment score {score}: quantitative and qualitative evidence are largely consistent. "
            "No recommendation is issued."
        )
    elif score >= 40:
        alignment_prose = (
            f"Evidence alignment score {score}: mixed consistency across management statements and financial evidence. "
            "No recommendation is issued."
        )
    else:
        alignment_prose = (
            f"Evidence alignment score {score}: material inconsistencies between management statements and financial evidence. "
            "No recommendation is issued."
        )

    top = (supported[:3] + unsupported[:3] + partial[:2] + insufficient[:2])[:8]
    sections: dict[str, Any] = {
        "executive_summary": _section(
            "executive_summary",
            top,
            note="Cross-evidence highlights only — not an investment thesis.",
        ),
        "supported_statements": _section("supported_statements", supported),
        "partially_supported_statements": _section("partially_supported_statements", partial),
        "unsupported_statements": _section("unsupported_statements", unsupported),
        "insufficient_evidence": _section(
            "insufficient_evidence",
            insufficient,
            note="Topics discussed without measurable financial evidence yet.",
        ),
        "financial_consistency": _section("financial_consistency", _bucket("financial_consistency")),
        "capital_allocation_consistency": _section(
            "capital_allocation_consistency", _bucket("capital_allocation_consistency")
        ),
        "risk_consistency": _section("risk_consistency", _bucket("risk_consistency")),
        "guidance_consistency": _section("guidance_consistency", _bucket("guidance_consistency")),
        "overall_evidence_alignment": {
            "section": "overall_evidence_alignment",
            "alignment": align,
            "prose": alignment_prose,
            "mission_control": pack.get("mission_control"),
            "uses_llm": False,
            "recommendation": None,
        },
    }
    for name in REPORT_SECTIONS:
        sections.setdefault(name, _section(name, []))

    return {
        "ok": True,
        "workstream_id": WORKSTREAM_ID,
        "programme": PROGRAMME,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "report_type": "EvidenceFusionReport",
        "report_code": "EFR",
        "sections": sections,
        "findings": findings,
        "by_result": {
            RESULT_SUPPORTED: supported,
            RESULT_PARTIAL: partial,
            RESULT_NOT_SUPPORTED: unsupported,
            RESULT_INSUFFICIENT: insufficient,
        },
        "alignment": align,
        "mission_control": pack.get("mission_control"),
        "inputs": pack.get("inputs"),
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "buy_sell": False,
        "forecast": False,
        "uses_llm": False,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "fire_03_unchanged": True,
        "spec": SPEC,
        "as_of": now_iso(),
    }
