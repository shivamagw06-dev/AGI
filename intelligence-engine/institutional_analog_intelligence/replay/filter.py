"""Point-in-time memory filter — no future leakage."""

from __future__ import annotations

from typing import Any


def available_on_or_before(available_from: str | None, as_of: str | None) -> bool:
    if not as_of:
        return True
    if not available_from:
        return False
    return str(available_from)[:10] <= str(as_of)[:10]


def filter_memories(
    memories: list[dict[str, Any]],
    *,
    as_of: str | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Keep memories whose available_from <= as_of; drop outcome leakage."""
    if not as_of:
        return list(memories), []
    kept: list[dict[str, Any]] = []
    dropped: list[str] = []
    for m in memories:
        af = m.get("available_from")
        if available_on_or_before(af if isinstance(af, str) else None, as_of):
            # Also hide outcome details that require known_outcome_as_of > as_of
            ko = m.get("known_outcome_as_of") or af
            row = dict(m)
            if ko and str(ko)[:10] > str(as_of)[:10]:
                row = {
                    **row,
                    "outcome_summary": "Outcome after as_of excluded (replay integrity).",
                    "lessons_learned": [
                        "Replay mode — post-cut-off lessons withheld",
                    ],
                    "outcome_redacted": True,
                }
            kept.append(row)
        else:
            dropped.append(str(m.get("memory_id")))
    return kept, dropped
