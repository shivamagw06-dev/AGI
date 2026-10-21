"""FIRE-01 Mission Control / API façades."""

from __future__ import annotations

from typing import Any

from financial_intelligence.flags import flags_dict, is_enabled
from financial_intelligence.report import build_report
from financial_intelligence.schema import (
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
        "role": "financial_narrative_trend_engine",
        "consumes": ["financial_warehouse", "derived_metrics", "validation", "coverage"],
        "never_mutates_warehouse": True,
        "never_reads_collectors": True,
        "uses_llm": False,
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "buy_sell": False,
        "forecast": False,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": SPEC,
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    """Aggregate ops board — empty universe stats until companies analysed."""
    h = health()
    return {
        "status": h["status"],
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "phase": PHASE,
        "financial_findings": None,
        "high_confidence_findings": None,
        "warnings": None,
        "evidence_coverage": None,
        "confidence_distribution": None,
        "note": "Per-company boards via /financial-intelligence/company/{ticker}",
        "issues_recommendations": False,
        "buy_sell": False,
        "spec": SPEC,
        "as_of": now_iso(),
    }


def company(ticker: str) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": WORKSTREAM_ID, "version": VERSION}
    report = build_report(ticker)
    return {
        "ok": True,
        "enabled": True,
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": report.get("ticker"),
        "executive_summary": report.get("executive_summary"),
        "findings": report.get("findings"),
        "evidence": report.get("evidence"),
        "confidence": report.get("confidence"),
        "sections": report.get("sections"),
        "mission_control": report.get("mission_control"),
        "warnings": report.get("warnings"),
        "issues_recommendations": False,
        "buy_sell": False,
        "forecast": False,
        "uses_llm": False,
        "as_of": report.get("as_of"),
    }


def findings(ticker: str) -> dict[str, Any]:
    pack = company(ticker)
    return {
        "ok": pack.get("ok"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "findings": pack.get("findings") or [],
        "n": len(pack.get("findings") or []),
        "confidence": pack.get("confidence"),
        "evidence": pack.get("evidence"),
        "issues_recommendations": False,
        "as_of": now_iso(),
    }


def soft_slice_mission_control(ticker: str | None = None) -> dict[str, Any]:
    """Optional soft board for Mission Control aggregate (additive)."""
    if ticker:
        pack = company(ticker)
        mc = pack.get("mission_control") or {}
        return {
            "status": "ok" if pack.get("ok") else "empty",
            "ticker": ticker.upper(),
            **mc,
            "issues_recommendations": False,
        }
    return {
        "status": health().get("status"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "issues_recommendations": False,
        "buy_sell": False,
    }


# --- FIRE-02 façades (additive; FIRE-01 company/findings shape unchanged) ---


def financial_drivers(ticker: str) -> dict[str, Any]:
    from financial_intelligence.drivers.production import drivers

    return drivers(ticker)


def financial_relationships(ticker: str) -> dict[str, Any]:
    from financial_intelligence.drivers.production import relationships

    return relationships(ticker)
