"""FIRE-02 façades — drivers & relationships (additive to FIRE-01)."""

from __future__ import annotations

from typing import Any

from financial_intelligence.drivers.engine import build_driver_pack
from financial_intelligence.drivers.schema import (
    ISSUES_RECOMMENDATIONS,
    PHASE,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    SPEC,
    SUBSYSTEM,
    VERSION,
    WORKSTREAM_ID,
)
from financial_intelligence.flags import is_enabled

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
        "role": "financial_relationship_driver_analysis",
        "consumes": ["financial_warehouse", "derived_metrics", "validation", "coverage"],
        "never_mutates_warehouse": True,
        "never_reads_collectors": True,
        "uses_llm": False,
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "buy_sell": False,
        "forecast": False,
        "fire_01_unchanged": True,
        "enabled": is_enabled(),
        "spec": SPEC,
        "as_of": now_iso(),
    }


def drivers(ticker: str, *, series_map: dict[str, list] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": WORKSTREAM_ID, "version": VERSION}
    pack = build_driver_pack(ticker, series_map=series_map)
    return {
        "ok": True,
        "enabled": True,
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "section": pack.get("section"),
        "title": pack.get("title"),
        "subsections": pack.get("subsections"),
        "relationships": pack.get("relationships"),
        "n_relationships": pack.get("n_relationships"),
        "driver_categories": pack.get("driver_categories"),
        "cash_quality_warnings": pack.get("cash_quality_warnings"),
        "working_capital_warnings": pack.get("working_capital_warnings"),
        "capital_allocation_observations": pack.get("capital_allocation_observations"),
        "high_severity_findings": pack.get("high_severity_findings"),
        "confidence": pack.get("confidence"),
        "evidence": pack.get("evidence"),
        "mission_control": pack.get("mission_control"),
        "issues_recommendations": False,
        "buy_sell": False,
        "forecast": False,
        "uses_llm": False,
        "fire_01_unchanged": True,
        "as_of": pack.get("as_of"),
    }


def relationships(ticker: str, *, series_map: dict[str, list] | None = None) -> dict[str, Any]:
    pack = drivers(ticker, series_map=series_map)
    return {
        "ok": pack.get("ok"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "relationships": pack.get("relationships") or [],
        "n": len(pack.get("relationships") or []),
        "confidence": pack.get("confidence"),
        "evidence": pack.get("evidence"),
        "issues_recommendations": False,
        "buy_sell": False,
        "as_of": now_iso(),
    }


def soft_slice_mission_control(ticker: str | None = None) -> dict[str, Any]:
    if ticker:
        pack = drivers(ticker)
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
