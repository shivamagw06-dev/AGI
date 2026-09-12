"""Helpers for production hardening."""

from __future__ import annotations

import hashlib
import json
import resource
import time
from datetime import datetime, timezone
from typing import Any, Callable


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_float(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))


def fingerprint(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()[:20]


def rss_mb() -> float:
    # ru_maxrss is KB on Linux
    try:
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 2)
    except Exception:
        return 0.0


def timed(fn: Callable[..., Any], *args, **kwargs) -> tuple[Any, float]:
    t0 = time.perf_counter()
    out = fn(*args, **kwargs)
    return out, round((time.perf_counter() - t0) * 1000.0, 2)


def soft_call(label: str, fn: Callable[..., Any], *args, **kwargs) -> dict[str, Any]:
    try:
        out = fn(*args, **kwargs)
        if isinstance(out, dict):
            return {**out, "_soft": label, "_ok": True}
        return {"_soft": label, "_ok": True, "value": out}
    except Exception as exc:  # noqa: BLE001
        return {"_soft": label, "_ok": False, "error": f"{type(exc).__name__}:{str(exc)[:140]}"}


def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return None


def age_days(ts: str | None) -> float | None:
    dt = parse_iso(ts)
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0
