"""IRAE flags — final reasoning certification, no new architecture."""

from __future__ import annotations

from typing import Any


def _settings():
    try:
        from app.core.config import get_settings

        return get_settings()
    except Exception:
        return None


def is_enabled() -> bool:
    settings = _settings()
    return True if settings is None else bool(
        getattr(settings, "reasoning_audit", True)
    )


def flags_dict() -> dict[str, Any]:
    return {
        "REASONING_AUDIT": is_enabled(),
        "IRAE_V1": True,
        "IRAE_REASONING_REPLAY": True,
        "IRAE_TRACEABILITY": True,
        "FINAL_REASONING_CERTIFICATION_GATE": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "ARCHITECTURE_FROZEN": True,
        "RQ2_SPRINT_10": True,
    }
