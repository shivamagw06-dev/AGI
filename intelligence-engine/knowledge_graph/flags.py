"""IKG feature flags — soft layer only."""

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
    return bool(getattr(s, "knowledge_graph", True))


def _sub(name: str, default: bool = True) -> bool:
    s = _settings()
    if s is None:
        return default
    return bool(getattr(s, "knowledge_graph", True)) and bool(getattr(s, name, default))


def flags_dict() -> dict[str, Any]:
    return {
        "KNOWLEDGE_GRAPH": is_enabled(),
        "IKG_ENTITY_RESOLUTION": _sub("ikg_entity_resolution"),
        "IKG_SUPPLY_CHAIN": _sub("ikg_supply_chain"),
        "IKG_OWNERSHIP": _sub("ikg_ownership"),
        "IKG_MACRO": _sub("ikg_macro"),
        "IKG_EVENTS": _sub("ikg_events"),
        "IKG_THESIS": _sub("ikg_thesis"),
        "IKG_QUERY": _sub("ikg_query"),
        "IKG_DEPENDENCY": _sub("ikg_dependency"),
    }
