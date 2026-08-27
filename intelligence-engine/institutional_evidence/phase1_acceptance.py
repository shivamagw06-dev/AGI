"""Phase 1 — explicit Institutional Coverage Complete acceptance criteria."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .schema import (
    MIN_FINANCIAL_YEARS,
    PHASE1_ACCEPTANCE_CRITERIA,
    RESEARCH_READY_THRESHOLD,
)


def evaluate_institutional_coverage(
    ticker: str,
    *,
    pack: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    For each company, all criteria must pass before
    Institutional Coverage Complete.
    """
    from .research_pack.builder import build_institutional_research_pack
    from .timeline.company_timeline import build_company_timeline
    from .entity.resolve import resolve_entity

    t = str(ticker or "").upper().strip()
    p = pack if isinstance(pack, dict) else build_institutional_research_pack(t)
    fin = p.get("financials") or {}
    periods = fin.get("periods") or []
    annuals = [x for x in periods if (x or {}).get("period_type") == "annual"]
    quarters = [x for x in periods if (x or {}).get("period_type") == "quarterly"]
    reg_items = ((p.get("evidence") or {}).get("registry") or {}).get("items") or []
    dtypes = {str(i.get("document_type") or "") for i in reg_items}
    sources = {str(i.get("source") or "") for i in reg_items}
    mem = p.get("company_memory") or {}
    tl = build_company_timeline(t)
    resolved = resolve_entity(t)

    checks: Dict[str, bool] = {}
    # Approximate years from annual count (explicit 10y target)
    checks["financial_statements_10y"] = len(annuals) >= MIN_FINANCIAL_YEARS or (
        len(periods) >= MIN_FINANCIAL_YEARS * 2
    )
    checks["complete_annual_reports"] = (
        "annual_report" in dtypes or len(annuals) >= 1
    )
    checks["quarterly_history"] = len(quarters) >= 4 or "quarterly_results" in dtypes
    checks["earnings_presentations"] = "earnings_presentation" in dtypes
    checks["earnings_call_transcripts"] = (
        "earnings_transcript" in dtypes or "earnings_call_transcript" in dtypes
    )
    checks["corporate_actions"] = "corporate_action" in dtypes
    checks["shareholding_history"] = "shareholding" in dtypes
    checks["segment_history"] = bool(fin.get("segment_revenue"))
    checks["company_timeline"] = (tl.get("event_count") or 0) >= 3
    checks["canonical_financials"] = bool(fin.get("published") and periods)
    checks["company_memory"] = (mem.get("slot_coverage") or 0) >= 0.25
    checks["evidence_registry"] = len(reg_items) >= 2
    checks["knowledge_graph"] = bool(p.get("knowledge_graph"))
    checks["research_readiness_target"] = bool(
        p.get("research_ready")
        or ((p.get("research_readiness") or {}).get("score") or 0) >= RESEARCH_READY_THRESHOLD
    )
    checks["zero_unsupported_material_claims"] = bool(p.get("claim_safe"))
    checks["reproducible_research_note"] = bool(
        p.get("claim_safe") and (p.get("evidence") or {}).get("primary_citation_ids")
    )

    # Ensure all criteria keys present
    for key in PHASE1_ACCEPTANCE_CRITERIA:
        checks.setdefault(key, False)

    passed = sum(1 for v in checks.values() if v)
    total = len(PHASE1_ACCEPTANCE_CRITERIA)
    complete = passed == total
    return {
        "ok": True,
        "ticker": t,
        "entity_id": resolved.get("entity_id"),
        "institutional_coverage_complete": complete,
        "status": "Institutional Coverage Complete" if complete else "Coverage Incomplete",
        "passed": passed,
        "total": total,
        "pass_pct": round(100.0 * passed / max(1, total), 2),
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "criteria": list(PHASE1_ACCEPTANCE_CRITERIA),
        "scale_rule": "Only then expand beyond Top-20 / toward Nifty 500",
        "sources_seen": sorted(sources),
        "document_types_seen": sorted(dtypes),
    }
