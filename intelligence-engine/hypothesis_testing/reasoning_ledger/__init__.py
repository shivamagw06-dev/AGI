"""Reasoning ledger — append-only audit of how belief changed."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_ledger(hypothesis_id: str, statement: str, initial_confidence: float) -> list[dict[str, Any]]:
    return [
        {
            "ts": _ts(),
            "event": "created",
            "hypothesis_id": hypothesis_id,
            "note": f"Hypothesis registered for institutional testing: {statement}",
            "probability": round(float(initial_confidence), 4),
        }
    ]


def append_event(ledger: list[dict[str, Any]], event: str, **payload: Any) -> list[dict[str, Any]]:
    entry = {"ts": _ts(), "event": event, **payload}
    ledger.append(entry)
    return ledger


def build_reasoning_ledger(
    *,
    hypothesis_id: str,
    statement: str,
    initial_confidence: float,
    evidence: list[dict[str, Any]],
    probability_timeline: list[dict[str, Any]],
    status: str,
    updated_probability: float,
) -> list[dict[str, Any]]:
    ledger = create_ledger(hypothesis_id, statement, initial_confidence)
    for e in evidence:
        effect = str(e.get("effect") or "Neutral")
        if e.get("polarity") == "missing" or e.get("kind") == "missing":
            append_event(
                ledger,
                "missing_evidence",
                evidence_id=e.get("id"),
                note=f"Missing evidence noted: {e.get('text')}",
                effect=effect,
            )
            continue
        append_event(
            ledger,
            "evidence_effect",
            evidence_id=e.get("id"),
            effect=effect,
            note=f"Evidence {e.get('id')} {effect.lower()}: {e.get('text')}",
            delta=e.get("probability_delta"),
        )
    # Probability updates from timeline
    prev = None
    for step in probability_timeline:
        if step.get("step") == "initial":
            prev = step.get("probability")
            continue
        cur = step.get("probability")
        append_event(
            ledger,
            "probability_updated",
            note=step.get("note"),
            from_probability=prev,
            to_probability=cur,
            delta=step.get("delta"),
        )
        prev = cur
    append_event(
        ledger,
        "final_status",
        status=status,
        probability=updated_probability,
        note=f"Final status {status} at {round(float(updated_probability) * 100)}%",
    )
    return ledger
