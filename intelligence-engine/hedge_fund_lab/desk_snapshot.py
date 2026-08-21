"""Expensive read-side artifacts, built in the background and published atomically.

The desk used to build everything it needed inside whichever request happened to
arrive after a cache expired. Measured on 21 August: 256 seconds on the first
request after a restart, and a timeout whenever a backfill slice ran at the same
time. The client's wait was the rebuild's duration.

An artifact qualifies for this treatment when it is expensive, deterministic, and
needed before the desk can answer at all. Nothing else belongs here - this is not
a general cache, and persisting arbitrary intermediate state would trade one
problem for a directory full of stale files.

Three properties, in the order they matter:

* A request never waits for a build. It is served whatever is on hand and told
  how old that is.
* A failed build never costs the last good one. Serving something stale and
  saying so beats serving nothing.
* A restart does not start from nothing. Artifacts live on the mounted disk, so
  a fresh process serves the previous build while it makes a new one.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

SNAPSHOT_VERSION = 3

# Default staleness budget. Overridden per artifact, because "how old may this
# be" is a question about the data, not about how long it takes to build.
REFRESH_AFTER_SEC = float(os.getenv("DESK_SNAPSHOT_REFRESH_SEC", "1800") or 1800)

# When a build fails, how long before trying again. Long enough that a broken
# warehouse is not hammered, short enough to recover without a deploy.
RETRY_AFTER_SEC = 120.0

# A build slower than this is worth reporting even when it succeeds.
SLOW_BUILD_SEC = 60.0

FRESH, STALE, DEGRADED, EMPTY = "FRESH", "STALE", "DEGRADED", "EMPTY"

_STATES: dict[str, dict[str, Any]] = {}
_LOCKS: dict[str, threading.Lock] = {}
_BUILDING: dict[str, threading.Event] = {}
_REGISTRY: dict[str, dict[str, Any]] = {}
_GLOBAL_LOCK = threading.Lock()


def _blank() -> dict[str, Any]:
    return {"payload": None, "built_at": 0.0, "build_seconds": None, "source": None,
            "failures": 0, "last_error": None, "last_attempt_at": 0.0, "builds": 0}


def _state(name: str) -> dict[str, Any]:
    with _GLOBAL_LOCK:
        if name not in _STATES:
            _STATES[name] = _blank()
            _LOCKS[name] = threading.Lock()
            _BUILDING[name] = threading.Event()
        return _STATES[name]


def register(name: str, builder: Callable[[], Any], *, refresh_after: float = REFRESH_AFTER_SEC,
             source: str = "warehouse") -> None:
    """Declare an artifact so it can be primed and refreshed without a request."""
    _state(name)
    _REGISTRY[name] = {"builder": builder, "refresh_after": float(refresh_after),
                       "source": source}


def snapshot_path(name: str) -> Path:
    from institutional_warehouse.db import store_root

    return Path(store_root()) / f"desk_{name}.json"


def _write_atomically(path: Path, payload: dict[str, Any]) -> None:
    """Write beside the target and rename over it.

    A process killed mid-write must not leave a half-written file that the next
    boot reads as the last good one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.stem}_", suffix=".tmp")
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


def _size(payload: Any) -> Optional[int]:
    try:
        return len(payload)
    except TypeError:
        return None


def save(name: str, payload: Any, *, source: str, build_seconds: float) -> bool:
    if not payload:
        return False
    try:
        _write_atomically(snapshot_path(name), {
            "version": SNAPSHOT_VERSION,
            "name": name,
            "built_at": time.time(),
            "build_seconds": round(build_seconds, 2),
            "source": source,
            "size": _size(payload),
            "payload": payload,
        })
        return True
    except Exception:
        # An artifact that cannot be persisted is still usable in memory. Losing
        # it at the next restart is worse than nothing only if that stops this
        # process serving now, which it does not.
        return False


def load(name: str) -> Optional[dict[str, Any]]:
    path = snapshot_path(name)
    try:
        if not path.exists():
            return None
        blob = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if int(blob.get("version") or 0) != SNAPSHOT_VERSION:
        return None
    return blob if blob.get("payload") else None


def age_seconds(name: str) -> Optional[float]:
    built = float(_state(name).get("built_at") or 0.0)
    return None if not built else max(0.0, time.time() - built)


def refresh_after(name: str) -> float:
    return float((_REGISTRY.get(name) or {}).get("refresh_after") or REFRESH_AFTER_SEC)


def freshness(name: str) -> str:
    st = _state(name)
    if not st.get("payload"):
        return EMPTY
    if int(st.get("failures") or 0) >= 2:
        return DEGRADED
    age = age_seconds(name)
    return FRESH if age is not None and age < refresh_after(name) else STALE


def status(name: str) -> dict[str, Any]:
    st = _state(name)
    age = age_seconds(name)
    return {
        "name": name,
        "freshness": freshness(name),
        "size": _size(st.get("payload")),
        "age_seconds": None if age is None else round(age, 1),
        "build_seconds": st.get("build_seconds"),
        "source": st.get("source"),
        "builds": st.get("builds"),
        "failures": st.get("failures"),
        "last_error": st.get("last_error"),
        "building_now": _BUILDING[name].is_set() if name in _BUILDING else False,
        "persisted": snapshot_path(name).exists(),
        "refresh_after_seconds": refresh_after(name),
        "max_stale_seconds": round(refresh_after(name) * 4, 1),
        "slow_build": bool((st.get("build_seconds") or 0) > SLOW_BUILD_SEC),
    }


def status_all() -> list[dict[str, Any]]:
    return [status(n) for n in sorted(set(_REGISTRY) | set(_STATES))]


