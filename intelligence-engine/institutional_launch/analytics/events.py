"""Raw product analytics events (L-01)."""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from typing import Any, Deque, Dict, List, Optional

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


_LOCK = threading.Lock()
_EVENTS: Deque[dict[str, Any]] = deque(maxlen=10000)
_USERS_DAY: Dict[str, set] = {}
_USERS_WEEK: Dict[str, set] = {}
_USERS_MONTH: Dict[str, set] = {}


def reset_for_tests() -> None:
    with _LOCK:
        _EVENTS.clear()
        _USERS_DAY.clear()
        _USERS_WEEK.clear()
        _USERS_MONTH.clear()


def _bucket(ts: float, kind: str) -> str:
    if kind == "day":
        return time.strftime("%Y-%m-%d", time.gmtime(ts))
    if kind == "week":
        return time.strftime("%Y-W%W", time.gmtime(ts))
    return time.strftime("%Y-%m", time.gmtime(ts))


def emit_event(
    name: str,
    *,
    user_id: str = "",
    stage: str = "",
    duration_ms: Optional[float] = None,
    ok: bool = True,
    error: str = "",
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    ts = time.time()
    row = {
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "name": name,
        "stage": stage,
        "user_id": user_id or "anonymous",
        "duration_ms": round(duration_ms, 3) if duration_ms is not None else None,
        "ok": bool(ok),
        "error": error or None,
        "timestamp": now_iso(),
        "ts": ts,
        "meta": dict(meta or {}),
    }
    uid = row["user_id"]
    with _LOCK:
        _EVENTS.append(row)
        _USERS_DAY.setdefault(_bucket(ts, "day"), set()).add(uid)
        _USERS_WEEK.setdefault(_bucket(ts, "week"), set()).add(uid)
        _USERS_MONTH.setdefault(_bucket(ts, "month"), set()).add(uid)
    return row


def recent_events(limit: int = 50, *, name: str = "", stage: str = "") -> List[dict[str, Any]]:
    with _LOCK:
        rows = list(_EVENTS)
    if name:
        rows = [r for r in rows if r.get("name") == name]
    if stage:
        rows = [r for r in rows if r.get("stage") == stage]
    return list(reversed(rows[-limit:]))


def adoption_counts() -> dict[str, Any]:
    now = time.time()
    with _LOCK:
        dau = len(_USERS_DAY.get(_bucket(now, "day"), set()))
        wau = len(_USERS_WEEK.get(_bucket(now, "week"), set()))
        mau = len(_USERS_MONTH.get(_bucket(now, "month"), set()))
        total_events = len(_EVENTS)
    return {
        "daily_active_users": dau,
        "weekly_active_users": wau,
        "monthly_active_users": mau,
        "total_events": total_events,
    }
