"""The desk's universe, built in the background and published atomically.

The desk used to build its universe inside whichever request happened to arrive
after the cache expired. Measured on 21 August: 200 seconds on the first request
after a restart, 12 to 25 seconds every time the fifteen-minute cache turned
over, and a timeout whenever a backfill slice was running at the same time.

The client's wait was the rebuild's duration. That is the thing this fixes.

Three properties matter, in this order:

* A request never waits for a build. It is served whatever is on hand, and told
  how old that is.
* A failed build never costs the last good one. Serving something stale and
  saying so beats serving nothing.
* A restart does not start from nothing. The snapshot lives on the mounted disk,
  so a fresh process serves the previous build while it makes a new one.

Staleness is not hidden. Every payload carries when it was built and whether the
builder is currently unwell, so a reader can decide rather than guess.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

SNAPSHOT_VERSION = 2
FILENAME = "desk_universe.json"

# How old a snapshot may get before a rebuild is triggered. The rebuild happens
# behind the request, so this is not a latency budget - it is how stale the desk
# is allowed to be, which is a different question.
REFRESH_AFTER_SEC = 300.0

# When a build fails, how long before trying again. Long enough that a broken
# warehouse is not hammered, short enough to recover without a deploy.
RETRY_AFTER_SEC = 120.0

FRESH, STALE, DEGRADED, EMPTY = "FRESH", "STALE", "DEGRADED", "EMPTY"

_STATE: dict[str, Any] = {
    "rows": None,
    "built_at": 0.0,
    "build_seconds": None,
    "source": None,
    "failures": 0,
    "last_error": None,
    "last_attempt_at": 0.0,
    "builds": 0,
}
_LOCK = threading.Lock()
_BUILDING = threading.Event()


def snapshot_path() -> Path:
    from institutional_warehouse.db import store_root

    return Path(store_root()) / FILENAME


def _write_atomically(path: Path, payload: dict[str, Any]) -> None:
    """Write beside the target and rename over it.

    A process killed mid-write must not leave a half-written snapshot that the
    next boot reads as the last good one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".desk_", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(payload, out)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def save(rows: list[dict[str, Any]], *, source: str, build_seconds: float) -> bool:
    if not rows:
        return False
    try:
        _write_atomically(snapshot_path(), {
            "version": SNAPSHOT_VERSION,
            "built_at": time.time(),
            "build_seconds": round(build_seconds, 2),
            "source": source,
            "count": len(rows),
            "rows": rows,
        })
        return True
    except Exception:
        # A snapshot that cannot be persisted is still usable in memory; losing
        # it on the next restart is worse than nothing only if that stops the
        # process serving now, which it does not.
        return False


def load() -> Optional[dict[str, Any]]:
    path = snapshot_path()
    try:
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if int(payload.get("version") or 0) != SNAPSHOT_VERSION:
        return None
    rows = payload.get("rows")
    return payload if isinstance(rows, list) and rows else None


def age_seconds() -> Optional[float]:
    built = float(_STATE.get("built_at") or 0.0)
    return None if not built else max(0.0, time.time() - built)


def freshness() -> str:
    if not _STATE.get("rows"):
        return EMPTY
    if int(_STATE.get("failures") or 0) >= 2:
        return DEGRADED
    age = age_seconds()
    return FRESH if age is not None and age < REFRESH_AFTER_SEC else STALE


def status() -> dict[str, Any]:
    age = age_seconds()
    return {
        "freshness": freshness(),
        "rows": len(_STATE.get("rows") or []),
        "age_seconds": None if age is None else round(age, 1),
        "build_seconds": _STATE.get("build_seconds"),
        "source": _STATE.get("source"),
        "builds": _STATE.get("builds"),
        "failures": _STATE.get("failures"),
        "last_error": _STATE.get("last_error"),
        "building_now": _BUILDING.is_set(),
        "persisted": snapshot_path().exists(),
    }


def _adopt(rows: list[dict[str, Any]], *, source: str, build_seconds: float,
           built_at: Optional[float] = None) -> None:
    _STATE["rows"] = rows
    _STATE["built_at"] = built_at or time.time()
    _STATE["build_seconds"] = build_seconds
    _STATE["source"] = source
    _STATE["failures"] = 0
    _STATE["last_error"] = None


def prime() -> bool:
    """Adopt whatever the last process left on disk. Called once at import."""
    payload = load()
    if not payload:
        return False
    with _LOCK:
        if _STATE.get("rows"):
            return False
        _adopt(payload["rows"], source=str(payload.get("source") or "disk"),
               build_seconds=payload.get("build_seconds"),
               built_at=float(payload.get("built_at") or 0.0))
    return True


def rebuild(builder: Callable[[], list[dict[str, Any]]], *, source: str = "warehouse") -> dict[str, Any]:
    """Build a new universe and publish it, or leave the old one alone.

    Only one build runs at a time. A second caller arriving mid-build is told so
    rather than queued: two identical scans of the same tables help nobody and
    compete for the same database lock.
    """
    if _BUILDING.is_set():
        return {"ok": False, "skipped": "already_building"}
    _BUILDING.set()
    started = time.time()
    _STATE["last_attempt_at"] = started
    try:
        rows = builder()
        took = time.time() - started
        if not rows:
            # An empty result is a failed build, not a universe of nothing.
            _STATE["failures"] = int(_STATE.get("failures") or 0) + 1
            _STATE["last_error"] = "builder_returned_no_rows"
            return {"ok": False, "error": "builder_returned_no_rows",
                    "kept_previous": bool(_STATE.get("rows"))}
        with _LOCK:
            _adopt(rows, source=source, build_seconds=took)
            _STATE["builds"] = int(_STATE.get("builds") or 0) + 1
        persisted = save(rows, source=source, build_seconds=took)
        return {"ok": True, "rows": len(rows), "build_seconds": round(took, 2),
                "persisted": persisted}
    except Exception as exc:
        _STATE["failures"] = int(_STATE.get("failures") or 0) + 1
        _STATE["last_error"] = str(exc)[:300]
        return {"ok": False, "error": str(exc)[:300],
                "kept_previous": bool(_STATE.get("rows"))}
    finally:
        _BUILDING.clear()


def should_refresh() -> bool:
    if _BUILDING.is_set():
        return False
    if not _STATE.get("rows"):
        return True
    if int(_STATE.get("failures") or 0):
        return (time.time() - float(_STATE.get("last_attempt_at") or 0.0)) >= RETRY_AFTER_SEC
    age = age_seconds()
    return age is None or age >= REFRESH_AFTER_SEC


def current(builder: Callable[[], list[dict[str, Any]]],
            *, source: str = "warehouse") -> list[dict[str, Any]]:
    """The universe, now. Never waits for a build unless there is nothing at all.

    The one case that blocks is a process that has never built and found nothing
    on disk. There is no stale answer to give, and an empty desk is not an
    answer either.
    """
    rows = _STATE.get("rows")
    if rows and should_refresh():
        threading.Thread(target=rebuild, args=(builder,), kwargs={"source": source},
                         name="desk-snapshot-refresh", daemon=True).start()
    if rows:
        return rows
    if prime():
        return _STATE.get("rows") or []
    rebuild(builder, source=source)
    return _STATE.get("rows") or []


def reset() -> None:
    """For tests. Does not delete the persisted snapshot."""
    with _LOCK:
        _STATE.update({"rows": None, "built_at": 0.0, "build_seconds": None,
                       "source": None, "failures": 0, "last_error": None,
                       "last_attempt_at": 0.0, "builds": 0})
    _BUILDING.clear()
