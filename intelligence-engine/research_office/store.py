"""Research Office stores — registry, queue, watchlists, telemetry, history."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

_PUBLICATIONS: dict[str, dict[str, Any]] = {}
_HISTORY: list[dict[str, Any]] = []
_QUEUE: dict[str, Any] = {}
_WATCHLISTS: dict[str, list[dict[str, Any]]] = {}
_TELEMETRY: list[dict[str, Any]] = []
_RUNS: dict[str, dict[str, Any]] = {}
_STATUS: dict[str, Any] = {
    "state": "IDLE",
    "last_run_id": None,
    "ready_for_users": False,
    "publications_today": 0,
}


def reset() -> None:
    _PUBLICATIONS.clear()
    _HISTORY.clear()
    _QUEUE.clear()
    _WATCHLISTS.clear()
    _TELEMETRY.clear()
    _RUNS.clear()
    _STATUS.clear()
    _STATUS.update(
        {
            "state": "IDLE",
            "last_run_id": None,
            "ready_for_users": False,
            "publications_today": 0,
        }
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def set_status(**kwargs: Any) -> dict[str, Any]:
    _STATUS.update(kwargs)
    return deepcopy(_STATUS)


def get_status() -> dict[str, Any]:
    return deepcopy(_STATUS)


def put_publication(pub_id: str, obj: dict[str, Any]) -> None:
    _PUBLICATIONS[pub_id] = deepcopy(obj)


def get_publication(pub_id: str) -> dict[str, Any] | None:
    row = _PUBLICATIONS.get(pub_id)
    return deepcopy(row) if row else None


def list_publications(*, limit: int = 100, pub_type: str | None = None) -> list[dict[str, Any]]:
    rows = list(_PUBLICATIONS.values())
    if pub_type:
        rows = [r for r in rows if r.get("publication_type") == pub_type]
    rows.sort(key=lambda r: str(r.get("created") or ""), reverse=True)
    return deepcopy(rows[: max(1, limit)])


def put_queue(queue: dict[str, Any]) -> None:
    _QUEUE.clear()
    _QUEUE.update(deepcopy(queue))


def get_queue() -> dict[str, Any]:
    return deepcopy(_QUEUE)


def put_watchlists(lists: dict[str, list[dict[str, Any]]]) -> None:
    _WATCHLISTS.clear()
    for k, v in lists.items():
        _WATCHLISTS[k] = deepcopy(v)


def get_watchlists() -> dict[str, list[dict[str, Any]]]:
    return deepcopy(_WATCHLISTS)


def append_history(row: dict[str, Any]) -> None:
    _HISTORY.append(deepcopy(row))


def list_history(*, limit: int = 50) -> list[dict[str, Any]]:
    return deepcopy(list(reversed(_HISTORY[-max(1, limit) :])))


def put_run(run_id: str, row: dict[str, Any]) -> None:
    _RUNS[run_id] = deepcopy(row)


def get_run(run_id: str) -> dict[str, Any] | None:
    row = _RUNS.get(run_id)
    return deepcopy(row) if row else None


def append_telemetry(row: dict[str, Any]) -> None:
    _TELEMETRY.append(deepcopy(row))


def list_telemetry(*, limit: int = 100) -> list[dict[str, Any]]:
    return deepcopy(list(reversed(_TELEMETRY[-max(1, limit) :])))
