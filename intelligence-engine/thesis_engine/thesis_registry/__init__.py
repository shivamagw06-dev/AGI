"""Thesis registry — normalise the Institutional Belief Package for thesis construction."""

from __future__ import annotations

from typing import Any


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def extract_beliefs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    bbce = _safe_dict(payload.get("belief_engine"))
    nested = _safe_dict(bbce.get("belief_engine"))
    body = nested or bbce
    pkg = _safe_dict(body.get("institutional_belief_package"))
    raw = _safe_list(pkg.get("beliefs") or body.get("beliefs") or payload.get("beliefs"))
    out = []
    for i, b in enumerate(raw, start=1):
        if not isinstance(b, dict):
            continue
        stmt = str(b.get("hypothesis") or b.get("statement") or "").strip()
        if not stmt:
            continue
        posterior = b.get("posterior_belief")
        if posterior is None:
            posterior = b.get("updated_probability") or b.get("confidence") or 0.55
        posterior = float(posterior)
        if posterior > 1.0:
            posterior = posterior / 100.0
        out.append(
            {
                "hypothesis_id": str(b.get("hypothesis_id") or b.get("id") or f"H{i}"),
                "hypothesis": stmt,
                "type": str(b.get("type") or "Business"),
                "prior_belief": b.get("prior_belief"),
                "posterior_belief": round(posterior, 4),
                "belief_state": b.get("belief_state"),
                "confidence": float(b.get("confidence") or 0.6),
                "uncertainty": _safe_dict(b.get("uncertainty")),
                "drift": _safe_dict(b.get("drift")),
                "supporting_evidence": _safe_list(b.get("supporting_evidence")),
                "contradicting_evidence": _safe_list(b.get("contradicting_evidence")),
                "missing_evidence": _safe_list(
                    b.get("missing_evidence") or _safe_dict(b.get("uncertainty")).get("missing_evidence")
                ),
            }
        )
    return out


def register_thesis(thesis: dict[str, Any]) -> dict[str, Any]:
    pillars = _safe_list(thesis.get("supporting_pillars"))
    return {
        "pillar_count": len(pillars),
        "pillars": [p.get("pillar") for p in pillars],
        "status": thesis.get("status"),
        "conviction": (thesis.get("conviction") or {}).get("overall"),
        "catalyst_count": len(_safe_list(thesis.get("catalysts"))),
        "contradiction_count": len(_safe_list((thesis.get("contradictions") or {}).get("major"))),
    }
