"""Hypothesis registry — normalise IHG / payload hypotheses for testing."""

from __future__ import annotations

from typing import Any


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def extract_hypotheses(payload: dict[str, Any]) -> list[dict[str, Any]]:
    ihg = _safe_dict(payload.get("hypothesis_engine"))
    nested = _safe_dict(ihg.get("hypothesis_engine"))
    body = nested or ihg
    raw = _safe_list(body.get("hypotheses") or payload.get("hypotheses"))
    out = []
    for i, h in enumerate(raw, start=1):
        if not isinstance(h, dict):
            continue
        stmt = str(h.get("statement") or h.get("hypothesis") or "").strip()
        if not stmt:
            continue
        conf = h.get("confidence")
        if conf is None and h.get("confidence_pct") is not None:
            conf = float(h["confidence_pct"]) / 100.0
        conf = float(conf if conf is not None else 0.65)
        if conf > 1.0:
            conf = conf / 100.0
        out.append(
            {
                "id": str(h.get("id") or f"H{i}"),
                "statement": stmt,
                "hypothesis": stmt,
                "type": str(h.get("type") or "Business"),
                "initial_confidence": round(max(0.05, min(0.95, conf)), 4),
                "reason": h.get("reason"),
                "required_evidence": list(h.get("required_evidence") or []),
                "status": "Under Test",
            }
        )
    return out


def register_hypotheses(hypotheses: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {h["id"]: h for h in hypotheses}
    by_type: dict[str, int] = {}
    for h in hypotheses:
        t = str(h.get("type") or "Business")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "count": len(hypotheses),
        "by_id": by_id,
        "by_type": by_type,
        "ids": list(by_id.keys()),
    }
