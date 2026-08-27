"""FIRE-05 orchestration — objectives, evaluation, score, mission control."""

from __future__ import annotations

from datetime import date
from typing import Any

from management_execution.evaluate import evaluate_all
from management_execution.inventory import load_execution_inputs
from management_execution.objectives import normalize_objectives
from management_execution.schema import (
    STATUS_CANNOT,
    STATUS_DELIVERED,
    STATUS_NOT_YET,
    STATUS_PARTIAL,
    STATUS_SUPERSEDED,
    VERSION,
    WORKSTREAM_ID,
)
from management_execution.score import execution_score

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def confidence_distribution(findings: list[dict[str, Any]]) -> dict[str, int]:
    dist = {"High": 0, "Medium": 0, "Low": 0}
    for f in findings:
        c = f.get("confidence") or "Low"
        dist[c] = dist.get(c, 0) + 1
    return dist


def mission_control_board(score: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "objectives_tracked": score.get("objectives_tracked"),
        "delivered_pct": score.get("delivered_pct"),
        "outstanding_pct": score.get("outstanding_pct"),
        "superseded": score.get("superseded"),
        "average_delivery_time_months": score.get("average_delivery_months"),
        "execution_score": score.get("management_execution_score"),
        "confidence_distribution": confidence_distribution(findings),
        "delivered": score.get("delivered"),
        "partially_delivered": score.get("partially_delivered"),
        "cannot_yet_evaluate": score.get("cannot_yet_evaluate"),
    }


def build_timeline(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for f in findings:
        rows.append(
            {
                "objective_id": f.get("objective_id"),
                "original_period": f.get("original_period"),
                "statement": f.get("statement"),
                "category": f.get("category"),
                "status": f.get("current_status"),
                "evaluation_date": f.get("evaluation_date"),
                "delivery_months": f.get("delivery_months"),
                "evaluation_window": f.get("evaluation_window"),
                "evidence_ids": f.get("evidence_ids"),
            }
        )
    rows.sort(key=lambda r: (str(r.get("original_period") or ""), str(r.get("objective_id") or "")))
    return rows


def build_execution_pack(
    ticker: str,
    *,
    series_map: dict[str, list[dict[str, Any]]] | None = None,
    fire03_facts: list[dict[str, Any]] | None = None,
    fire03_documents: list[dict[str, Any]] | None = None,
    fire04_findings: list[dict[str, Any]] | None = None,
    coverage_pct: float | None = None,
    windows: list[str] | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    inv = load_execution_inputs(
        ticker,
        series_map=series_map,
        fire03_facts=fire03_facts,
        fire03_documents=fire03_documents,
        fire04_findings=fire04_findings,
        coverage_pct=coverage_pct,
    )
    facts = inv.get("fire03_facts") or []
    objectives = normalize_objectives(facts, ticker=inv.get("ticker") or ticker)
    findings = evaluate_all(
        objectives,
        series_map=inv.get("series") or {},
        later_facts=facts,
        windows=windows,
        as_of=as_of,
        coverage_pct=inv.get("coverage_pct"),
    )
    score = execution_score(findings, coverage_pct=inv.get("coverage_pct"))
    mc = mission_control_board(score, findings)
    by_status = {
        STATUS_DELIVERED: [f for f in findings if f.get("current_status") == STATUS_DELIVERED],
        STATUS_PARTIAL: [f for f in findings if f.get("current_status") == STATUS_PARTIAL],
        STATUS_NOT_YET: [f for f in findings if f.get("current_status") == STATUS_NOT_YET],
        STATUS_CANNOT: [f for f in findings if f.get("current_status") == STATUS_CANNOT],
        STATUS_SUPERSEDED: [f for f in findings if f.get("current_status") == STATUS_SUPERSEDED],
    }

    return {
        "ok": True,
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "ticker": inv.get("ticker"),
        "objectives": objectives,
        "n_objectives": len(objectives),
        "findings": findings,
        "n_findings": len(findings),
        "by_status": by_status,
        "timeline": build_timeline(findings),
        "score": score,
        "mission_control": mc,
        "fire04_refs_n": len(inv.get("fire04_findings") or []),
        "inputs": {
            "fire03_facts_n": len(facts),
            "metrics_with_series": sorted(k for k, v in (inv.get("series") or {}).items() if v),
            "coverage_pct": inv.get("coverage_pct"),
            "notes": inv.get("notes") or [],
        },
        "read_only": True,
        "uses_llm": False,
        "buy_sell": False,
        "forecast": False,
        "judges_honesty": False,
        "issues_recommendations": False,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "fire_03_unchanged": True,
        "fire_04_unchanged": True,
        "as_of": now_iso(),
    }
