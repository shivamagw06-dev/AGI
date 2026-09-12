"""End-to-end user journey instrumentation (L-01)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from institutional_launch.analytics.events import emit_event
from institutional_launch.schema import JOURNEY_STAGES

_LOCK = threading.Lock()
# stage → counters
_STATS: Dict[str, dict[str, Any]] = defaultdict(
    lambda: {
        "starts": 0,
        "completions": 0,
        "errors": 0,
        "drop_offs": 0,
        "duration_ms_sum": 0.0,
        "duration_ms_n": 0,
    }
)
_SESSIONS: Dict[str, dict[str, Any]] = {}


def reset_for_tests() -> None:
    with _LOCK:
        _STATS.clear()
        _SESSIONS.clear()


def record_journey_step(
    stage: str,
    *,
    user_id: str = "",
    session_id: str = "",
    duration_ms: Optional[float] = None,
    ok: bool = True,
    error: str = "",
    completed: bool = True,
    dropped: bool = False,
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    stage_n = str(stage or "").strip().lower().replace(" ", "_").replace("-", "_")
    if stage_n not in JOURNEY_STAGES:
        # allow aliases
        aliases = {
            "ask": "ask_agi",
            "workspace": "research_workspace",
            "research": "research_workspace",
            "pub": "publication",
            "publish": "publication",
        }
        stage_n = aliases.get(stage_n, stage_n)
    if stage_n not in JOURNEY_STAGES:
        stage_n = "dashboard"

    with _LOCK:
        st = _STATS[stage_n]
        st["starts"] += 1
        if completed and ok:
            st["completions"] += 1
        if not ok:
            st["errors"] += 1
        if dropped or (not completed and not ok):
            st["drop_offs"] += 1
        if duration_ms is not None:
            st["duration_ms_sum"] += float(duration_ms)
            st["duration_ms_n"] += 1
        if session_id:
            sess = _SESSIONS.setdefault(
                session_id,
                {"session_id": session_id, "user_id": user_id, "stages": [], "started_at": time.time()},
            )
            sess["stages"].append(stage_n)
            sess["last_stage"] = stage_n

    emit_event(
        f"journey.{stage_n}",
        user_id=user_id,
        stage=stage_n,
        duration_ms=duration_ms,
        ok=ok,
        error=error,
        meta={"completed": completed, "dropped": dropped, **(meta or {})},
    )
    return {"ok": True, "stage": stage_n, "completed": completed and ok}


def stage_metrics() -> dict[str, Any]:
    with _LOCK:
        out = {}
        for stage in JOURNEY_STAGES:
            st = dict(_STATS.get(stage) or {})
            n = int(st.get("duration_ms_n") or 0)
            mean = round(st["duration_ms_sum"] / n, 3) if n else None
            starts = int(st.get("starts") or 0)
            completions = int(st.get("completions") or 0)
            out[stage] = {
                "starts": starts,
                "completions": completions,
                "errors": int(st.get("errors") or 0),
                "drop_offs": int(st.get("drop_offs") or 0),
                "completion_rate": round(completions / starts, 4) if starts else None,
                "mean_duration_ms": mean,
            }
    return out


def journey_funnel() -> dict[str, Any]:
    metrics = stage_metrics()
    steps = []
    prev = None
    for stage in JOURNEY_STAGES:
        m = metrics[stage]
        drop_from_prev = None
        if prev is not None and prev["completions"]:
            drop_from_prev = round(
                1.0 - (m["starts"] / prev["completions"]) if prev["completions"] else 0.0,
                4,
            )
            if drop_from_prev < 0:
                drop_from_prev = 0.0
        steps.append({"stage": stage, **m, "drop_from_previous": drop_from_prev})
        prev = m
    return {"stages": list(JOURNEY_STAGES), "funnel": steps}
