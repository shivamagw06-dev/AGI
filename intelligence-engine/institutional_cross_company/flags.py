"""Feature flags for CCI-01."""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    raw = (os.environ.get("AGI_CCI_01_ENABLED") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_CCI_01_ENABLED": is_enabled(),
        "llm": False,
        "generates_recommendations": False,
        "owns_graph": False,
        "graph_system_of_record": "KG-01",
        "predictive": False,
        "dependency_propagation_only": True,
    }
