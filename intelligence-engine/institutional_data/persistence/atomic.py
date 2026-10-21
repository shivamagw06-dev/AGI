"""Atomic writes + cross-process file locking for crash-safe commits."""

from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def atomic_write_bytes(path: Path | str, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        # Best-effort directory fsync for durability on POSIX
        try:
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except Exception:
            pass
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def atomic_write_json(path: Path | str, payload: Any, *, indent: int = 2) -> None:
    data = json.dumps(payload, indent=indent, default=str, sort_keys=True).encode("utf-8")
    atomic_write_bytes(path, data)


@contextmanager
def file_lock(path: Path | str, *, timeout_s: float = 30.0, poll_s: float = 0.05) -> Iterator[None]:
    """Exclusive lock file (fcntl on POSIX; no-op fallback elsewhere)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path if path.suffix == ".lock" else Path(str(path) + ".lock")
    fh = open(lock_path, "a+", encoding="utf-8")
    start = time.time()
    locked = False
    try:
        try:
            import fcntl  # type: ignore

            while True:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except BlockingIOError:
                    if time.time() - start >= timeout_s:
                        raise TimeoutError(f"file_lock_timeout:{lock_path}")
                    time.sleep(poll_s)
        except ImportError:
            # Non-POSIX: rely on process-local coordination only
            locked = True
        yield
    finally:
        if locked:
            try:
                import fcntl  # type: ignore

                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
        try:
            fh.close()
        except Exception:
            pass
