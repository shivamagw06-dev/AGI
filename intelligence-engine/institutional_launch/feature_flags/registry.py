"""Feature flag registry for incremental v1.1 rollout (L-01)."""

from __future__ import annotations

import os
import threading
from typing import Any, Dict, Optional

from institutional_launch.schema import V11_FEATURE_FLAGS

_LOCK = threading.Lock()
_OVERRIDES: Dict[str, bool] = {}


def reset_for_tests() -> None:
    with _LOCK:
        _OVERRIDES.clear()


def _env_default(name: str) -> bool:
    # All v1.1 flags default false
    raw = (os.environ.get(name) or "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def get_flag(name: str) -> bool:
    key = str(name or "").strip().upper()
    with _LOCK:
        if key in _OVERRIDES:
            return _OVERRIDES[key]
    return _env_default(key)


def set_flag(name: str, enabled: bool, *, actor: str = "") -> dict[str, Any]:
    key = str(name or "").strip().upper()
    if key not in V11_FEATURE_FLAGS:
        return {"ok": False, "error": f"unknown flag: {key}", "known": list(V11_FEATURE_FLAGS)}
    with _LOCK:
        _OVERRIDES[key] = bool(enabled)
    return {
        "ok": True,
        "flag": key,
        "enabled": bool(enabled),
        "actor": actor,
        "note": "Runtime override; does not alter GA architecture.",
    }


def list_flags() -> dict[str, Any]:
    flags = []
    for name in V11_FEATURE_FLAGS:
        flags.append(
            {
                "flag": name,
                "enabled": get_flag(name),
                "default": False,
                "gated_until": "Launch-01 healthy",
            }
        )
    return {
        "flags": flags,
        "all_disabled": all(not f["enabled"] for f in flags),
        "architecture_frozen": True,
        "v11_not_started": True,
    }
