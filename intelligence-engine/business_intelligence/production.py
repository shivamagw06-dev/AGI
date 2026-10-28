"""FIRE-03 Mission Control / API façades."""

from __future__ import annotations

from typing import Any

from business_intelligence.flags import flags_dict, is_enabled
from business_intelligence.report import build_report
from business_intelligence.schema import (
    ISSUES_RECOMMENDATIONS,
    PHASE,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    SPEC,
    SUBSYSTEM,
    VERSION,
    WORKSTREAM_ID,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "workstream_id": WORKSTREAM_ID,
        "subsystem": SUBSYSTEM,
        "version": VERSION,
        "phase": PHASE,
        "role": "business_management_intelligence",
        "consumes": ["institutional_documents", "financial_knowledge.glossary"],
        "never_mutates_warehouse": True,
        "never_mutates_idi": True,
        "never_reads_collectors": True,
        "uses_llm": False,
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "buy_sell": False,
        "forecast": False,
        "sentiment": False,
        "is_summariser": False,
        "is_evidence_extraction_engine": True,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": SPEC,
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    h = health()
    return {
        "status": h["status"],
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "phase": PHASE,
        "business_documents_processed": None,
        "pages_indexed": None,
        "facts_extracted": None,
        "segment_coverage": None,
        "risk_coverage": None,
        "guidance_extracted": None,
        "confidence_distribution": None,
        "note": "Per-company boards via /business-intelligence/company/{ticker}",
        "issues_recommendations": False,
        "buy_sell": False,
        "spec": SPEC,
        "as_of": now_iso(),
    }


def company(
    ticker: str,
    *,
    documents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": WORKSTREAM_ID, "version": VERSION}
    report = build_report(ticker, documents=documents)
    return {
        "ok": True,
        "enabled": True,
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": report.get("ticker"),
        "report_type": report.get("report_type"),
        "sections": report.get("sections"),
        "facts": report.get("facts"),
        "n_facts": len(report.get("facts") or []),
        "BusinessProfile": report.get("BusinessProfile"),
        "ManagementStrategy": report.get("ManagementStrategy"),
        "SegmentAnalysis": report.get("SegmentAnalysis"),
        "RiskRegister": report.get("RiskRegister"),
        "OpportunityRegister": report.get("OpportunityRegister"),
        "GuidanceSummary": report.get("GuidanceSummary"),
        "CapitalAllocationNarrative": report.get("CapitalAllocationNarrative"),
        "packs": report.get("packs"),
        "sources": report.get("sources"),
        "confidence": report.get("confidence"),
        "mission_control": report.get("mission_control"),
        "issues_recommendations": False,
        "buy_sell": False,
        "forecast": False,
        "uses_llm": False,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "as_of": report.get("as_of"),
    }


def segments(ticker: str, *, documents: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    pack = company(ticker, documents=documents)
    rows = pack.get("SegmentAnalysis") or []
    return {
        "ok": pack.get("ok"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "SegmentAnalysis": rows,
        "n": len(rows),
        "issues_recommendations": False,
        "buy_sell": False,
        "as_of": now_iso(),
    }


def strategy(ticker: str, *, documents: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    pack = company(ticker, documents=documents)
    rows = pack.get("ManagementStrategy") or []
    return {
        "ok": pack.get("ok"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "ManagementStrategy": rows,
        "CapitalAllocationNarrative": pack.get("CapitalAllocationNarrative") or [],
        "n": len(rows),
        "issues_recommendations": False,
        "buy_sell": False,
        "as_of": now_iso(),
    }


def risks(ticker: str, *, documents: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    pack = company(ticker, documents=documents)
    rows = pack.get("RiskRegister") or []
    return {
        "ok": pack.get("ok"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "RiskRegister": rows,
        "n": len(rows),
        "note": "Disclosed risks only — no inferred risks",
        "issues_recommendations": False,
        "buy_sell": False,
        "as_of": now_iso(),
    }


def guidance(ticker: str, *, documents: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    pack = company(ticker, documents=documents)
    rows = pack.get("GuidanceSummary") or []
    return {
        "ok": pack.get("ok"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "GuidanceSummary": rows,
        "n": len(rows),
        "note": "Explicitly stated guidance / outlook only",
        "issues_recommendations": False,
        "buy_sell": False,
        "forecast": False,
        "as_of": now_iso(),
    }


def soft_slice_mission_control(ticker: str | None = None) -> dict[str, Any]:
    """Optional soft board for Mission Control aggregate (additive)."""
    if ticker:
        pack = company(ticker)
        mc = pack.get("mission_control") or {}
        return {
            "status": "ok" if pack.get("ok") else "empty",
            "workstream_id": WORKSTREAM_ID,
            "version": VERSION,
            "ticker": ticker.upper(),
            **mc,
            "issues_recommendations": False,
            "buy_sell": False,
        }
    h = health()
    return {
        "status": h.get("status"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "issues_recommendations": False,
        "buy_sell": False,
        "is_evidence_extraction_engine": True,
    }


def admin_page() -> str:
    h = health()
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>FIRE-03 Business Intelligence</title></head>
<body>
<h1>FIRE-03 — Business &amp; Management Intelligence</h1>
<pre>{h}</pre>
<p>Evidence extraction over official disclosures. No BUY/SELL. No LLM summaries.</p>
</body></html>"""
