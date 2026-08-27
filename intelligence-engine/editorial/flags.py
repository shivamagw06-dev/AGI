"""Feature flags for the Editorial Intelligence Layer."""

from __future__ import annotations


def _flag(name: str, default: bool = True) -> bool:
    try:
        from app.core.config import get_settings

        return bool(getattr(get_settings(), name, default))
    except Exception:
        return default


def is_enabled() -> bool:
    return _flag("editorial_layer", True) and _flag("ask_agi_editorial_layer", True)


def flags_dict() -> dict[str, bool | str]:
    provider = "gemini"
    try:
        from app.core.config import get_settings

        provider = (get_settings().editorial_provider or "gemini").strip().lower() or "gemini"
    except Exception:
        pass
    return {
        "EDITORIAL_LAYER": is_enabled(),
        "ASK_AGI_EDITORIAL_LAYER": _flag("ask_agi_editorial_layer", True),
        "EDITORIAL_PROVIDER": provider,
        "ROLE": "writer_only",
    }
