"""FIRE-06 Mission Control / API façades."""

from __future__ import annotations

from typing import Any

from business_quality.flags import flags_dict, is_enabled
from business_quality.report import build_report
from business_quality.schema import (
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
        "role": "business_quality_engine",
        "consumes": [
            "financial_warehouse",
            "derived_metrics",
            "financial_intelligence",
            "business_intelligence",
            "evidence_fusion",
            "management_execution",
            "financial_knowledge.quality_weights",
        ],
        "never_mutates_warehouse": True,
        "never_reads_collectors": True,
        "uses_llm": False,
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "buy_sell": False,
        "valuation": False,
        "dcf": False,
        "forecast": False,
        "pillar_scores_primary": True,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "fire_03_unchanged": True,
        "fire_04_unchanged": True,
        "fire_05_unchanged": True,
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
        "quality_score": None,
        "pillar_scores": None,
        "confidence": None,
        "evidence_coverage": None,
        "score_trend": None,
        "note": "Per-company boards via /business-quality/company/{ticker}",
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
        "pillars": report.get("pillars"),
        "pillar_scores": report.get("pillar_scores"),
        "findings": report.get("findings"),
        "overall": report.get("overall"),
        "quality_score": report.get("quality_score"),
        "strengths": report.get("strengths"),
        "weaknesses": report.get("weaknesses"),
        "confidence": report.get("confidence"),
        "mission_control": report.get("mission_control"),
        "weights": report.get("weights"),
        "inputs": report.get("inputs"),
        "issues_recommendations": False,
        "buy_sell": False,
        "valuation": False,
        "uses_llm": False,
        "pillar_scores_primary": True,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "fire_03_unchanged": True,
        "fire_04_unchanged": True,
        "fire_05_unchanged": True,
        "as_of": report.get("as_of"),
    }


def quality(ticker: str, **kwargs: Any) -> dict[str, Any]:
    pack = company(ticker, **kwargs)
    return {
        "ok": pack.get("ok"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "quality_score": pack.get("quality_score"),
        "overall": pack.get("overall"),
        "pillar_scores": pack.get("pillar_scores"),
        "mission_control": pack.get("mission_control"),
        "pillars_primary": True,
        "issues_recommendations": False,
        "buy_sell": False,
        "as_of": now_iso(),
    }


def pillars(ticker: str, **kwargs: Any) -> dict[str, Any]:
    pack = company(ticker, **kwargs)
    return {
        "ok": pack.get("ok"),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "pillars": pack.get("pillars"),
        "pillar_scores": pack.get("pillar_scores"),
        "findings": pack.get("findings"),
        "n": len(pack.get("findings") or []),
        "note": "Pillar scores are the primary outputs; overall is derived.",
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
        "pillar_scores_primary": True,
        "issues_recommendations": False,
        "buy_sell": False,
    }


def admin_page() -> str:
    h = health()
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>FIRE-06 Business Quality</title></head>
<body>
<h1>FIRE-06 — Business Quality Engine</h1>
<pre>{h}</pre>
<p>Pillar-primary synthesis. No BUY/SELL. No valuation. No LLM.</p>
</body></html>"""
