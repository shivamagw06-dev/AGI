"""Contradiction resolver — strongest support vs strongest challenge."""

from __future__ import annotations

from typing import Any


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _score(item: Any) -> int:
    if isinstance(item, dict):
        return int(item.get("support_score") or item.get("contradiction_score") or item.get("strength") or 50)
    return 50


def _text(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("text") or item.get("statement") or "")
    return str(item)


def resolve_contradictions(beliefs: list[dict[str, Any]], pillars: list[dict[str, Any]]) -> dict[str, Any]:
    supports: list[dict[str, Any]] = []
    challenges: list[dict[str, Any]] = []
    missing: list[str] = []
    outstanding: list[str] = []

    for b in beliefs:
        hid = b.get("hypothesis_id")
        for e in _safe_list(b.get("supporting_evidence")):
            t = _text(e)
            if t:
                supports.append({"hypothesis_id": hid, "text": t, "score": _score(e)})
        for e in _safe_list(b.get("contradicting_evidence")):
            t = _text(e)
            if t:
                challenges.append({"hypothesis_id": hid, "text": t, "score": _score(e)})
        for gap in _safe_list(b.get("missing_evidence")):
            missing.append(str(gap))
        unc = b.get("uncertainty") or {}
        for ku in _safe_list(unc.get("known_unknowns"))[:2]:
            outstanding.append(str(ku))
        # Weak / contested beliefs become outstanding questions
        state = str(b.get("belief_state") or "")
        if state in ("Neutral", "Leaning Negative", "Challenged", "Contradicted", "Rejected"):
            outstanding.append(f"Resolve contested belief {hid}: {b.get('hypothesis')}")

    supports.sort(key=lambda x: -x["score"])
    challenges.sort(key=lambda x: -x["score"])

    # Major contradictions: highest-scoring challenges + weak pillars
    major = list(challenges[:4])
    for p in pillars:
        if p.get("verdict") == "Weak" and p.get("evidence_backed"):
            major.append(
                {
                    "hypothesis_id": None,
                    "text": f"{p['pillar']} pillar is weak (strength {p['strength_pct']}%)",
                    "score": 70,
                }
            )

    return {
        "strongest_supporting_evidence": supports[:5],
        "strongest_contradicting_evidence": challenges[:5],
        "major": major[:6],
        "major_count": len(major[:6]),
        "outstanding_questions": list(dict.fromkeys(outstanding))[:8],
        "missing_evidence": list(dict.fromkeys(missing))[:8],
        "resolution_note": (
            "Committee must weigh strongest supporting evidence against strongest challenges before voting"
        ),
    }
