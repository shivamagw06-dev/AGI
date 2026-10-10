"""Deterministic workflow state transitions."""

from __future__ import annotations

from financial_statements_engine.orchestrator.schema import ALLOWED_TRANSITIONS, WORKFLOW_STATES


class IllegalTransition(ValueError):
    pass


def can_transition(current: str, target: str) -> bool:
    if current not in WORKFLOW_STATES or target not in WORKFLOW_STATES:
        return False
    return target in ALLOWED_TRANSITIONS.get(current, ())


def transition(current: str, target: str) -> str:
    if current == target:
        return current
    if not can_transition(current, target):
        raise IllegalTransition(f"illegal_transition:{current}->{target}")
    return target
