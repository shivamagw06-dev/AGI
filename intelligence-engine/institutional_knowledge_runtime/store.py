"""In-memory IKO store for runtime execution."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_object import empty_iko

_STORE: dict[str, dict[str, Any]] = {}


def _key(entity_type: str, entity_id: str) -> str:
    return f"{entity_type}:{entity_id.upper()}"


def get(entity_type: str, entity_id: str) -> dict[str, Any] | None:
    return _STORE.get(_key(entity_type, entity_id))


def put(entity_type: str, entity_id: str, iko: dict[str, Any]) -> dict[str, Any]:
    _STORE[_key(entity_type, entity_id)] = iko
    return iko


def load_or_create_company(entity_id: str, *, company: str | None = None, iko: dict[str, Any] | None = None) -> dict[str, Any]:
    key = _key("company", entity_id)
    if iko and isinstance(iko, dict):
        return put("company", entity_id, iko)
    existing = _STORE.get(key)
    if existing:
        return existing
    obj = empty_iko(entity_id, company=company)
    return put("company", entity_id, obj)
