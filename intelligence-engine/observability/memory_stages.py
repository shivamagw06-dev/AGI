"""Which stage actually allocates the memory, recorded rather than guessed.

The engine climbs from ~2.5 GB after a deploy to 7.6 GB and stays there. Two
explanations have already been wrong: a schema-migration lock (falsified by
measurement - the migration is 58 ms) and duplicated FIE/HVIE runtimes in the
sidecar (removing them fixed latency completely and did not touch the memory
curve). Both were inferred from what was running rather than from what was
allocating.

So this measures. Every heavy stage records what it cost, and nothing decides
which stage is guilty until the numbers say so.

Peak, not just before and after
-------------------------------
The desk publishes artifacts stale-while-revalidate: the old artifact stays live
in ``_STATES[name]["payload"]`` for the whole build so requests keep being
answered, and is only released when the new one is adopted. A stage that starts
at 2 GB, holds old and new at 5 GB, and settles back to 2.4 GB looks free if you
only sample the ends. That shape is exactly what an 8 GB ceiling cannot absorb,
so a sampler thread watches RSS through the stage and keeps the maximum.

Written to disk, on purpose
---------------------------
The gather sidecar is a separate OS process from uvicorn - start_engine.sh forks
it precisely so they do not share an event loop. Measurements held in memory
would therefore be invisible to the HTTP process that has to report them. Each
record is appended to a file on the shared disk, and the diagnostic endpoint
only ever reads it.

Reading is free; nothing here starts work.
"""

from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Iterator, Optional

#: How often the sampler looks at RSS while a stage runs. Fast enough to catch a
#: publish that holds two artifacts for a second, cheap enough to leave on.
SAMPLE_SECONDS = 0.1

#: Keep the file bounded. A stage record is a few hundred bytes and the point is
#: the last run, not a history.
MAX_RECORDS = 400

_LOCK = threading.Lock()
_PAGE = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096


def rss_bytes() -> Optional[int]:
    """Resident set size of this process, without a new dependency.

    psutil is not in requirements.txt, so it may or may not exist on the
    instance; /proc/self/statm is always there on Linux, which is what Render
    runs. resource.getrusage is the fallback for local work on macOS, where it
    reports the high-water mark rather than the current size - good enough for a
    peak, wrong for an "after", and labelled as such by :func:`rss_is_exact`.
    """
    try:
        with open("/proc/self/statm", "r") as handle:
            return int(handle.read().split()[1]) * _PAGE
    except (OSError, IndexError, ValueError):
        pass
    try:
        import resource
        import sys
        raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # ru_maxrss is bytes on Darwin and kilobytes on Linux. Guessing from the
        # magnitude gets a 15 MB process wrong by a factor of 1024, so ask the
        # platform instead.
        return int(raw) if sys.platform == "darwin" else int(raw) * 1024
    except Exception:
        return None


def rss_is_exact() -> bool:
    """Whether rss_bytes() is the current size rather than a high-water mark."""
    return os.path.exists("/proc/self/statm")


def _path() -> str:
    root = os.environ.get("INSTITUTIONAL_WAREHOUSE_ROOT") or "/tmp"
    folder = os.path.join(root, "diagnostics")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "memory_stages.jsonl")


def record(entry: dict[str, Any]) -> None:
    """Append one measurement. Never raises - diagnostics must not break a job."""
    try:
        entry.setdefault("at", time.time())
        entry.setdefault("pid", os.getpid())
        entry.setdefault("role", os.environ.get("AGI_ROLE", "?"))
        with _LOCK:
            path = _path()
            with open(path, "a") as handle:
                handle.write(json.dumps(entry, default=str) + "\n")
            _trim(path)
    except Exception:
        pass


def _trim(path: str) -> None:
    try:
        if os.path.getsize(path) < 400_000:
            return
        with open(path, "r") as handle:
            lines = handle.readlines()[-MAX_RECORDS:]
        tmp = path + ".tmp"
        with open(tmp, "w") as handle:
            handle.writelines(lines)
        os.replace(tmp, path)
    except Exception:
        pass


def heartbeat(name: str, **facts: Any) -> None:
    """Mark that execution reached a point.

    The sidecar currently stops somewhere after `gather_worker_warehouse` and
    never reaches `gather_worker_ready`, and no log line says where. A heartbeat
    costs nothing and turns "it stops somewhere in there" into a line number.
    """
    record({"kind": "heartbeat", "stage": name, "rss_mb": _mb(rss_bytes()), **facts})


def _mb(value: Optional[int]) -> Optional[float]:
    return None if value is None else round(value / (1024 * 1024), 1)


