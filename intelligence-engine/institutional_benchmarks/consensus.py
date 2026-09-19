"""Optional consensus comparison — overlap analytics, not correctness grading."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence


DEFAULT_HOUSES: tuple[str, ...] = (
    "Goldman Sachs",
    "Morgan Stanley",
    "Jefferies",
    "JP Morgan",
    "UBS",
    "ICICI Securities",
    "Axis Capital",
    "Kotak Institutional Equities",
    "Motilal Oswal",
)


def compare_consensus(
    report: Mapping[str, Any],
    *,
    house_notes: Optional[Sequence[Mapping[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Compare AGI reasoning against sell-side notes when provided.

    Comparison is NOT correctness. Measures overlap / uniqueness / disagreement strength.
    Without house notes, returns a structured placeholder.
    """
    notes = list(house_notes or [])
    agi_claims = []
    for item in ((report.get("sections") or {}).get("evidence_supporting") or {}).get("items") or []:
        if isinstance(item, Mapping) and item.get("claim"):
            agi_claims.append(str(item["claim"]))

    if not notes:
        return {
            "ok": True,
            "mode": "optional_unavailable",
            "houses": list(DEFAULT_HOUSES),
            "note": (
                "Consensus comparison is optional. Provide house_notes to measure reasoning/evidence "
                "overlap. AGI may legitimately disagree with sell-side conclusions."
            ),
            "agi_claim_count": len(agi_claims),
            "reasoning_overlap": None,
            "evidence_overlap": None,
            "unique_insights": agi_claims[:5],
            "missed_considerations": [],
            "strength_of_disagreement": None,
        }

    def tokens(text: str) -> set[str]:
        return {t.lower() for t in str(text).split() if len(t) > 3}

    agi_tok: set[str] = set()
    for c in agi_claims:
        agi_tok |= tokens(c)
    house_tok: set[str] = set()
    for n in notes:
        house_tok |= tokens(str(n.get("summary") or n.get("text") or ""))
    inter = agi_tok & house_tok
    union = agi_tok | house_tok
    overlap = round(len(inter) / max(1, len(union)), 4)
    return {
        "ok": True,
        "mode": "overlap",
        "houses": [n.get("house") for n in notes if n.get("house")],
        "reasoning_overlap": overlap,
        "evidence_overlap": overlap,
        "unique_insights": [c for c in agi_claims if not (tokens(c) & house_tok)][:8],
        "missed_considerations": [
            str(n.get("summary") or "")[:160]
            for n in notes
            if not (tokens(str(n.get("summary") or "")) & agi_tok)
        ][:8],
        "strength_of_disagreement": round(1.0 - overlap, 4),
        "correctness_graded": False,
    }
