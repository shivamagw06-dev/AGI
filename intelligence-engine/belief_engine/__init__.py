"""Bayesian Belief & Confidence Engine (BBCE) V1 — RQ2 Sprint 6.

Soft-wire belief updater. Not a top-level intelligence layer.
Executes AFTER Institutional Falsification Engine and BEFORE analyst opinions.
"""

from belief_engine.production import (
    constitution,
    generate_for_question,
    health,
    plan,
    quality_gates,
    soft_slice_for_ask_agi,
    update_belief,
)

__all__ = [
    "constitution",
    "generate_for_question",
    "health",
    "plan",
    "quality_gates",
    "soft_slice_for_ask_agi",
    "update_belief",
]