class _Peak:
    """Samples RSS on a thread so a transient double-allocation is not missed."""

    def __init__(self) -> None:
        self.peak = rss_bytes() or 0
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> "_Peak":
        def watch() -> None:
            while not self._stop.wait(SAMPLE_SECONDS):
                now = rss_bytes()
                if now and now > self.peak:
                    self.peak = now
        self._thread = threading.Thread(target=watch, name="rss-peak", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> int:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        now = rss_bytes()
        if now and now > self.peak:
            self.peak = now
        return self.peak


@contextmanager
def stage(name: str, *, collect: bool = False, **facts: Any) -> Iterator[dict[str, Any]]:
    """Measure one heavy stage.

    Yields a dict the caller can fill in with what the stage actually did -
    ``rows``, ``items``, ``companies`` - so a delta can be read per unit of work
    rather than as a bare number.

    ``collect`` runs gc.collect() after the stage and reports what it freed.
    Off by default: it is not free, and an unchanged RSS afterwards proves
    nothing on its own - CPython returns arenas to the OS only when they empty
    completely, so fragmentation and a genuine leak look identical from here.
    """
    detail: dict[str, Any] = dict(facts)
    before = rss_bytes()
    threads_before = threading.active_count()
    peak = _Peak().start()
    started = time.perf_counter()
    error = None
    try:
        yield detail
    except BaseException as exc:  # noqa: BLE001 - recorded, then re-raised
        error = f"{type(exc).__name__}: {str(exc)[:160]}"
        raise
    finally:
        duration = time.perf_counter() - started
        high = peak.stop()
        after = rss_bytes()
        freed = None
        after_gc = None
        if collect:
            try:
                import gc
                freed = gc.collect()
                after_gc = rss_bytes()
            except Exception:
                pass
        record({
            "kind": "stage",
            "stage": name,
            "rss_before_mb": _mb(before),
            "rss_peak_mb": _mb(high),
            "rss_after_mb": _mb(after),
            "rss_delta_mb": (None if (before is None or after is None)
                             else round((after - before) / (1024 * 1024), 1)),
            "rss_peak_over_before_mb": (None if (before is None)
                                        else round((high - before) / (1024 * 1024), 1)),
            "duration_s": round(duration, 3),
            "threads_before": threads_before,
            "threads_after": threading.active_count(),
            "gc_freed_objects": freed,
            "rss_after_gc_mb": _mb(after_gc),
            "rss_exact": rss_is_exact(),
            "error": error,
            **detail,
        })


def process_table() -> list[dict[str, Any]]:
    """Live RSS for every process in the container, not just this one.

    start_engine.sh forks the gather sidecar, so "the engine's memory" is at
    least two processes. On 21 August that distinction was the whole answer:
    service memory went 3.09 -> 7.53 GB while the web process sat at 2332 MB
    and never moved, and the only per-stage reading available for the sidecar
    was stale because it was captured at stage entry and the stage never
    returned.

    Reading /proc is live and costs nothing, so a stalled process can no longer
    hide its size behind a measurement taken minutes ago.
    """
    out: list[dict[str, Any]] = []
    try:
        pids = [name for name in os.listdir("/proc") if name.isdigit()]
    except OSError:
        return out
    for pid in pids:
        try:
            with open(f"/proc/{pid}/statm", "r") as handle:
                rss = int(handle.read().split()[1]) * _PAGE
            with open(f"/proc/{pid}/cmdline", "rb") as handle:
                cmd = handle.read().replace(b"\x00", b" ").decode("utf-8", "replace").strip()
        except (OSError, IndexError, ValueError):
            continue
        if not cmd:
            continue
        out.append({"pid": int(pid), "rss_mb": _mb(rss), "cmd": cmd[:110]})
    out.sort(key=lambda row: row.get("rss_mb") or 0, reverse=True)
    return out


def read_stages(limit: int = 200) -> dict[str, Any]:
    """Everything recorded, newest last. Reads only - starts no work."""
    path = _path()
    rows: list[dict[str, Any]] = []
    try:
        with open(path, "r") as handle:
            for line in handle.readlines()[-int(limit):]:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except FileNotFoundError:
        pass

    worst = None
    for row in rows:
        if row.get("kind") != "stage":
            continue
        delta = row.get("rss_peak_over_before_mb")
        if delta is not None and (worst is None or delta > worst.get("rss_peak_over_before_mb", 0)):
            worst = row
    processes = process_table()
    return {
        "ok": True,
        "path": path,
        "records": len(rows),
        "rss_now_mb": _mb(rss_bytes()),
        "rss_exact": rss_is_exact(),
        # The number that located the missing 4.44 GB: every process, live.
        "processes": processes,
        "processes_total_rss_mb": round(sum(p.get("rss_mb") or 0 for p in processes), 1),
        "largest_peak_stage": worst,
        "stages": rows,
    }
