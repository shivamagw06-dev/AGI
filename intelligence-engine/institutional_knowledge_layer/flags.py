"""IKL feature flags (env-driven, soft defaults)."""

from __future__ import annotations

import os


def _truthy(name: str, default: str = "1") -> bool:
    return str(os.environ.get(name, default) or default).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def ikl_enabled() -> bool:
    return _truthy("IKL_ENABLED", "1")


def ikl_writeback_enabled() -> bool:
    return ikl_enabled() and _truthy("IKL_WRITEBACK_ENABLED", "1")


def ikl_ask_consult_enabled() -> bool:
    return ikl_enabled() and _truthy("IKL_ASK_CONSULT_ENABLED", "1")


def ikl_delta_enabled() -> bool:
    return ikl_enabled() and _truthy("IKL_DELTA_ENABLED", "1")
