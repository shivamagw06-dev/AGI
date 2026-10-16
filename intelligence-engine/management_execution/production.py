"""FIRE-05 Mission Control / API façades."""

from __future__ import annotations

from typing import Any

from management_execution.flags import flags_dict, is_enabled
from management_execution.report import build_report
from management_execution.schema import (
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
        "role": "management_execution_temporal_engine",
        "consumes": [
            "business_intelligence",
            "evidence_fusion",
            "financial_warehouse",
            "derived_metrics",
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
        "judges_honesty": False,
        "fraud_detection": False,
        "legal_conclusions": False,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "fire_03_unchanged": True,
        "fire_04_unchanged": True,
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
        "objectives_tracked": None,
        "delivered_pct": None,
        "outstanding_pct": None,
        "superseded": None,
        "average_delivery_time": None,
        "execution_score": None,
        "confidence": None,
        "note": "Per-company boards via /management-execution/company/{ticker}",
        "issues_recommendations": False,
        "buy_sell": False,
        "judges_honesty": False,
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
        "objectives": report.get("objectives"),
        "n_objectives": len(report.get("objectives") or []),
        "findings": report.get("findings"),
        "by_status": report.get("by_status"),
        "timeline": report.get("timeline"),
        "score": report.get("score"),
        "mission_control": report.get("mission_control"),
        "inputs": report.get("inputs"),
        "issues_recommendations": False,
        "buy_sell": False,
        "forecast": False,
        "uses_llm": False,
        "judges_honesty": False,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "fire_03_unchanged": True,
        "fire_04_unchanged": True,
        "as_of": report.get("as_of"),
    }


def timeline(ticker: str, **kwargs: Any) -> dict[str, Any]:
    pack = company(ticker, **kwargs)
    rows = pack.get("timeline") or []
    return {
        "ok": pack.get("ok"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "timeline": rows,
        "n": len(rows),
        "issues_recommendations": False,
        "buy_sell": False,
        "judges_honesty": False,
        "as_of": now_iso(),
    }


def score(ticker: str, **kwargs: Any) -> dict[str, Any]:
    pack = company(ticker, **kwargs)
    return {
        "ok": pack.get("ok"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "score": pack.get("score"),
        "mission_control": pack.get("mission_control"),
        "issues_recommendations": False,
        "buy_sell": False,
        "judges_honesty": False,
        "as_of": now_iso(),
    }


def objectives(ticker: str, **kwargs: Any) -> dict[str, Any]:
    pack = company(ticker, **kwargs)
    rows = pack.get("objectives") or []
    return {
        "ok": pack.get("ok"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "objectives": rows,
        "n": len(rows),
        "findings": pack.get("findings"),
        "issues_recommendations": False,
        "buy_sell": False,
        "judges_honesty": False,
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
            "judges_honesty": False,
        }
    h = health()
    return {
        "status": h.get("status"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "issues_recommendations": False,
        "buy_sell": False,
        "judges_honesty": False,
    }


def admin_page() -> str:
    h = health()
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>FIRE-05 Management Execution</title></head>
<body>
<h1>FIRE-05 — Management Execution &amp; Temporal Evidence</h1>
<pre>{h}</pre>
<p>Execution tracking only. Never honesty judgments. No BUY/SELL. No LLM.</p>
</body></html>"""
