"""In-memory IERI store — immutable relationship / commodity / transmission objects."""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any

_LOCK = RLock()
_RELATIONSHIPS: dict[str, dict[str, Any]] = {}
_COMMODITIES: dict[str, dict[str, Any]] = {}
_TRANSMISSIONS: dict[str, dict[str, Any]] = {}
_NODES: dict[str, dict[str, Any]] = {}
_RUNS: list[dict[str, Any]] = []


def reset() -> None:
    with _LOCK:
        _RELATIONSHIPS.clear()
        _COMMODITIES.clear()
        _TRANSMISSIONS.clear()
        _NODES.clear()
        _RUNS.clear()


def put_relationship(obj: dict[str, Any]) -> dict[str, Any]:
    rid = str(obj.get("relationship_id") or "")
    if not rid:
        raise ValueError("relationship requires relationship_id")
    with _LOCK:
        if rid in _RELATIONSHIPS:
            return deepcopy(_RELATIONSHIPS[rid])
        _RELATIONSHIPS[rid] = deepcopy(obj)
        return deepcopy(_RELATIONSHIPS[rid])


def get_relationship(relationship_id: str) -> dict[str, Any] | None:
    with _LOCK:
        row = _RELATIONSHIPS.get(str(relationship_id or ""))
        return deepcopy(row) if row else None


def list_relationships(
    *,
    entity: str | None = None,
    relationship_type: str | None = None,
    semantics: str | None = None,
    as_of: str | None = None,
) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_RELATIONSHIPS.values())
    if entity:
        e = entity.lower()
        rows = [
            r
            for r in rows
            if e
            in (
                str(r.get("source_entity") or "").lower(),
                str(r.get("target_entity") or "").lower(),
                str((r.get("source_ref") or {}).get("id") or "").lower(),
                str((r.get("target_ref") or {}).get("id") or "").lower(),
            )
        ]
    if relationship_type:
        t = relationship_type.lower()
        rows = [r for r in rows if str(r.get("relationship_type") or "").lower() == t]
    if semantics:
        s = semantics.lower()
        rows = [r for r in rows if str(r.get("semantics") or "").lower() == s]
    if as_of:
        rows = [r for r in rows if str(r.get("available_from") or "") <= as_of]
    return [deepcopy(r) for r in sorted(rows, key=lambda x: x.get("relationship_id") or "")]


def relationship_count() -> int:
    with _LOCK:
        return len(_RELATIONSHIPS)


def put_commodity(obj: dict[str, Any]) -> dict[str, Any]:
    cid = str(obj.get("commodity_id") or "")
    if not cid:
        raise ValueError("commodity requires commodity_id")
    with _LOCK:
        if cid not in _COMMODITIES:
            _COMMODITIES[cid] = deepcopy(obj)
        return deepcopy(_COMMODITIES[cid])


def get_commodity(commodity_id: str) -> dict[str, Any] | None:
    with _LOCK:
        row = _COMMODITIES.get(str(commodity_id or "").lower())
        return deepcopy(row) if row else None


def list_commodities() -> list[dict[str, Any]]:
    with _LOCK:
        return [deepcopy(v) for _, v in sorted(_COMMODITIES.items())]


def commodity_count() -> int:
    with _LOCK:
        return len(_COMMODITIES)


def put_transmission(obj: dict[str, Any]) -> dict[str, Any]:
    tid = str(obj.get("transmission_id") or "")
    if not tid:
        raise ValueError("transmission requires transmission_id")
    with _LOCK:
        if tid not in _TRANSMISSIONS:
            _TRANSMISSIONS[tid] = deepcopy(obj)
        return deepcopy(_TRANSMISSIONS[tid])


def list_transmissions() -> list[dict[str, Any]]:
    with _LOCK:
        return [deepcopy(v) for _, v in sorted(_TRANSMISSIONS.items())]


def put_node(node: dict[str, Any]) -> dict[str, Any]:
    nid = str(node.get("node_id") or "")
    if not nid:
        raise ValueError("node requires node_id")
    with _LOCK:
        if nid not in _NODES:
            _NODES[nid] = deepcopy(node)
        return deepcopy(_NODES[nid])


def list_nodes(*, kind: str | None = None) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_NODES.values())
    if kind:
        k = kind.lower()
        rows = [n for n in rows if str(n.get("kind") or "").lower() == k]
    return [deepcopy(n) for n in sorted(rows, key=lambda x: x.get("node_id") or "")]


def node_count() -> int:
    with _LOCK:
        return len(_NODES)


def record_run(summary: dict[str, Any]) -> None:
    with _LOCK:
        _RUNS.append(deepcopy(summary))
        if len(_RUNS) > 50:
            del _RUNS[:-50]


def last_run() -> dict[str, Any] | None:
    with _LOCK:
        return deepcopy(_RUNS[-1]) if _RUNS else None
