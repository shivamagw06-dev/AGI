"""Institutional Intelligence durable snapshot — HTTP reads only; worker aggregates.

Persists under $KIP_DATA_DIR/mission_control/institutional_intelligence.json

The admin page previously did Promise.all across 11 dashboard GETs on open.
The worker now soft-calls the same production facades and packages one snapshot.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Optional

from mission_control.snapshot import _now, _read_json, _write_json, store_root

II_VERSION = "institutional-intelligence-v1.0.0"

_LOCK = threading.RLock()
_WARM: dict[str, Any] | None = None
_META: dict[str, Any] = {
    "last_successful_at": None,
    "last_failure_at": None,
    "last_error": None,
    "last_trigger": None,
}
_JOB: dict[str, Any] = {
    "job_id": None,
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "trigger": None,
    "error": None,
}
_JOB_LOCK = threading.RLock()

# Keys match frontend state setters in InstitutionalIntelligence.jsx
BOARD_KEYS = (
    "health",
    "historical_depth",
    "sector",
    "macro",
    "decision_quality",
    "hall",
    "universe",
    "institutional_knowledge",
    "relationship",
    "alternative_data",
    "expectations",
)


def institutional_intelligence_path() -> Path:
    return store_root() / "institutional_intelligence.json"


def board_workers() -> int:
    try:
        return max(1, min(8, int(os.getenv("MC_II_BOARD_WORKERS") or "4")))
    except (TypeError, ValueError):
        return 4


def put_institutional_intelligence(payload: dict[str, Any], *, trigger: str = "manual") -> dict[str, Any]:
    global _WARM
    body = deepcopy(payload) if isinstance(payload, dict) else {}
    meta = {
        "persisted_at": _now(),
        "trigger": trigger,
        "path": str(institutional_intelligence_path()),
        "durable": bool((os.getenv("KIP_DATA_DIR") or "").strip()),
        "source": "precomputed",
        "delivery": "snapshot",
    }
    snap_meta = body.get("snapshot") if isinstance(body.get("snapshot"), dict) else {}
    body["snapshot"] = {**snap_meta, **meta}
    body["delivery"] = {"mode": "snapshot", "class": "institutional_intelligence"}
    body["status"] = "ready"
    _write_json(institutional_intelligence_path(), body)
    with _LOCK:
        _WARM = deepcopy(body)
        _META["last_successful_at"] = meta["persisted_at"]
        _META["last_trigger"] = trigger
        _META["last_error"] = None
    return meta


def get_institutional_intelligence() -> Optional[dict[str, Any]]:
    global _WARM
    with _LOCK:
        if isinstance(_WARM, dict) and (
            _WARM.get("boards") is not None or _WARM.get("status") == "ready"
        ):
            return deepcopy(_WARM)
    disk = _read_json(institutional_intelligence_path())
    if isinstance(disk, dict) and (disk.get("boards") is not None or disk.get("status") == "ready"):
        with _LOCK:
            _WARM = deepcopy(disk)
        return deepcopy(disk)
    return None


def job_status() -> dict[str, Any]:
    with _JOB_LOCK:
        return deepcopy(_JOB)


def _set_job(**kwargs: Any) -> None:
    with _JOB_LOCK:
        _JOB.update(kwargs)


def institutional_intelligence_meta() -> dict[str, Any]:
    snap = get_institutional_intelligence()
    with _LOCK:
        meta = deepcopy(_META)
    job = job_status()
    if not snap:
        return {
            "exists": False,
            "status": "warming" if job.get("status") in {"queued", "running"} else "missing",
            "job": job,
            **meta,
        }
    s = snap.get("snapshot") if isinstance(snap.get("snapshot"), dict) else {}
    return {
        "exists": True,
        "status": "ready",
        "persisted_at": s.get("persisted_at") or snap.get("generated_at"),
        "generated_at": snap.get("generated_at"),
        "trigger": s.get("trigger") or meta.get("last_trigger"),
        "durable": s.get("durable"),
        "path": s.get("path") or str(institutional_intelligence_path()),
        "job": job,
        **meta,
    }


def warming_payload(*, message: str | None = None) -> dict[str, Any]:
    meta = institutional_intelligence_meta()
    empty_boards = {k: None for k in BOARD_KEYS}
    return {
        "status": "warming",
        "snapshot": None,
        "message": message or "Institutional Intelligence is initializing.",
        "enabled": True,
        "read_only": True,
        "version": II_VERSION,
        "delivery": {"mode": "snapshot", "class": "warming"},
        "snapshot_meta": meta,
        "boards": empty_boards,
        "board_errors": {},
        "summary": {
            "boards_ok": 0,
            "boards_total": len(BOARD_KEYS),
            "headline": "Institutional Intelligence warming — snapshot not ready yet",
        },
        "generated_at": None,
        "_warming": True,
    }


def read_institutional_intelligence() -> dict[str, Any]:
    """HTTP-safe: return snapshot or warming. Never aggregates dashboards."""
    snap = get_institutional_intelligence()
    if snap:
        out = deepcopy(snap)
        out.setdefault("status", "ready")
        out["snapshot_meta"] = institutional_intelligence_meta()
        return out
    return warming_payload()


def _soft_call(name: str, fn: Callable[[], Any]) -> tuple[str, Any, str | None]:
    try:
        return name, fn(), None
    except Exception as exc:  # noqa: BLE001
        return name, None, str(exc)[:240]


def _board_callers() -> dict[str, Callable[[], Any]]:
    def _health():
        from knowledge_factory.coverage import daily_health_scorecard

        return daily_health_scorecard()

    def _hd():
        from knowledge_factory.production import historical_depth_coverage

        return historical_depth_coverage()

    def _sector():
        from knowledge_factory.production import sector_intelligence_coverage

        return sector_intelligence_coverage()

    def _macro():
        from knowledge_factory.production import macro_intelligence_coverage

        return macro_intelligence_coverage()

    def _dq():
        from decision_quality.production import dashboard

        return dashboard()

    def _hall():
        from decision_quality.production import hall

        return hall()

    def _universe():
        from universe_intelligence.production import dashboard

        return dashboard(universe_id="NIFTY_500")

    def _iks():
        from knowledge_factory.institutional_knowledge_stack.production import dashboard

        return dashboard(ensure=False)

    def _rel():
        from knowledge_factory.economic_relationship_intelligence.production import dashboard

        return dashboard()

    def _alt():
        from knowledge_factory.alternative_data_intelligence.production import dashboard

        return dashboard()

    def _exp():
        from knowledge_factory.market_expectations_intelligence.production import dashboard

        return dashboard()

    return {
        "health": _health,
        "historical_depth": _hd,
        "sector": _sector,
        "macro": _macro,
        "decision_quality": _dq,
        "hall": _hall,
        "universe": _universe,
        "institutional_knowledge": _iks,
        "relationship": _rel,
        "alternative_data": _alt,
        "expectations": _exp,
    }


def soft_gather_boards() -> tuple[dict[str, Any], dict[str, str]]:
    """Soft-call each dashboard facade with bounded concurrency. Worker-only."""
    callers = _board_callers()
    boards: dict[str, Any] = {k: None for k in BOARD_KEYS}
    errors: dict[str, str] = {}
    workers = min(board_workers(), len(callers))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_soft_call, name, fn): name for name, fn in callers.items()}
        for fut in as_completed(futs):
            name, body, err = fut.result()
            boards[name] = body
            if err:
                errors[name] = err
    return boards, errors


def _summarize(boards: dict[str, Any], errors: dict[str, str]) -> dict[str, Any]:
    ok = sum(1 for k in BOARD_KEYS if boards.get(k) is not None)
    return {
        "boards_ok": ok,
        "boards_total": len(BOARD_KEYS),
        "boards_failed": len(errors),
        "headline": f"{ok}/{len(BOARD_KEYS)} boards ready · {len(errors)} soft-failed",
    }


def build_and_persist_institutional_intelligence(*, trigger: str = "manual") -> dict[str, Any]:
    if os.getenv("PYTEST_CURRENT_TEST") and os.getenv("MC_ALLOW_LIVE_IN_PYTEST") != "1":
        boards = {
            "health": {"decision_coverage": {"soft_coverage_pct": 0.5}, "pytest_stub": True},
            "historical_depth": {"coverage_pct": 0.4, "pytest_stub": True},
            "sector": {"kpi": {}, "pytest_stub": True},
            "macro": {"kpi": {}, "pytest_stub": True},
            "decision_quality": {"kpi": {"score": 0.7}, "pytest_stub": True},
            "hall": {"hall_of_fame": [], "hall_of_shame": [], "pytest_stub": True},
            "universe": {
                "coverage": {},
                "ici_leaders": [],
                "pytest_stub": True,
            },
            "institutional_knowledge": {
                "summary": {
                    "stack_complete": False,
                    "reality_layers_ok": 3,
                    "expectation_layers_ok": 1,
                },
                "reality": {},
                "expectations": {},
                "pytest_stub": True,
            },
            "relationship": {
                "economic_relationship_coverage": {"relationships": 0, "commodities": 0},
                "pytest_stub": True,
            },
            "alternative_data": {
                "alternative_data_coverage": {"datasets": 0, "observations": 0},
                "pytest_stub": True,
            },
            "expectations": {
                "expectation_dashboard": {"surprises": 0, "narratives": 0},
                "pytest_stub": True,
            },
        }
        errors: dict[str, str] = {}
        body = {
            "enabled": True,
            "read_only": True,
            "version": II_VERSION,
            "generated_at": _now(),
            "boards": boards,
            "board_errors": errors,
            "summary": _summarize(boards, errors),
        }
        meta = put_institutional_intelligence(body, trigger=f"pytest:{trigger}")
        return {"ok": True, "trigger": trigger, "meta": meta, "pytest_stub": True}

    boards, errors = soft_gather_boards()
    body = {
        "enabled": True,
        "read_only": True,
        "version": II_VERSION,
        "generated_at": _now(),
        "boards": boards,
        "board_errors": errors,
        "summary": _summarize(boards, errors),
    }
    meta = put_institutional_intelligence(body, trigger=trigger)
    return {
        "ok": True,
        "trigger": trigger,
        "meta": meta,
        "generated_at": body.get("generated_at"),
        "summary": body.get("summary"),
    }


def enqueue_rebuild(*, trigger: str = "admin_rebuild", wait: bool = False) -> dict[str, Any]:
    with _JOB_LOCK:
        if _JOB.get("status") in {"queued", "running"}:
            already = True
            job_id = _JOB.get("job_id")
        else:
            already = False
            job_id = f"ii-snap-{uuid.uuid4().hex[:12]}"
            _JOB.update(
                {
                    "job_id": job_id,
                    "status": "queued",
                    "started_at": _now(),
                    "finished_at": None,
                    "trigger": trigger,
                    "error": None,
                }
            )

    if already:
        return {
            "ok": True,
            "status": "already_running",
            "job_id": job_id,
            "snapshot": institutional_intelligence_meta(),
            "message": "Institutional Intelligence rebuild already in progress; serving existing snapshot",
        }

    def _worker() -> None:
        _set_job(status="running")
        try:
            build_and_persist_institutional_intelligence(trigger=trigger)
            _set_job(status="completed", finished_at=_now(), error=None)
        except Exception as exc:  # noqa: BLE001
            with _LOCK:
                _META["last_failure_at"] = _now()
                _META["last_error"] = str(exc)[:240]
            _set_job(status="failed", finished_at=_now(), error=str(exc)[:240])

    if wait:
        _worker()
        return {
            "ok": True,
            "status": job_status().get("status"),
            "job_id": job_id,
            "snapshot": institutional_intelligence_meta(),
            "institutional_intelligence": get_institutional_intelligence() or warming_payload(),
        }

    threading.Thread(target=_worker, name=f"ii-snap-{job_id}", daemon=True).start()
    return {
        "ok": True,
        "status": "queued",
        "job_id": job_id,
        "snapshot": institutional_intelligence_meta(),
        "message": "Institutional Intelligence snapshot rebuild queued; existing snapshot continues to serve",
    }


def reset_for_tests() -> None:
    global _WARM
    for _ in range(50):
        with _JOB_LOCK:
            status = _JOB.get("status")
        if status not in {"queued", "running"}:
            break
        time.sleep(0.02)
    with _LOCK:
        _WARM = None
        _META.update(
            {
                "last_successful_at": None,
                "last_failure_at": None,
                "last_error": None,
                "last_trigger": None,
            }
        )
        path = institutional_intelligence_path()
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass
    _set_job(
        job_id=None,
        status="idle",
        started_at=None,
        finished_at=None,
        trigger=None,
        error=None,
    )
    with _LOCK:
        _WARM = None
