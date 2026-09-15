"""Belief registry — normalise tested / falsified hypotheses into belief candidates."""

from __future__ import annotations

from typing import Any


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def extract_tested_hypotheses(payload: dict[str, Any]) -> list[dict[str, Any]]:
    ihte = _safe_dict(payload.get("hypothesis_testing"))
    nested = _safe_dict(ihte.get("hypothesis_testing"))
    body = nested or ihte
    tested = _safe_list(body.get("tested_hypotheses") or payload.get("tested_hypotheses"))
    out = []
    for i, h in enumerate(tested, start=1):
        if not isinstance(h, dict):
            continue
        stmt = str(h.get("hypothesis") or h.get("statement") or "").strip()
        if not stmt:
            continue
        out.append(
            {
                "id": str(h.get("id") or f"H{i}"),
                "hypothesis": stmt,
                "type": str(h.get("type") or "Business"),
                "initial_confidence": h.get("initial_confidence") or h.get("updated_probability") or 0.55,
                "updated_probability": h.get("updated_probability"),
                "support_score": h.get("support_score"),
                "contradiction_score": h.get("contradiction_score"),
                "supporting_evidence": h.get("supporting_evidence") or [],
                "contradicting_evidence": h.get("contradicting_evidence") or [],
                "missing_evidence": h.get("missing_evidence") or [],
                "evidence_effects": h.get("evidence_effects") or [],
                "uncertainty": h.get("uncertainty") or {},
                "status": h.get("status"),
                "assumptions": h.get("assumptions") or {},
            }
        )
    return out


def extract_falsification_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Map hypothesis_id → falsification report when IFE is present."""
    ife = _safe_dict(payload.get("falsification") or payload.get("falsification_engine"))
    nested = _safe_dict(ife.get("falsification") or ife.get("falsification_engine"))
    body = nested or ife
    reports = _safe_list(body.get("reports") or body.get("falsification_reports") or body.get("hypotheses"))
    out: dict[str, dict[str, Any]] = {}
    for r in reports:
        if not isinstance(r, dict):
            continue
        hid = str(r.get("hypothesis_id") or r.get("id") or "")
        if hid:
            out[hid] = r
    # Also allow flat severity on body
    if not out and body.get("severity"):
        out["*"] = body
    return out


def register_beliefs(beliefs: list[dict[str, Any]]) -> dict[str, Any]:
    by_state: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for b in beliefs:
        s = str(b.get("belief_state") or "Neutral")
        t = str(b.get("type") or "Business")
        by_state[s] = by_state.get(s, 0) + 1
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "count": len(beliefs),
        "by_state": by_state,
        "by_type": by_type,
        "ids": [b.get("hypothesis_id") or b.get("id") for b in beliefs],
    }
