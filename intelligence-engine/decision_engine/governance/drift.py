"""Thesis drift + recommendation delta vs previous institutional analysis."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stance_bucket(status: str | None, band: str | None, action: str | None) -> str:
    blob = f"{status or ''} {band or ''} {action or ''}".lower()
    if "inconclusive" in blob or "deferred" in blob or "withheld" in blob:
        return "Inconclusive"
    if "constructive" in blob or "accumulate" in blob or band == "high_conviction_allowed":
        return "Constructive"
    if "avoid" in blob or "cautious" in blob:
        return "Cautious"
    if "watch" in blob or band == "watchlist":
        return "Neutral"
    if "selective" in blob or "moderate" in blob:
        return "Neutral"
    return "Neutral"


def _drift_level(prev: str, cur: str) -> str:
    if prev == cur:
        return "None"
    order = ["Inconclusive", "Cautious", "Neutral", "Constructive"]
    try:
        d = abs(order.index(prev) - order.index(cur))
    except ValueError:
        return "Moderate"
    if d >= 2:
        return "High"
    return "Moderate"


def compute_thesis_drift(
    *,
    previous: dict[str, Any] | None,
    current_gate: dict[str, Any] | None,
    current_decision: dict[str, Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prev = previous if isinstance(previous, dict) else {}
    gate = current_gate if isinstance(current_gate, dict) else {}
    decision = current_decision if isinstance(current_decision, dict) else {}
    ca = company_analysis if isinstance(company_analysis, dict) else {}

    prev_thesis = str(
        prev.get("thesis_stance")
        or prev.get("investment_thesis_status")
        or prev.get("house_view")
        or "Unknown"
    )
    # Normalize previous stored bucket if already a stance label
    if prev_thesis in {"Constructive", "Neutral", "Cautious", "Inconclusive"}:
        prev_bucket = prev_thesis
    else:
        prev_bucket = _stance_bucket(
            str(prev.get("investment_thesis_status") or prev_thesis),
            str(prev.get("readiness_band") or ""),
            str(prev.get("action") or ""),
        )

    cur_bucket = _stance_bucket(
        str(gate.get("investment_thesis_status") or decision.get("investment_thesis_status")),
        str(gate.get("band") or ""),
        str(decision.get("action") or ""),
    )
    if gate.get("investment_thesis_status") == "INCONCLUSIVE":
        cur_bucket = "Inconclusive"

    reasons: list[str] = []
    fin = ca.get("financial_intelligence") or {}
    for x in (fin.get("what_deteriorated") or [])[:3]:
        reasons.append(str(x).replace("_", " "))
    for x in (fin.get("what_improved") or [])[:2]:
        reasons.append("Improved: " + str(x).replace("_", " "))
    for c in (gate.get("reason_bullets") or [])[:4]:
        if c not in reasons:
            reasons.append(str(c))
    if not reasons and prev_bucket != cur_bucket:
        reasons.append("Readiness / evidence profile changed since last analysis")
    if not reasons:
        reasons.append("No material thesis change detected")

    level = _drift_level(prev_bucket, cur_bucket) if prev else "n/a"
    return {
        "previous_thesis": prev_bucket if prev else None,
        "current_thesis": cur_bucket,
        "thesis_drift": level if prev else "n/a",
        "reasons": reasons[:6],
        "previous_at": prev.get("recorded_at") or prev.get("generated_at"),
        "note": "Thesis drift tracks stance change — not merely score movement.",
    }


def compute_recommendation_delta(
    *,
    previous: dict[str, Any] | None,
    current_gate: dict[str, Any] | None,
) -> dict[str, Any]:
    prev = previous if isinstance(previous, dict) else {}
    gate = current_gate if isinstance(current_gate, dict) else {}
    cur_ready = gate.get("recommendation_readiness_pct")
    if cur_ready is None:
        cur_ready = gate.get("evidence_confidence_pct")
    prev_ready = prev.get("recommendation_readiness_pct")
    if prev_ready is None:
        prev_ready = prev.get("evidence_confidence_pct")

    reasons = list(gate.get("reason_bullets") or [])[:6]
    if not reasons:
        reasons = list(gate.get("additional_evidence_required") or [])[:4]
    delta = None
    if prev_ready is not None and cur_ready is not None:
        try:
            delta = round(float(cur_ready) - float(prev_ready), 1)
        except (TypeError, ValueError):
            delta = None

    driver = "data_changed"
    if gate.get("investment_thesis_status") == "FORMED" and prev.get("investment_thesis_status") == "INCONCLUSIVE":
        driver = "evidence_improved"
    elif gate.get("investment_thesis_status") == "INCONCLUSIVE" and float(cur_ready or 0) < float(prev_ready or 100):
        driver = "data_changed_or_stale"
    elif delta is not None and abs(delta) < 3:
        driver = "stable"

    return {
        "last_analysis": {
            "recommendation_readiness_pct": prev_ready,
            "institutional_readiness_pct": prev.get("institutional_readiness_pct") or prev.get("overall_coverage_pct"),
            "investment_thesis_status": prev.get("investment_thesis_status"),
            "recorded_at": prev.get("recorded_at") or prev.get("generated_at"),
        }
        if prev
        else None,
        "today": {
            "recommendation_readiness_pct": cur_ready,
            "institutional_readiness_pct": gate.get("institutional_readiness_pct") or gate.get("overall_coverage_pct"),
            "investment_thesis_status": gate.get("investment_thesis_status"),
            "recorded_at": _now(),
        },
        "delta_pct": delta,
        "driver": driver,
        "reasons": reasons,
        "note": "Recommendation delta separates company change from data/pack change.",
    }
