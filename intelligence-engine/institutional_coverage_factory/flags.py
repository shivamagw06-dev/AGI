"""Feature flags for Institutional Coverage Factory."""

from __future__ import annotations

import os


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def is_icf_enabled() -> bool:
    return _env_bool("AGI_ICF_ENABLED", True)


def is_icf_scheduler_enabled() -> bool:
    return is_icf_enabled() and _env_bool("AGI_ICF_SCHEDULER_ENABLED", True)


def is_icf_dispatch_enabled() -> bool:
    """When false, planner ranks/queues only — no collector side-effects."""
    return is_icf_enabled() and _env_bool("AGI_ICF_DISPATCH_ENABLED", True)


def is_icf_mission_control_enabled() -> bool:
    return is_icf_enabled() and _env_bool("AGI_ICF_MISSION_CONTROL_ENABLED", True)
