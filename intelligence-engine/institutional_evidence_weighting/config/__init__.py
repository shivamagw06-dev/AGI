"""Versioned IEW configuration loader."""

from __future__ import annotations

from typing import Any

from institutional_evidence_weighting.config.profiles.v1_0_0 import PROFILE as _V1
from institutional_evidence_weighting.schema import WEIGHT_VERSION

_PROFILES: dict[str, dict[str, Any]] = {
    _V1["profile_id"]: _V1,
    "v1": _V1,
    "v1.0.0": _V1,
    "default": _V1,
}


def list_profiles() -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for p in _PROFILES.values():
        pid = str(p.get("profile_id"))
        if pid in seen:
            continue
        seen.add(pid)
        out.append(
            {
                "profile_id": pid,
                "version": p.get("version"),
                "deterministic": p.get("deterministic", True),
                "llm_used": p.get("llm_used", False),
                "active_default": pid == WEIGHT_VERSION or pid == _V1["profile_id"],
            }
        )
    return out


def load_profile(profile_id: str | None = None) -> dict[str, Any]:
    key = str(profile_id or WEIGHT_VERSION or "default")
    if key in _PROFILES:
        return dict(_PROFILES[key])
    # Fallback: exact weight_version match
    for p in _PROFILES.values():
        if p.get("profile_id") == key:
            return dict(p)
    return dict(_V1)


def active_weight_version() -> str:
    return str(load_profile().get("profile_id") or WEIGHT_VERSION)
