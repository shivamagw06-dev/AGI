"""FIRE-04 Mission Control / API façades."""

from __future__ import annotations

from typing import Any

from evidence_fusion.flags import flags_dict, is_enabled
from evidence_fusion.report import build_report
from evidence_fusion.schema import (
    ISSUES_RECOMMENDATIONS,
    PHASE,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    RESULT_NOT_SUPPORTED,
    RESULT_SUPPORTED,
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
        "role": "evidence_fusion_engine",
        "consumes": [
            "financial_warehouse",
            "derived_metrics",
            "financial_intelligence",
            "financial_intelligence.drivers",
            "business_intelligence",
            "financial_knowledge",
        ],
        "never_mutates_warehouse": True,
        "never_reads_collectors": True,
        "uses_llm": False,
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "buy_sell": False,
        "forecast": False,
        "valuation": False,
        "sentiment": False,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "fire_03_unchanged": True,
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
        "supported_findings": None,
        "conflicting_findings": None,
        "missing_evidence": None,
        "evidence_alignment_score": None,
        "confidence_distribution": None,
        "document_coverage": None,
        "note": "Per-company boards via /evidence-fusion/company/{ticker}",
        "issues_recommendations": False,
        "buy_sell": False,
        "spec": SPEC,
        "as_of": now_iso(),
    }


def company(ticker: str, **kwargs: Any) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": WORKSTREAM_ID, "version": VERSION}
    report = build_report(ticker, **kwargs)
    return {
        "ok": True,
        "enabled": True,
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": report.get("ticker"),
        "report_type": report.get("report_type"),
        "sections": report.get("sections"),
        "findings": report.get("findings"),
        "n_findings": len(report.get("findings") or []),
        "by_result": report.get("by_result"),
        "alignment": report.get("alignment"),
        "mission_control": report.get("mission_control"),
        "inputs": report.get("inputs"),
        "issues_recommendations": False,
        "buy_sell": False,
        "forecast": False,
        "uses_llm": False,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "fire_03_unchanged": True,
        "as_of": report.get("as_of"),
    }


def supported(ticker: str, **kwargs: Any) -> dict[str, Any]:
    pack = company(ticker, **kwargs)
    rows = (pack.get("by_result") or {}).get(RESULT_SUPPORTED) or []
    return {
        "ok": pack.get("ok"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "supported": rows,
        "n": len(rows),
        "issues_recommendations": False,
        "buy_sell": False,
        "as_of": now_iso(),
    }


def conflicts(ticker: str, **kwargs: Any) -> dict[str, Any]:
    pack = company(ticker, **kwargs)
    rows = (pack.get("by_result") or {}).get(RESULT_NOT_SUPPORTED) or []
    return {
        "ok": pack.get("ok"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "conflicts": rows,
        "n": len(rows),
        "note": "Not Supported fusion findings only — no honesty judgment",
        "issues_recommendations": False,
        "buy_sell": False,
        "as_of": now_iso(),
    }


def alignment(ticker: str, **kwargs: Any) -> dict[str, Any]:
    pack = company(ticker, **kwargs)
    return {
        "ok": pack.get("ok"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "alignment": pack.get("alignment"),
        "mission_control": pack.get("mission_control"),
        "overall_evidence_alignment": (pack.get("sections") or {}).get("overall_evidence_alignment"),
        "issues_recommendations": False,
        "buy_sell": False,
        "as_of": now_iso(),
    }


def soft_slice_mission_control(ticker: str | None = None) -> dict[str, Any]:
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
    }


def admin_page() -> str:
    h = health()
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>FIRE-04 Evidence Fusion</title></head>
<body>
<h1>FIRE-04 — Evidence Fusion Engine</h1>
<pre>{h}</pre>
<p>Cross-evidence consistency only. No BUY/SELL. No LLM.</p>
</body></html>"""
