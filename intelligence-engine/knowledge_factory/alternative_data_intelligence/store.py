"""In-memory IADI store — immutable datasets and observations."""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any

_LOCK = RLock()
_DATASETS: dict[str, dict[str, Any]] = {}
_OBSERVATIONS: dict[str, dict[str, Any]] = {}  # obs_id -> row
_BY_DATASET: dict[str, list[str]] = {}
_RUNS: list[dict[str, Any]] = []


def reset() -> None:
    with _LOCK:
        _DATASETS.clear()
        _OBSERVATIONS.clear()
        _BY_DATASET.clear()
        _RUNS.clear()


def put_dataset(obj: dict[str, Any]) -> dict[str, Any]:
    did = str(obj.get("dataset_id") or "")
    if not did:
        raise ValueError("dataset requires dataset_id")
    with _LOCK:
        if did not in _DATASETS:
            _DATASETS[did] = deepcopy(obj)
            _BY_DATASET.setdefault(did, [])
        return deepcopy(_DATASETS[did])


def get_dataset(dataset_id: str) -> dict[str, Any] | None:
    with _LOCK:
        row = _DATASETS.get(str(dataset_id or "").lower())
        return deepcopy(row) if row else None


def list_datasets() -> list[dict[str, Any]]:
    with _LOCK:
        return [deepcopy(v) for _, v in sorted(_DATASETS.items())]


def dataset_count() -> int:
    with _LOCK:
        return len(_DATASETS)


def put_observation(obj: dict[str, Any]) -> dict[str, Any]:
    oid = str(obj.get("observation_id") or "")
    did = str(obj.get("dataset_id") or "")
    if not oid or not did:
        raise ValueError("observation requires observation_id and dataset_id")
    with _LOCK:
        if oid in _OBSERVATIONS:
            return deepcopy(_OBSERVATIONS[oid])
        _OBSERVATIONS[oid] = deepcopy(obj)
        _BY_DATASET.setdefault(did, []).append(oid)
        return deepcopy(_OBSERVATIONS[oid])


def list_observations(
    *,
    dataset_id: str | None = None,
    as_of: str | None = None,
) -> list[dict[str, Any]]:
    with _LOCK:
        if dataset_id:
            ids = list(_BY_DATASET.get(str(dataset_id).lower(), []))
            rows = [_OBSERVATIONS[i] for i in ids if i in _OBSERVATIONS]
        else:
            rows = list(_OBSERVATIONS.values())
    if as_of:
        rows = [r for r in rows if str(r.get("available_from") or "") <= as_of]
    return [
        deepcopy(r)
        for r in sorted(rows, key=lambda x: (x.get("date") or "", x.get("observation_id") or ""))
    ]


def observation_count() -> int:
    with _LOCK:
        return len(_OBSERVATIONS)


def record_run(summary: dict[str, Any]) -> None:
    with _LOCK:
        _RUNS.append(deepcopy(summary))
        if len(_RUNS) > 50:
            del _RUNS[:-50]


def last_run() -> dict[str, Any] | None:
    with _LOCK:
        return deepcopy(_RUNS[-1]) if _RUNS else None
