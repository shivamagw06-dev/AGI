"""Feature flags for Continuous Gather → Learn (Ask-safe)."""

from __future__ import annotations

import os


def _truthy(name: str, default: str = "false") -> bool:
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def is_enabled() -> bool:
    """Master switch — background loop + ops APIs."""
    return _truthy("CONTINUOUS_GATHER_LEARN", "true")


def morning_dag_enabled() -> bool:
    return is_enabled() and _truthy("CONTINUOUS_MORNING_DAG", "true")


def lidi_enabled() -> bool:
    return is_enabled() and _truthy("CONTINUOUS_LIDI", "true")


def kf_hd_enabled() -> bool:
    return is_enabled() and _truthy("CONTINUOUS_KF_HD", "true")


def faa_in_loop_enabled() -> bool:
    """Optional FAA refresh inside CGL post-market phase (independent of Ask)."""
    return is_enabled() and _truthy("CONTINUOUS_FAA_REFRESH", "true")


def learning_loop_enabled() -> bool:
    return is_enabled() and _truthy("CONTINUOUS_LEARNING_LOOP", "true")


def director_learning_inject() -> bool:
    return _truthy("CONTINUOUS_DIRECTOR_LEARNING", "true")


def historical_backfill_enabled() -> bool:
    return is_enabled() and _truthy("CONTINUOUS_HISTORICAL_BACKFILL", "true")


def backfill_until_complete_enabled() -> bool:
    return historical_backfill_enabled() and _truthy("CONTINUOUS_BACKFILL_UNTIL_COMPLETE", "true")


def interval_sec() -> float:
    """Adaptive interval: faster while historical backlog remains."""
    try:
        base = max(120.0, float(os.getenv("CONTINUOUS_GATHER_LEARN_INTERVAL_SEC") or "1800"))
    except ValueError:
        base = 1800.0
    if not backfill_until_complete_enabled():
        return base
    try:
        from knowledge_factory.historical_depth import queue as bf_queue

        state = bf_queue.load_engine_state()
        if state.get("maintenance_only"):
            return base
        stats = bf_queue.backlog_stats()
        if int(stats.get("remaining") or 0) > 0:
            try:
                fast = float(os.getenv("CONTINUOUS_BACKFILL_ACTIVE_INTERVAL_SEC") or "300")
            except ValueError:
                fast = 300.0
            return max(120.0, min(base, fast))
    except Exception:
        pass
    return base


def flags_dict() -> dict[str, bool | float]:
    return {
        "CONTINUOUS_GATHER_LEARN": is_enabled(),
        "CONTINUOUS_MORNING_DAG": morning_dag_enabled(),
        "CONTINUOUS_LIDI": lidi_enabled(),
        "CONTINUOUS_KF_HD": kf_hd_enabled(),
        "CONTINUOUS_FAA_REFRESH": faa_in_loop_enabled(),
        "CONTINUOUS_LEARNING_LOOP": learning_loop_enabled(),
        "CONTINUOUS_DIRECTOR_LEARNING": director_learning_inject(),
        "CONTINUOUS_HISTORICAL_BACKFILL": historical_backfill_enabled(),
        "CONTINUOUS_BACKFILL_UNTIL_COMPLETE": backfill_until_complete_enabled(),
        "CONTINUOUS_GATHER_LEARN_INTERVAL_SEC": interval_sec(),
        "FAA_BACKGROUND_COLLECTOR": _truthy("FAA_BACKGROUND_COLLECTOR", "false"),
        "KF_HD_LIVE_COLLECTORS": _truthy("KF_HD_LIVE_COLLECTORS", "false"),
    }
