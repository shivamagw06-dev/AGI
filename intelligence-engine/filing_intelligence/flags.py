"""FIL feature flags — soft layer only."""

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
    return bool(getattr(s, "filing_intelligence", True))


def _sub(name: str, default: bool = True) -> bool:
    s = _settings()
    if s is None:
        return default
    return bool(getattr(s, "filing_intelligence", True)) and bool(getattr(s, name, default))


def flags_dict() -> dict[str, Any]:
    return {
        "FILING_INTELLIGENCE": is_enabled(),
        "FIL_STATEMENTS": _sub("fil_statements"),
        "FIL_NOTES": _sub("fil_notes"),
        "FIL_SEGMENTS": _sub("fil_segments"),
        "FIL_GUIDANCE": _sub("fil_guidance"),
        "FIL_RISKS": _sub("fil_risks"),
        "FIL_MANAGEMENT": _sub("fil_management"),
        "FIL_HISTORY": _sub("fil_history"),
        "FIL_EVIDENCE": _sub("fil_evidence"),
    }
