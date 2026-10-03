"""FIRE-04 orchestration — build fusion pack + mission control board."""

from __future__ import annotations

from typing import Any

from evidence_fusion.confidence import confidence_distribution
from evidence_fusion.fusion import fuse_all
from evidence_fusion.inventory import load_fusion_inputs
from evidence_fusion.schema import (
    RESULT_INSUFFICIENT,
    RESULT_NOT_SUPPORTED,
    RESULT_PARTIAL,
    RESULT_SUPPORTED,
    VERSION,
    WORKSTREAM_ID,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def alignment_score(findings: list[dict[str, Any]]) -> dict[str, Any]:
    supported = sum(1 for f in findings if f.get("fusion_result") == RESULT_SUPPORTED)
    partial = sum(1 for f in findings if f.get("fusion_result") == RESULT_PARTIAL)
    unsupported = sum(1 for f in findings if f.get("fusion_result") == RESULT_NOT_SUPPORTED)
    insufficient = sum(1 for f in findings if f.get("fusion_result") == RESULT_INSUFFICIENT)
    applicable = supported + partial + unsupported
    score = round(100.0 * (supported + 0.5 * partial) / applicable, 2) if applicable else None
    return {
        "evidence_alignment_score": score,
        "supported": supported,
        "partially_supported": partial,
        "not_supported": unsupported,
        "insufficient_evidence": insufficient,
        "applicable_n": applicable,
        "total_findings": len(findings),
    }


def mission_control_board(
    findings: list[dict[str, Any]],
    *,
    document_coverage: int | None = None,
) -> dict[str, Any]:
    align = alignment_score(findings)
    return {
        "supported_findings": align["supported"],
        "conflicting_findings": align["not_supported"],
        "partial_findings": align["partially_supported"],
        "missing_evidence": align["insufficient_evidence"],
        "evidence_alignment_score": align["evidence_alignment_score"],
        "confidence_distribution": confidence_distribution(findings),
        "document_coverage": document_coverage,
        "total_fusion_findings": len(findings),
    }


def build_fusion_pack(
    ticker: str,
    *,
    series_map: dict[str, list[dict[str, Any]]] | None = None,
    fire01_findings: list[dict[str, Any]] | None = None,
    fire02_relationships: list[dict[str, Any]] | None = None,
    fire03_facts: list[dict[str, Any]] | None = None,
    coverage_pct: float | None = None,
    fire03_documents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    inv = load_fusion_inputs(
        ticker,
        series_map=series_map,
        fire01_findings=fire01_findings,
        fire02_relationships=fire02_relationships,
        fire03_facts=fire03_facts,
        coverage_pct=coverage_pct,
        fire03_documents=fire03_documents,
    )
    findings = fuse_all(
        fire03_facts=inv.get("fire03_facts") or [],
        series_map=inv.get("series") or {},
        fire01_findings=inv.get("fire01_findings") or [],
        fire02_relationships=inv.get("fire02_relationships") or [],
        coverage_pct=inv.get("coverage_pct"),
    )
    align = alignment_score(findings)
    doc_cov = len(inv.get("fire03_sources") or [])
    mc = mission_control_board(findings, document_coverage=doc_cov or None)

    by_result = {
        RESULT_SUPPORTED: [f for f in findings if f.get("fusion_result") == RESULT_SUPPORTED],
        RESULT_PARTIAL: [f for f in findings if f.get("fusion_result") == RESULT_PARTIAL],
        RESULT_NOT_SUPPORTED: [f for f in findings if f.get("fusion_result") == RESULT_NOT_SUPPORTED],
        RESULT_INSUFFICIENT: [f for f in findings if f.get("fusion_result") == RESULT_INSUFFICIENT],
    }

    return {
        "ok": True,
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": inv.get("ticker"),
        "findings": findings,
        "n_findings": len(findings),
        "by_result": by_result,
        "alignment": align,
        "mission_control": mc,
        "inputs": {
            "fire01_findings_n": len(inv.get("fire01_findings") or []),
            "fire02_relationships_n": len(inv.get("fire02_relationships") or []),
            "fire03_facts_n": len(inv.get("fire03_facts") or []),
            "metrics_with_series": sorted(k for k, v in (inv.get("series") or {}).items() if v),
            "coverage_pct": inv.get("coverage_pct"),
            "notes": inv.get("notes") or [],
        },
        "read_only": True,
        "uses_llm": False,
        "buy_sell": False,
        "forecast": False,
        "issues_recommendations": False,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "fire_03_unchanged": True,
        "as_of": now_iso(),
    }
