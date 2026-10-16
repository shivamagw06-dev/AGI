"""Management Execution Report (MER) — sections 1–10."""

from __future__ import annotations

from typing import Any

from management_execution.engine import build_execution_pack
from management_execution.schema import (
    ISSUES_RECOMMENDATIONS,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    REPORT_SECTIONS,
    SPEC,
    STATUS_CANNOT,
    STATUS_DELIVERED,
    STATUS_NOT_YET,
    STATUS_PARTIAL,
    STATUS_SUPERSEDED,
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


def build_report(ticker: str, **kwargs: Any) -> dict[str, Any]:
    pack = kwargs.pop("pack", None) or build_execution_pack(ticker, **kwargs)
    findings: list[dict[str, Any]] = list(pack.get("findings") or [])
    by = pack.get("by_status") or {}
    delivered = by.get(STATUS_DELIVERED) or []
    partial = by.get(STATUS_PARTIAL) or []
    outstanding = by.get(STATUS_NOT_YET) or []
    superseded = by.get(STATUS_SUPERSEDED) or []
    cannot = by.get(STATUS_CANNOT) or []

    capital = [f for f in findings if f.get("bucket") == "capital_allocation_delivery"]
    strategy = [f for f in findings if f.get("bucket") == "strategy_delivery"]
    score = pack.get("score") or {}
    mes = score.get("management_execution_score")
    if mes is None:
        prose = "Insufficient applicable objectives to compute a Management Execution Score."
    else:
        prose = (
            f"Management Execution Score {mes} from {score.get('delivered', 0)} delivered, "
            f"{score.get('partially_delivered', 0)} partially delivered, and "
            f"{score.get('outstanding', 0)} outstanding applicable objectives. "
            "No honesty judgment and no recommendation is issued."
        )

    top = (delivered[:3] + outstanding[:3] + partial[:2] + superseded[:2] + cannot[:2])[:8]
    sections: dict[str, Any] = {
        "executive_summary": _section(
            "executive_summary",
            top,
            note="Temporal execution highlights only — not an investment thesis or honesty assessment.",
        ),
        "delivered_objectives": _section("delivered_objectives", delivered),
        "partially_delivered": _section("partially_delivered", partial),
        "outstanding_objectives": _section(
            "outstanding_objectives",
            outstanding,
            note="Not Yet Delivered — evidence-backed classification only.",
        ),
        "superseded_objectives": _section(
            "superseded_objectives",
            superseded,
            note="Superseded is not classified as failure.",
        ),
        "cannot_yet_evaluate": _section("cannot_yet_evaluate", cannot),
        "execution_timeline": {
            "section": "execution_timeline",
            "timeline": pack.get("timeline") or [],
            "n": len(pack.get("timeline") or []),
            "uses_llm": False,
        },
        "capital_allocation_delivery": _section("capital_allocation_delivery", capital),
        "strategy_delivery": _section("strategy_delivery", strategy),
        "overall_execution_score": {
            "section": "overall_execution_score",
            "score": score,
            "prose": prose,
            "mission_control": pack.get("mission_control"),
            "uses_llm": False,
            "recommendation": None,
            "judges_honesty": False,
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
        "report_type": "ManagementExecutionReport",
        "report_code": "MER",
        "sections": sections,
        "objectives": pack.get("objectives"),
        "findings": findings,
        "by_status": by,
        "timeline": pack.get("timeline"),
        "score": score,
        "mission_control": pack.get("mission_control"),
        "inputs": pack.get("inputs"),
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "buy_sell": False,
        "forecast": False,
        "uses_llm": False,
        "judges_honesty": False,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "fire_03_unchanged": True,
        "fire_04_unchanged": True,
        "spec": SPEC,
        "as_of": now_iso(),
    }
