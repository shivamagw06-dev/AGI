"""Research session — persistent research context across conversations."""

from __future__ import annotations

from typing import Any

from research_workflow_framework.schema import PLAYBOOK_STATUS_LABELS, STATUS_COMPLETE, STATUS_NEEDS_REVIEW, STATUS_PENDING


def merge_research_session(
    prior: dict[str, Any] | None,
    *,
    objective: str,
    workflow_key: str,
    ticker: str | None,
    company: str | None,
    question: str,
    playbook_key: str | None,
    completed_labels: list[str],
    outstanding_questions: list[str] | None = None,
    current_thesis: str | None = None,
) -> dict[str, Any]:
    """Merge session state for this user research thread."""
    state = dict(prior or {})
    questions = list(state.get("questions_asked") or [])
    if question and question not in questions:
        questions.append(question)

    playbooks_done = set(state.get("playbooks_completed") or [])
    label = PLAYBOOK_STATUS_LABELS.get(playbook_key or "", "")
    if label:
        playbooks_done.add(label)
    for lbl in completed_labels:
        playbooks_done.add(lbl)

    outstanding = list(outstanding_questions or state.get("outstanding_questions") or [])

    return {
        "research_objective": objective,
        "workflow_key": workflow_key,
        "company": company or ticker or state.get("company"),
        "ticker": (ticker or state.get("ticker") or "").upper() or None,
        "questions_asked": questions[-20:],
        "playbooks_completed": sorted(playbooks_done),
        "outstanding_questions": outstanding[:12],
        "current_thesis": current_thesis or state.get("current_thesis"),
        "research_status": state.get("research_status") or STATUS_PENDING,
        "turn_count": int(state.get("turn_count") or 0) + 1,
        "session_timestamp": state.get("session_timestamp") or None,
    }
