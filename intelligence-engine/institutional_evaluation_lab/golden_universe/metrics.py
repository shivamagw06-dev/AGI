"""Structured per-ticker evaluation metrics."""

from __future__ import annotations

from typing import Any


def _layer_score(layers_by_id: dict[str, Any], key: str) -> float | None:
    lyr = layers_by_id.get(key) or {}
    for field in ("score", "company_quality_score", "evidence_quality_score"):
        if lyr.get(field) is not None:
            try:
                n = float(lyr[field])
            except (TypeError, ValueError):
                continue
            # Normalize 0–100 → 0–10 when needed
            if n > 10:
                n = n / 10.0
            return round(max(0.0, min(10.0, n)), 2)
    return None


def _decision_label(
    *,
    action: str | None,
    band: str | None,
    thesis: str | None,
    gate_status: str | None,
) -> str:
    blob = f"{action or ''} {band or ''} {thesis or ''} {gate_status or ''}".lower()
    if "inconclusive" in blob or "defer" in blob or band in {"deferred"}:
        return "Deferred"
    if band == "watchlist" or "watch" in blob:
        return "Watchlist"
    if band == "high_conviction_allowed" or "high conviction" in blob or "accumulate" in blob:
        return "High Conviction"
    if "constructive" in blob:
        return "Constructive"
    if "avoid" in blob or "cautious" in blob:
        return "Cautious"
    if "neutral" in blob or band == "moderate_conviction":
        return "Neutral"
    if action:
        return str(action).replace("_", " ").title()
    return "Inconclusive"


def _evidence_class(readiness_pct: float | None, gate_status: str | None) -> str:
    r = float(readiness_pct or 0)
    if gate_status == "FAILED" and r < 50:
        return "Insufficient"
    if r >= 80:
        return "Complete"
    if r >= 50:
        return "Partial"
    return "Insufficient"


def extract_metrics(
    *,
    ticker: str,
    company_name: str | None,
    sector: str | None,
    bucket: str | None,
    ide_pkg: dict[str, Any] | None,
    price_pkg: dict[str, Any] | None,
    pack_present: bool,
    runtime_ms: int,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    """Build the structured evaluation row stored for regression."""
    ide = ide_pkg if isinstance(ide_pkg, dict) else {}
    summary = ide.get("summary") if isinstance(ide.get("summary"), dict) else {}
    gate = ide.get("institutional_readiness_gate") if isinstance(ide.get("institutional_readiness_gate"), dict) else {}
    decision = ide.get("decision") if isinstance(ide.get("decision"), dict) else {}
    layers = ide.get("layers") or []
    layers_by_id: dict[str, Any] = {}
    if isinstance(layers, list):
        layers_by_id = {str(r.get("id")): r for r in layers if isinstance(r, dict) and r.get("id")}
    elif isinstance(layers, dict):
        layers_by_id = layers

    readiness = (
        gate.get("recommendation_readiness_pct")
        or gate.get("evidence_confidence_pct")
        or summary.get("evidence_confidence_pct")
        or gate.get("overall_coverage_pct")
        or summary.get("overall_coverage_pct")
    )
    try:
        readiness_f = float(readiness) if readiness is not None else None
    except (TypeError, ValueError):
        readiness_f = None

    price = price_pkg if isinstance(price_pkg, dict) else {}
    snap = price.get("snapshot") if isinstance(price.get("snapshot"), dict) else {}
    live_price = bool(snap.get("ltp") is not None) and not bool(snap.get("stale"))
    # Seeded/gateway still counts as live_price attempt; mark provider
    price_available = snap.get("ltp") is not None

    band = gate.get("band") or summary.get("readiness_band")
    thesis = gate.get("investment_thesis_status") or summary.get("investment_thesis_status")
    action = summary.get("action") or decision.get("action")
    gate_status = gate.get("status") or ("FAILED" if summary.get("gate_blocked") else "PASSED")
    if summary.get("gate_blocked"):
        gate_status = "FAILED"

    decision_label = _decision_label(action=action, band=band, thesis=thesis, gate_status=gate_status)

    company_q = summary.get("company_quality_10")
    if company_q is None:
        company_q = _layer_score(layers_by_id, "company_quality")
    financial_q = _layer_score(layers_by_id, "financial_quality")
    valuation = _layer_score(layers_by_id, "valuation")
    macro = _layer_score(layers_by_id, "macro")
    technical = _layer_score(layers_by_id, "technical")
    risk = _layer_score(layers_by_id, "risk")

    overall = summary.get("overall_score")
    try:
        overall_f = float(overall) if overall is not None else None
        if overall_f is not None and overall_f > 10:
            overall_f = round(overall_f / 10.0, 2)
    except (TypeError, ValueError):
        overall_f = None

    return {
        "ticker": ticker.upper(),
        "company_name": company_name,
        "sector": sector,
        "bucket": bucket,
        "company_quality": company_q,
        "financial_quality": financial_q,
        "valuation": valuation,
        "macro": macro,
        "technical": technical,
        "risk": risk,
        "overall_score": overall_f,
        "recommendation_readiness": round(readiness_f, 1) if readiness_f is not None else None,
        "institutional_readiness": gate.get("institutional_readiness_pct") or gate.get("overall_coverage_pct"),
        "decision": decision_label,
        "action": action,
        "readiness_band": band,
        "investment_thesis_status": thesis,
        "gate": "PASS" if gate_status == "PASSED" else "FAIL",
        "gate_status": gate_status,
        "runtime_ms": int(runtime_ms),
        "live_price": bool(live_price),
        "price_available": bool(price_available),
        "price_ltp": snap.get("ltp"),
        "price_source": snap.get("source_provider") or snap.get("provider") or price.get("provider_called"),
        "price_stale": bool(snap.get("stale")),
        "price_age_sec": price.get("age_sec"),
        "pack_present": bool(pack_present),
        "evidence_class": _evidence_class(readiness_f, gate_status),
        "investment_grade": summary.get("investment_grade") or ide.get("investment_grade"),
        "not_a_negative_view": bool(gate.get("not_a_negative_view") or summary.get("not_a_negative_view")),
        "errors": list(errors or []),
        "ok": not bool(errors),
    }