def _adopt(name: str, payload: Any, *, source: str, build_seconds: Optional[float],
           built_at: Optional[float] = None) -> None:
    # The moment old and new stop coexisting. Until this line the previous
    # artifact is still live in st["payload"] so requests keep being answered,
    # which is the whole point of stale-while-revalidate and also means peak RSS
    # during a rebuild is roughly both copies at once.
    from observability import memory_stages as ms

    st = _state(name)
    had_previous = st.get("payload") is not None
    ms.heartbeat("artifact_adopt", artifact=name, source=source,
                 replacing_previous=had_previous,
                 build_seconds=None if build_seconds is None else round(build_seconds, 2))
    st["payload"] = payload
    st["built_at"] = built_at or time.time()
    st["build_seconds"] = build_seconds
    st["source"] = source
    st["failures"] = 0
    st["last_error"] = None


def prime(name: str) -> bool:
    """Adopt whatever the last process left on disk."""
    blob = load(name)
    if not blob:
        return False
    st = _state(name)
    with _LOCKS[name]:
        if st.get("payload"):
            return False
        _adopt(name, blob["payload"], source=str(blob.get("source") or "disk"),
               build_seconds=blob.get("build_seconds"),
               built_at=float(blob.get("built_at") or 0.0))
    return True


def rebuild(name: str, builder: Optional[Callable[[], Any]] = None, *,
            source: str = "") -> dict[str, Any]:
    """Build and publish, or leave the previous artifact untouched.

    Only one build per artifact runs at a time. A second caller arriving
    mid-build is told so rather than queued: two identical scans of the same
    tables help nobody and compete for the same database lock.
    """
    _state(name)
    reg = _REGISTRY.get(name) or {}
    builder = builder or reg.get("builder")
    source = source or str(reg.get("source") or "warehouse")
    if builder is None:
        return {"ok": False, "error": f"no_builder_for:{name}"}

    if _BUILDING[name].is_set():
        return {"ok": False, "skipped": "already_building"}
    _BUILDING[name].set()
    started = time.time()
    st = _state(name)
    st["last_attempt_at"] = started
    try:
        payload = builder()
        took = time.time() - started
        if not payload:
            # An empty result is a failed build, not a discovery that the data
            # is gone.
            st["failures"] = int(st.get("failures") or 0) + 1
            st["last_error"] = "builder_returned_nothing"
            return {"ok": False, "error": "builder_returned_nothing",
                    "kept_previous": bool(st.get("payload"))}
        with _LOCKS[name]:
            _adopt(name, payload, source=source, build_seconds=took)
            st["builds"] = int(st.get("builds") or 0) + 1
        persisted = save(name, payload, source=source, build_seconds=took)
        return {"ok": True, "name": name, "size": _size(payload),
                "build_seconds": round(took, 2), "persisted": persisted,
                "slow": took > SLOW_BUILD_SEC}
    except Exception as exc:
        st["failures"] = int(st.get("failures") or 0) + 1
        st["last_error"] = str(exc)[:300]
        return {"ok": False, "error": str(exc)[:300],
                "kept_previous": bool(st.get("payload"))}
    finally:
        _BUILDING[name].clear()


def should_refresh(name: str) -> bool:
    st = _state(name)
    if _BUILDING[name].is_set():
        return False
    if not st.get("payload"):
        return True
    if int(st.get("failures") or 0):
        return (time.time() - float(st.get("last_attempt_at") or 0.0)) >= RETRY_AFTER_SEC
    age = age_seconds(name)
    return age is None or age >= refresh_after(name)


def current(name: str, builder: Optional[Callable[[], Any]] = None, *,
            source: str = "", default: Any = None) -> Any:
    """The artifact, now. Never waits for a build unless there is nothing at all.

    The one case that blocks is a process that has never built this artifact and
    found nothing on disk. There is no stale answer to give.
    """
    st = _state(name)
    payload = st.get("payload")

    if payload is None and prime(name):
        payload = _state(name).get("payload")

    if payload is not None and should_refresh(name):
        threading.Thread(target=rebuild, args=(name, builder), kwargs={"source": source},
                         name=f"desk-refresh-{name}", daemon=True).start()

    if payload is not None:
        return payload

    rebuild(name, builder, source=source)
    return _state(name).get("payload") if _state(name).get("payload") is not None else default


def prime_all() -> dict[str, Any]:
    """Adopt every registered artifact from disk. Called once at startup.

    This is what makes a deploy cheap: the process comes up already able to
    answer, and the rebuild happens behind whatever arrives first.
    """
    out = {}
    for name in sorted(_REGISTRY):
        out[name] = prime(name)
    return {"ok": True, "primed": out}


def refresh_stale() -> dict[str, Any]:
    """Rebuild anything past its staleness budget. For a scheduled warmer."""
    done = {}
    for name in sorted(_REGISTRY):
        done[name] = rebuild(name) if should_refresh(name) else {"ok": True, "skipped": "fresh"}
    return {"ok": True, "artifacts": done}


def forget(name: str) -> None:
    """Clear the artifact and remove what it left on disk.

    reset() deliberately keeps the file, because a process restarting should
    find the last good build. A test asking for a clean slate wants the opposite,
    and a reset that leaves the artifact readable is not a reset - the next call
    primes from disk and the builder under test is never invoked.
    """
    reset(name)
    try:
        snapshot_path(name).unlink()
    except OSError:
        pass


def reset(name: Optional[str] = None) -> None:
    """For tests. Does not delete persisted files."""
    names = [name] if name else list(_STATES)
    for n in names:
        _state(n)
        with _LOCKS[n]:
            _STATES[n] = _blank()
        _BUILDING[n].clear()
