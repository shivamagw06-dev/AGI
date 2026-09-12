"""ERE feature flags — supporting identity soft-wire only."""

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
    return bool(getattr(s, "entity_resolution", True))


def flags_dict() -> dict[str, Any]:
    return {
        "ENTITY_RESOLUTION": is_enabled(),
        "ERE_V1": True,
        "ERE_IKG_AUTHORITATIVE": True,
        "ERE_NEVER_GUESS": True,
        "ERE_CLARIFY_BELOW_85": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "ARCHITECTURE_FROZEN": True,
    }
