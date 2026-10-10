"""AGI Observability — LangSmith tracing configuration (observability only)."""

from __future__ import annotations

import os
from typing import Any

OBSERVABILITY_VERSION = "agi-observability-v1.0.0"
MODULE_CODE = "OBS"
COMPANY = "AGI"
PROGRAMME = "AGI Observability · LangSmith tracing (langsmith-trace skill)"

DEFAULT_PROJECT = "agi-intelligence-engine"

FREEZE_LOCKS: dict[str, Any] = {
    "knowledge_factory": True,
    "reasoning_frozen": True,
    "framework_selection": True,
    "intent_resolution": True,
    "playbooks": True,
    "temporal_integrity": True,
    "evaluation_lab": True,
    "observability_only": True,
    "never_changes_answers": True,
    "fails_open": True,
}

# Truthy values accepted for LANGSMITH_TRACING
_TRUTHY = {"1", "true", "yes", "on"}


def api_key() -> str:
    for key in ("LANGSMITH_API_KEY", "LANGCHAIN_API_KEY"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    return ""


def project() -> str:
    for key in ("LANGSMITH_PROJECT", "LANGCHAIN_PROJECT"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    return DEFAULT_PROJECT


def workspace_id() -> str:
    return (os.environ.get("LANGSMITH_WORKSPACE_ID") or "").strip()


def endpoint() -> str:
    return (
        os.environ.get("LANGSMITH_ENDPOINT")
        or os.environ.get("LANGCHAIN_ENDPOINT")
        or "https://api.smith.langchain.com"
    ).strip()


def tracing_requested() -> bool:
    """LANGSMITH_TRACING opt-in. Defaults to on when an API key is present."""
    raw = os.environ.get("LANGSMITH_TRACING") or os.environ.get("LANGCHAIN_TRACING_V2")
    if raw is None:
        return bool(api_key())
    return str(raw).strip().lower() in _TRUTHY


def sdk_available() -> bool:
    try:
        import langsmith  # noqa: F401
    except Exception:
        return False
    return True


def is_enabled() -> bool:
    """Tracing is active only with an API key, opt-in flag, and the SDK installed."""
    return bool(api_key()) and tracing_requested() and sdk_available()


def config() -> dict[str, Any]:
    key = api_key()
    return {
        "company": COMPANY,
        "version": OBSERVABILITY_VERSION,
        "enabled": is_enabled(),
        "api_key_present": bool(key),
        "api_key_masked": f"{key[:7]}…{key[-4:]}" if len(key) > 12 else ("set" if key else None),
        "tracing_requested": tracing_requested(),
        "sdk_available": sdk_available(),
        "project": project(),
        "endpoint": endpoint(),
        "workspace_id": workspace_id() or None,
        "freeze_locks": dict(FREEZE_LOCKS),
        "fabricated": False,
    }
