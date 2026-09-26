"""Conversation memory — research journey state across Ask turns."""

from __future__ import annotations

from typing import Any

from institutional_playbook_framework.journey import infer_completed_step


def merge_journey_state(
    prior: dict[str, Any] | None,
    *,
    ticker: str | None,
    playbook_key: str,
    journey_steps: list[str],
    question: str,
    playbook_selection: dict[str, Any] | None = None,
    response_sections: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge prior journey progress with this turn."""
    state = dict(prior or {})
    key = (ticker or state.get("ticker") or "_general").upper()
    completed = list(state.get("completed_steps") or [])

    step = infer_completed_step(
        playbook_key=playbook_key,
        question=question,
        playbook_selection=playbook_selection,
        response_sections=response_sections,
    )
    if step and step not in completed:
        completed.append(step)

    return {
        "ticker": key if key != "_GENERAL" else None,
        "playbook_key": playbook_key,
        "journey_steps": journey_steps,
        "completed_steps": completed,
        "last_question": question,
        "turn_count": int(state.get("turn_count") or 0) + 1,
    }
