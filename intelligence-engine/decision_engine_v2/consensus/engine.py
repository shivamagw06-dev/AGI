"""Committee / institutional consensus soft summary for IDE V2."""

from __future__ import annotations

from typing import Any


def consensus_view(
    inputs: dict[str, Any],
    *,
    committee: dict[str, Any] | None = None,
    conflicts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    committee = committee or (inputs.get("layers") or {}).get("investment_committee") or {}
    summary = inputs.get("stack_summary") or {}
    minority = committee.get("minority_opinions") or committee.get("minority") or []
    stance = committee.get("committee_stance") or committee.get("stance") or summary.get("committee_stance") or "Neutral"
    return {
        "committee_position": stance,
        "minority_view": minority[:3] if isinstance(minority, list) else minority,
        "conflict_count": (conflicts or {}).get("conflict_count", 0),
        "rule": "Consensus summarised without erasing minority views",
    }
