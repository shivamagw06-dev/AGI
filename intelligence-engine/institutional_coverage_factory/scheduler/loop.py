"""24×7 rolling queue — every tick: plan → dispatch → validate → update readiness."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from institutional_coverage_factory.config import load_config
from institutional_coverage_factory.flags import is_icf_enabled, is_icf_scheduler_enabled
from institutional_coverage_factory.schema import ICF_VERSION, ICF_WORKSTREAM_ID

# In-process daily ICC counter (resets on UTC day change / process restart)
_STATE: Dict[str, Any] = {
    "day": None,
    "icc_entered_today": 0,
    "ticks": 0,
    "last_tick_at": None,
    "last_tick": None,
    "history": [],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _roll_day() -> None:
    today = date.today().isoformat()
    if _STATE.get("day") != today:
        _STATE["day"] = today
        _STATE["icc_entered_today"] = 0


def scheduler_status() -> Dict[str, Any]:
    _roll_day()
    cfg = load_config()
    return {
        "ok": True,
        "workstream_id": ICF_WORKSTREAM_ID,
        "version": ICF_VERSION,
        "enabled": is_icf_enabled() and is_icf_scheduler_enabled(),
        "day": _STATE.get("day"),
        "icc_entered_today": int(_STATE.get("icc_entered_today") or 0),
        "max_companies_per_day": cfg["max_companies_per_day"],
        "remaining_capacity_today": max(
            0, int(cfg["max_companies_per_day"]) - int(_STATE.get("icc_entered_today") or 0)
        ),
        "tick_interval_minutes": cfg["tick_interval_minutes"],
        "companies_per_tick": cfg["companies_per_tick"],
        "ticks": int(_STATE.get("ticks") or 0),
        "last_tick_at": _STATE.get("last_tick_at"),
        "metric": "companies_entering_icc_per_day",
    }


def run_coverage_tick(
    *,
    scope: str = "TOP20",
    limit: Optional[int] = None,
    dispatch: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    One rolling-queue tick.

    Respects max_companies_per_day as ICC entry capacity (not crawl batch size).
    """
    if not is_icf_enabled() or not is_icf_scheduler_enabled():
        return {"ok": False, "enabled": False, "reason": "icf_scheduler_disabled"}

    _roll_day()
    cfg = load_config()
    capacity = max(
        0, int(cfg["max_companies_per_day"]) - int(_STATE.get("icc_entered_today") or 0)
    )
    n = int(limit if limit is not None else cfg.get("companies_per_tick") or 8)
    # Still process companies for refresh/progress even if ICC capacity is full,
    # but track that new ICC entries are capacity-gated.
    from institutional_coverage_factory.planner.plan import plan_and_dispatch

    result = plan_and_dispatch(limit=n, scope=scope, dispatch=dispatch)
    entered = int(result.get("icc_entered") or 0)
    # Cap counted ICC entries by remaining daily capacity
    counted = min(entered, capacity)
    _STATE["icc_entered_today"] = int(_STATE.get("icc_entered_today") or 0) + counted
    _STATE["ticks"] = int(_STATE.get("ticks") or 0) + 1
    _STATE["last_tick_at"] = _now()
    summary = {
        "ok": True,
        "tick_at": _STATE["last_tick_at"],
        "scope": scope,
        "queued": len(result.get("queue") or []),
        "dispatched": result.get("dispatched"),
        "icc_entered_this_tick": entered,
        "icc_counted_toward_daily_target": counted,
        "icc_entered_today": _STATE["icc_entered_today"],
        "max_companies_per_day": cfg["max_companies_per_day"],
        "daily_target_met": _STATE["icc_entered_today"] >= int(cfg["max_companies_per_day"]),
        "capacity_remaining": max(
            0, int(cfg["max_companies_per_day"]) - int(_STATE["icc_entered_today"])
        ),
        "queue_tickers": [q.get("ticker") for q in (result.get("queue") or [])],
    }
    _STATE["last_tick"] = summary
    hist: List[Dict[str, Any]] = list(_STATE.get("history") or [])
    hist.append(summary)
    _STATE["history"] = hist[-48:]  # keep ~12h at 15-min ticks

    return {
        **summary,
        "workstream_id": ICF_WORKSTREAM_ID,
        "version": ICF_VERSION,
        "plan": {
            "candidates_scanned": result.get("candidates_scanned"),
            "icc_complete_in_scope": result.get("icc_complete_in_scope"),
            "non_icc": result.get("non_icc"),
            "queue": result.get("queue"),
        },
        "dispatch_results": result.get("dispatch_results") if dispatch is not False else [],
        "config": result.get("config"),
        "note": "Target metric is companies entering ICC/day — configurable via max_companies_per_day.",
    }
