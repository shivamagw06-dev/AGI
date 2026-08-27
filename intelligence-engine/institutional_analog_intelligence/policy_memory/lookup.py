"""Policy-scoped memory helpers."""

from __future__ import annotations

from typing import Any

from institutional_analog_intelligence.registry.index import list_memories

_POLICY_TYPES = {
    "previous_policy_event",
    "previous_rate_cycle",
    "government_decision_analog",
}


def policy_memories() -> list[dict[str, Any]]:
    return [m for m in list_memories() if m.get("type") in _POLICY_TYPES or m.get("policy_context")]
