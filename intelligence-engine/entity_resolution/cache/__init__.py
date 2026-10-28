"""Tiny in-process resolution cache."""

from __future__ import annotations

from typing import Any

_CACHE: dict[str, dict[str, Any]] = {}


def cache_get(key: str) -> dict[str, Any] | None:
    return _CACHE.get(key)


def cache_set(key: str, value: dict[str, Any]) -> None:
    if len(_CACHE) > 2048:
        _CACHE.clear()
    _CACHE[key] = value


def cache_stats() -> dict[str, Any]:
    return {"size": len(_CACHE)}


def make_key(question: str, prior_entity_id: str | None = None) -> str:
    return f"{(prior_entity_id or '').upper()}::{(question or '').strip().lower()}"
