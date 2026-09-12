"""Feature flags for Knowledge Operations Center."""

from __future__ import annotations

import os


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def is_koc_enabled() -> bool:
    return _env_bool("AGI_KOC_ENABLED", True)
