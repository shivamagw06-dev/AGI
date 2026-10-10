"""Pillar engine — aggregate beliefs into institutional thesis pillars."""

from __future__ import annotations

from typing import Any

from thesis_engine.schema import PILLAR_SOURCE_TYPES, PILLARS

# Fallback default strength when no belief maps to a pillar
_NEUTRAL_STRENGTH = 0.5


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _pillars_for_type(hyp_type: str) -> list[str]:
    out = []
    for pillar, types in PILLAR_SOURCE_TYPES.items():
        if hyp_type in types:
            out.append(pillar)
    return out or ["Business Quality"]


def build_pillars(beliefs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {p: [] for p in PILLARS}
    for b in beliefs:
        for pillar in _pillars_for_type(str(b.get("type") or "Business")):
            grouped[pillar].append(b)

    pillars: list[dict[str, Any]] = []
    for pillar in PILLARS:
        members = grouped.get(pillar) or []
        if members:
            strength = sum(float(m.get("posterior_belief") or 0.5) for m in members) / len(members)
            confidence = sum(float(m.get("confidence") or 0.6) for m in members) / len(members)
            evidence = []
            contradictions = []
            missing = []
            for m in members:
                for e in _safe_list(m.get("supporting_evidence"))[:3]:
                    text = e.get("text") if isinstance(e, dict) else str(e)
                    if text:
                        evidence.append({"hypothesis_id": m.get("hypothesis_id"), "text": text})
                for e in _safe_list(m.get("contradicting_evidence"))[:2]:
                    text = e.get("text") if isinstance(e, dict) else str(e)
                    if text:
                        contradictions.append({"hypothesis_id": m.get("hypothesis_id"), "text": text})
                for gap in _safe_list(m.get("missing_evidence"))[:2]:
                    missing.append(str(gap))
            derived = True
        else:
            strength = _NEUTRAL_STRENGTH
            confidence = 0.45
            evidence = []
            contradictions = []
            missing = [f"No tested hypothesis mapped to {pillar}"]
            derived = False

        pillars.append(
            {
                "pillar": pillar,
                "strength": round(strength, 4),
                "strength_pct": round(strength * 100),
                "confidence": round(confidence, 4),
                "confidence_pct": round(confidence * 100),
                "belief_ids": [m.get("hypothesis_id") for m in members],
                "belief_count": len(members),
                "evidence": evidence[:6],
                "contradictions": contradictions[:4],
                "missing_evidence": list(dict.fromkeys(missing))[:4],
                "supported": strength >= 0.58,
                "evidence_backed": derived,
                "verdict": (
                    "Strong"
                    if strength >= 0.72
                    else "Constructive"
                    if strength >= 0.58
                    else "Neutral"
                    if strength >= 0.45
                    else "Weak"
                ),
            }
        )
    return pillars


def pillar_summary(pillars: list[dict[str, Any]]) -> dict[str, Any]:
    backed = [p for p in pillars if p.get("evidence_backed")]
    supported = [p for p in pillars if p.get("supported")]
    return {
        "total": len(pillars),
        "evidence_backed": len(backed),
        "supported": len(supported),
        "supported_pillars": [p["pillar"] for p in supported],
        "weak_pillars": [p["pillar"] for p in pillars if p.get("verdict") == "Weak"],
        "mean_strength": round(sum(float(p["strength"]) for p in pillars) / max(len(pillars), 1), 4),
    }
