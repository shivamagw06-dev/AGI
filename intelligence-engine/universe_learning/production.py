"""Production façades for universe learning bootstrap."""

from __future__ import annotations

from typing import Any

from universe_learning.bootstrap import bootstrap_universe_learning, learning_status


def health() -> dict[str, Any]:
    st = learning_status()
    return {
        "ok": True,
        "version": st.get("version"),
        "universe": st.get("universe"),
        "queue_length": (st.get("queue") or {}).get("queue_length"),
        "cgl_enabled": ((st.get("cgl") or {}).get("enabled")),
    }


def soft_slice_for_ask_agi(question: str = "", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ = question, payload
    st = learning_status()
    return {
        "universe_learning": {
            "enabled": True,
            "supported_unique": ((st.get("universe") or {}).get("supported_unique")),
            "queue_length": (st.get("queue") or {}).get("queue_length"),
            "remaining": (st.get("progress") or {}).get("remaining_backlog"),
        }
    }


__all__ = [
    "bootstrap_universe_learning",
    "health",
    "learning_status",
    "soft_slice_for_ask_agi",
]
