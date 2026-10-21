"""IHTE feature flags — soft-wire only; not a top-level intelligence layer."""

from __future__ import annotations

from typing import Any


def _settings():
    try:
        from app.core.config import get_settings

        return get_settings()
    except Exception:
        return None


def is_enabled() -> bool:
    s = _settings()
    if s is None:
        return True
    return bool(getattr(s, "hypothesis_testing", True))


def flags_dict() -> dict[str, Any]:
    return {
        "HYPOTHESIS_TESTING": is_enabled(),
        "IHTE_V1": True,
        "IHTE_EVIDENCE_EFFECTS": True,
        "IHTE_REASONING_LEDGER": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "ARCHITECTURE_FROZEN": True,
        "RQ2_SPRINT_4": True,
    }
