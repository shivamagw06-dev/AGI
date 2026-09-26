"""Institutional stack soft-integration flags — additive only."""

from __future__ import annotations

from typing import Any


def _flag(name: str, default: bool = True) -> bool:
    try:
        from app.core.config import get_settings

        return bool(getattr(get_settings(), name, default))
    except Exception:
        return default


def is_enabled() -> bool:
    return _flag("institutional_stack", True)


def flags_dict() -> dict[str, Any]:
    return {
        "INSTITUTIONAL_STACK": is_enabled(),
        "INSTITUTIONAL_STACK_AUTO_CHAIN": is_enabled() and _flag("institutional_stack_auto_chain", True),
        "INSTITUTIONAL_STACK_ASK_AGI": is_enabled() and _flag("institutional_stack_ask_agi", True),
        "INSTITUTIONAL_STACK_ADMIN": is_enabled() and _flag("institutional_stack_admin", True),
    }
