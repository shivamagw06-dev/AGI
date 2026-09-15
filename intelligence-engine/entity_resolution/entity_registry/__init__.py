"""Entity registry — canonical institutional entities (soft fallback under IKG)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from entity_resolution.entity_registry.seed import AMBIGUOUS_STEMS, SEED_ENTITIES

_BY_ID: dict[str, dict[str, Any]] = {e["id"]: e for e in SEED_ENTITIES}
_ALIAS_INDEX: dict[str, list[str]] = {}


def _rebuild_alias_index() -> None:
    global _ALIAS_INDEX
    idx: dict[str, list[str]] = {}
    for ent in SEED_ENTITIES:
        keys = [str(ent.get("canonical_name") or "").lower()]
        if ent.get("ticker"):
            keys.append(str(ent["ticker"]).lower())
        keys.extend(str(a).lower() for a in (ent.get("aliases") or []))
        for k in keys:
            k = k.strip()
            if not k:
                continue
            idx.setdefault(k, [])
            if ent["id"] not in idx[k]:
                idx[k].append(ent["id"])
    _ALIAS_INDEX = idx


_rebuild_alias_index()


def all_entities() -> list[dict[str, Any]]:
    return [deepcopy(e) for e in SEED_ENTITIES]


def get_entity(entity_id: str) -> dict[str, Any] | None:
    row = _BY_ID.get(entity_id)
    return deepcopy(row) if row else None


def lookup_alias(alias: str) -> list[dict[str, Any]]:
    key = (alias or "").strip().lower()
    ids = _ALIAS_INDEX.get(key) or []
    return [get_entity(i) for i in ids if get_entity(i)]


def ambiguous_matches(stem: str) -> list[dict[str, Any]]:
    ids = AMBIGUOUS_STEMS.get((stem or "").strip().lower()) or []
    return [get_entity(i) for i in ids if get_entity(i)]


def registry_stats() -> dict[str, Any]:
    types: dict[str, int] = {}
    for e in SEED_ENTITIES:
        t = str(e.get("entity_type") or "Unknown")
        types[t] = types.get(t, 0) + 1
    return {
        "entity_count": len(SEED_ENTITIES),
        "alias_count": sum(len(v) for v in _ALIAS_INDEX.values()),
        "ambiguous_stems": list(AMBIGUOUS_STEMS.keys()),
        "by_type": types,
    }
