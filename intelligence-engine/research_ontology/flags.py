"""RQ1 Research Ontology flags — soft-wire supporting module only."""

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
    return bool(getattr(s, "research_ontology", True))


def flags_dict() -> dict[str, Any]:
    return {
        "RESEARCH_ONTOLOGY": is_enabled(),
        "RQ1_SPRINT1": True,
        "RQ1_NO_LAYER_EXECUTION": True,
        "RQ1_NO_ANALYST_EXECUTION": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "ARCHITECTURE_FROZEN": True,
    }
