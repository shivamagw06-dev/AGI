"""Institutional Coverage Complete exit criteria."""

from __future__ import annotations

from typing import Any, Dict, Optional

from institutional_coverage_factory.config import load_config
from institutional_coverage_factory.schema import ICC_EXIT_CRITERIA
from institutional_coverage_factory.scorer.score import score_evidence_classes


def evaluate_icc(
    ticker: str,
    *,
    pack: Optional[Dict[str, Any]] = None,
    score: Optional[Dict[str, Any]] = None,
    kil: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """A company is ICC only when all exit criteria pass."""
    t = str(ticker or "").upper().strip()
    cfg = load_config()
    p = pack
    if p is None:
        try:
            from institutional_evidence.research_pack.builder import build_institutional_research_pack

            p = build_institutional_research_pack(t)
        except Exception:
            p = {}
    p = p if isinstance(p, dict) else {}

    sc = score if isinstance(score, dict) else score_evidence_classes(t, pack=p)
    missing = list(sc.get("missing_classes") or [])
    coverage_pct = float(sc.get("coverage_pct") or 0)

    fin = p.get("financials") or {}
    reg_items = ((p.get("evidence") or {}).get("registry") or {}).get("items") or []
    mem = p.get("company_memory") or {}
    readiness = p.get("research_readiness") or {}
    readiness_score = float(
        readiness.get("score")
        if readiness.get("score") is not None
        else (100.0 if p.get("research_ready") else 0.0)
    )

    kc = None
    if isinstance(kil, dict):
        kc = (kil.get("knowledge_confidence") or {}).get("knowledge_confidence")
    if kc is None:
        try:
            from institutional_evidence.integration.confidence.score import (
                compute_knowledge_confidence,
            )

            kc_res = compute_knowledge_confidence(ticker=t, pack=p)
            kc = kc_res.get("knowledge_confidence")
        except Exception:
            kc = None
    kc_val = float(kc) if kc is not None else 0.0

    claim_safe = bool(p.get("claim_safe"))
    citations = ((p.get("evidence") or {}).get("primary_citation_ids")) or []
    traceable = bool(claim_safe and citations)

    icc_threshold = float(cfg["institutional_coverage_threshold"])
    ready_threshold = float(cfg["research_readiness_threshold"])
    kc_threshold = float(cfg["knowledge_confidence_threshold"])

    checks = {
        "all_mandatory_evidence_present": coverage_pct >= icc_threshold and not missing,
        "canonical_financials_published": bool(fin.get("published") and (fin.get("periods") or [])),
        "evidence_registry_complete": len(reg_items) >= 2 and not any(
            c in missing
            for c in (
                "annual_reports",
                "quarterly_results",
                "financial_statements",
                "earnings_presentations",
                "earnings_call_transcripts",
                "shareholding",
                "corporate_actions",
            )
        ),
        "company_memory_populated": (mem.get("slot_coverage") or 0) >= 0.25
        or bool(mem.get("populated"))
        or "company_memory" not in missing,
        "knowledge_graph_refreshed": bool(p.get("knowledge_graph"))
        or "knowledge_graph" not in missing,
        "research_readiness_above_threshold": readiness_score >= ready_threshold
        or bool(p.get("research_ready")),
        "knowledge_confidence_above_threshold": kc_val >= kc_threshold,
        "claim_safe": claim_safe,
        "research_note_traceable": traceable,
    }
    for key in ICC_EXIT_CRITERIA:
        checks.setdefault(key, False)

    passed = sum(1 for v in checks.values() if v)
    total = len(ICC_EXIT_CRITERIA)
    complete = passed == total and coverage_pct >= icc_threshold

    status = "ICC_COMPLETE" if complete else (
        "BLOCKED" if missing and coverage_pct < float(cfg["coverage_threshold"]) else "IN_PROGRESS"
    )
    if complete:
        # Continuous monitoring once ICC achieved
        status = "ICC_COMPLETE"

    return {
        "ok": True,
        "ticker": t,
        "institutional_coverage_complete": complete,
        "status": status,
        "coverage_pct": coverage_pct,
        "missing_classes": missing,
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "passed": passed,
        "total": total,
        "thresholds": {
            "institutional_coverage": icc_threshold,
            "research_readiness": ready_threshold,
            "knowledge_confidence": kc_threshold,
            "operational_coverage": float(cfg["coverage_threshold"]),
        },
        "research_readiness_score": readiness_score,
        "knowledge_confidence": kc_val,
        "claim_safe": claim_safe,
        "exit_criteria": list(ICC_EXIT_CRITERIA),
    }


def icc_status_for(ticker: str) -> Dict[str, Any]:
    return evaluate_icc(ticker)
