"""Step 7 — Contradiction detection."""

from __future__ import annotations

from typing import Any

from app.irp.models import ContradictionNote, RankedEvidenceItem


def detect_contradictions(
    ranked: list[RankedEvidenceItem],
    *,
    rsp_contradictions: list[Any] | None = None,
) -> list[ContradictionNote]:
    notes: list[ContradictionNote] = []
    bulls = [r for r in ranked if r.stance == "bull"]
    bears = [r for r in ranked if r.stance == "bear"]
    if bulls and bears:
        notes.append(
            ContradictionNote(
                topic="stance_split",
                summary="Retrieved evidence contains both constructive and cautious stances.",
                why="Broker / AGI notes disagree on near-term demand, pricing, or growth visibility.",
                sides=[
                    f"Constructive: {bulls[0].title}",
                    f"Cautious: {bears[0].title}",
                ],
                confidence=0.7,
            )
        )

    # Soft-pass RSP contradiction objects without exposing engine names
    for item in rsp_contradictions or []:
        if isinstance(item, str):
            notes.append(
                ContradictionNote(
                    topic="research_disagreement",
                    summary=item[:280],
                    why="Opposing institutional opinions retrieved for the same subject.",
                )
            )
            continue
        if not isinstance(item, dict):
            continue
        summary = str(item.get("summary") or item.get("snippet") or item.get("title") or "")[:280]
        if not summary:
            continue
        notes.append(
            ContradictionNote(
                topic=str(item.get("topic") or item.get("type") or "research_disagreement"),
                summary=summary,
                why=str(item.get("why") or item.get("reason") or "Material disagreement in sourced research."),
                sides=[str(x) for x in (item.get("sides") or [])][:4],
                confidence=item.get("confidence"),
            )
        )

    # Deduplicate by summary prefix
    out: list[ContradictionNote] = []
    seen: set[str] = set()
    for n in notes:
        key = n.summary[:120].lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(n)
    return out[:8]
