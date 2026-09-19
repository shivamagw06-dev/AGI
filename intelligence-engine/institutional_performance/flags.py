"""Feature flags for PRP-01."""

from __future__ import annotations

import os
from typing import Any


def _truthy(name: str, default: str = "true") -> bool:
    raw = (os.environ.get(name) or default).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def is_enabled() -> bool:
    return _truthy("AGI_PRP_01_ENABLED", "true")


def redis_enabled() -> bool:
    return _truthy("AGI_PRP_REDIS", "true")


def parallel_orchestration_enabled() -> bool:
    return _truthy("AGI_PRP_PARALLEL_ORCH", "true")


def async_publications_enabled() -> bool:
    return _truthy("AGI_PRP_ASYNC_PUB", "true")


# Alias used by job_queue / soft integrations
def async_publication_enabled() -> bool:
    return async_publications_enabled()


def max_workers() -> int:
    raw = (os.environ.get("AGI_PRP_MAX_WORKERS") or "8").strip()
    try:
        return max(1, min(32, int(raw)))
    except ValueError:
        return 8


def query_cache_enabled() -> bool:
    return _truthy("AGI_PRP_QUERY_CACHE", "true")


def workspace_cache_enabled() -> bool:
    return _truthy("AGI_PRP_WORKSPACE_CACHE", "true")


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_PRP_01_ENABLED": is_enabled(),
        "AGI_PRP_REDIS": redis_enabled(),
        "AGI_PRP_PARALLEL_ORCH": parallel_orchestration_enabled(),
        "AGI_PRP_ASYNC_PUB": async_publications_enabled(),
        "AGI_PRP_QUERY_CACHE": query_cache_enabled(),
        "AGI_PRP_WORKSPACE_CACHE": workspace_cache_enabled(),
        "AGI_PRP_MAX_WORKERS": max_workers(),
        "adds_intelligence_engines": False,
        "architecture_frozen": True,
        "redis_url_env": "REDIS_URL",
    }
