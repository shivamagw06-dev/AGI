"""Feature flags for PUB-01."""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    raw = (os.environ.get("AGI_PUB_01_ENABLED") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_PUB_01_ENABLED": is_enabled(),
        "llm": False,
        "analyzes": False,
        "generates_recommendations": False,
        "reinterprets_evidence": False,
        "compose_only": True,
        "manifest_is_audit_record": True,
    }
