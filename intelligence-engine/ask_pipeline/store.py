"""In-process Ask Pipeline store — contexts, executions, telemetry, replay."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

_CONTEXTS: dict[str, dict[str, Any]] = {}
_EXECUTIONS: dict[str, dict[str, Any]] = {}
_TELEMETRY: dict[str, dict[str, Any]] = {}
_REPLAYS: dict[str, dict[str, Any]] = {}


def reset() -> None:
    _CONTEXTS.clear()
    _EXECUTIONS.clear()
    _TELEMETRY.clear()
    _REPLAYS.clear()


def put_context(pipeline_id: str, obj: dict[str, Any]) -> None:
    _CONTEXTS[pipeline_id] = deepcopy(obj)


def get_context(pipeline_id: str) -> dict[str, Any] | None:
    row = _CONTEXTS.get(pipeline_id)
    return deepcopy(row) if row else None


def put_execution(pipeline_id: str, obj: dict[str, Any]) -> None:
    _EXECUTIONS[pipeline_id] = deepcopy(obj)


def get_execution(pipeline_id: str) -> dict[str, Any] | None:
    row = _EXECUTIONS.get(pipeline_id)
    return deepcopy(row) if row else None


def list_executions(*, limit: int = 100) -> list[dict[str, Any]]:
    rows = sorted(
        _EXECUTIONS.values(),
        key=lambda r: str(r.get("finished_at") or r.get("started_at") or ""),
        reverse=True,
    )
    return deepcopy(rows[: max(1, limit)])


def put_telemetry(pipeline_id: str, obj: dict[str, Any]) -> None:
    _TELEMETRY[pipeline_id] = deepcopy(obj)


def get_telemetry(pipeline_id: str) -> dict[str, Any] | None:
    row = _TELEMETRY.get(pipeline_id)
    return deepcopy(row) if row else None


def list_telemetry(*, limit: int = 100) -> list[dict[str, Any]]:
    rows = sorted(
        _TELEMETRY.values(),
        key=lambda r: str(r.get("finished_at") or ""),
        reverse=True,
    )
    return deepcopy(rows[: max(1, limit)])


def put_replay(replay_id: str, obj: dict[str, Any]) -> None:
    _REPLAYS[replay_id] = deepcopy(obj)


def get_replay(replay_id: str) -> dict[str, Any] | None:
    row = _REPLAYS.get(replay_id)
    return deepcopy(row) if row else None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def questions_today() -> int:
    today = utc_now()[:10]
    return sum(1 for r in _EXECUTIONS.values() if str(r.get("started_at") or "").startswith(today))
