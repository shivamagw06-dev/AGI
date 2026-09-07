"""FDI feature flags — soft layer only."""

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
    return bool(getattr(s, "filing_diff_engine", True))


def _sub(name: str, default: bool = True) -> bool:
    s = _settings()
    if s is None:
        return default
    return bool(getattr(s, "filing_diff_engine", True)) and bool(getattr(s, name, default))


def flags_dict() -> dict[str, Any]:
    return {
        "FILING_DIFF_ENGINE": is_enabled(),
        "FDI_STATEMENTS": _sub("fdi_statements"),
        "FDI_GUIDANCE": _sub("fdi_guidance"),
        "FDI_RISKS": _sub("fdi_risks"),
        "FDI_MANAGEMENT": _sub("fdi_management"),
        "FDI_SEGMENTS": _sub("fdi_segments"),
        "FDI_ACCOUNTING": _sub("fdi_accounting"),
        "FDI_CAPITAL": _sub("fdi_capital"),
        "FDI_GOVERNANCE": _sub("fdi_governance"),
        "FDI_OWNERSHIP": _sub("fdi_ownership"),
    }
