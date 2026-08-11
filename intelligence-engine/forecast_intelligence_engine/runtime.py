"""FIE universe bootstrap runtime — drains forecast queue until coverage rises."""

from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

from forecast_intelligence_engine.composer import build_forecast
from forecast_intelligence_engine.models import ENGINE_CODE, VERSION

_LOCK = threading.Lock()
_THREAD: Optional[threading.Thread] = None
_STATE: dict[str, Any] = {
    "status": "idle",
    "started_at": None,
    "stopped": False,
    "last_tick": None,
    "last_error": None,
    "completed_this_session": 0,
    "failed_this_session": 0,
    "processed_this_session": 0,
    "started_mono": None,
}


def _role() -> str:
    return str(os.getenv("AGI_ROLE") or "local").strip().lower()


def _owned_here() -> bool:
    return _role() not in {"web", "http", "api"}


def _runtime_snapshot() -> dict[str, Any]:
    with _LOCK:
        snap = {k: v for k, v in _STATE.items() if k != "started_mono"}
    snap["process_role"] = _role()
    snap["owned_here"] = _owned_here()
    if not _owned_here():
        # A daemon thread cannot be observed across Render processes. Do not
        # misreport the web process's local idle state as the worker's state.
        snap["status"] = "external_worker"
    return snap


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truthy(name: str, default: str = "true") -> bool:
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def _paged(tab: str, *, max_rows: int = 20000) -> list[dict[str, Any]]:
    from institutional_warehouse import store

    out: list[dict[str, Any]] = []
    offset = 0
    page_size = 5000
    while offset < max_rows:
        try:
            page = store.fetch(tab, limit=page_size, offset=offset)
        except Exception:
            break
        rows = page.get("rows") or []
        if not rows:
            break
        out.extend(rows)
        total = int(page.get("total") or 0)
        offset += len(rows)
        if offset >= total or len(rows) < page_size:
            break
    return out


def _upsert_runtime(symbol: str, **fields: Any) -> None:
    from institutional_warehouse import gateway

    row = {"symbol": str(symbol).upper(), **fields, "updated_at": _now()}
    gateway.write(
        "forecast_runtime",
        [row],
        source=ENGINE_CODE,
        actor="fie_runtime",
        reason="fie_runtime_upsert",
    )


def sync_universe() -> dict[str, Any]:
    masters = _paged("company_master", max_rows=20000)
    existing = {str(r.get("symbol") or "").upper() for r in _paged("forecast_runtime", max_rows=20000)}
    created = 0
    for m in masters:
        sym = str(m.get("symbol") or "").strip().upper()
        if not sym or sym in existing:
            continue
        _upsert_runtime(
            sym,
            queue_status="PENDING",
            lifecycle="NOT_STARTED",
            sector=m.get("sector"),
            industry=m.get("industry"),
        )
        created += 1
    return {"ok": True, "universe": len(masters), "created": created}


def pipeline_counts() -> dict[str, int]:
    rows = _paged("forecast_runtime", max_rows=50000)
    company = _paged("forecast_company", max_rows=50000)
    complete_syms = {str(r.get("symbol") or "").upper() for r in company if r.get("status") == "PASS"}

    def _c(status: str) -> int:
        return sum(1 for r in rows if str(r.get("queue_status") or "").upper() == status)

    def _life(life: str) -> int:
        return sum(1 for r in rows if str(r.get("lifecycle") or "").upper() == life)

    return {
        "universe": len(rows) or len(company),
        "complete": len(complete_syms),
        "pending": _c("PENDING"),
        "running": _c("RUNNING"),
        "failed": _c("FAILED"),
        "waiting_hvie": _life("WAITING_HVIE"),
        "waiting_rie": _life("WAITING_RIE"),
        "waiting_statements": _life("WAITING_STATEMENTS"),
    }


def process_batch(*, batch: int = 3) -> dict[str, Any]:
    rows = [
        r for r in _paged("forecast_runtime", max_rows=50000)
        if str(r.get("queue_status") or "").upper() in {"PENDING", "RETRY"}
    ]
    rows.sort(key=lambda r: str(r.get("symbol") or ""))
    claimed = rows[: max(1, min(int(batch), 25))]
    completed = 0
    failed = 0
    results = []
    t0 = time.time()
    for r in claimed:
        sym = str(r.get("symbol") or "").upper()
        _upsert_runtime(sym, queue_status="RUNNING", lifecycle="RUNNING", last_run_at=_now())
        try:
            out = build_forecast(sym)
        except Exception as exc:
            out = {"ok": False, "symbol": sym, "error": str(exc)[:200]}
        results.append({"symbol": sym, "ok": out.get("ok"), "status": out.get("status"), "error": out.get("error")})
        if out.get("ok") and out.get("status") == "PASS":
            _upsert_runtime(sym, queue_status="COMPLETED", lifecycle="COMPLETE", last_error=None, completed_at=_now())
            completed += 1
        else:
            errors = (out.get("dqiv") or {}).get("errors") or []
            life = "FAILED"
            if "insufficient_statements" in errors:
                life = "WAITING_STATEMENTS"
            elif any("hvie" in str(e) for e in errors):
                life = "WAITING_HVIE"
            _upsert_runtime(
                sym,
                queue_status="FAILED" if life == "FAILED" else "SKIPPED",
                lifecycle=life,
                last_error=str(out.get("error") or errors[:3])[:280],
            )
            failed += 1
    elapsed = max(0.001, time.time() - t0)
    with _LOCK:
        _STATE["last_tick"] = _now()
        _STATE["completed_this_session"] += completed
        _STATE["failed_this_session"] += failed
        _STATE["processed_this_session"] += len(claimed)
    return {
        "ok": True,
        "attempted": len(claimed),
        "completed": completed,
        "failed": failed,
        "elapsed_seconds": round(elapsed, 2),
        "pipeline": pipeline_counts(),
        "results": results,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def board() -> dict[str, Any]:
    pipe = pipeline_counts()
    snap = _runtime_snapshot()
    universe = int(pipe.get("universe") or 0)
    complete = int(pipe.get("complete") or 0)
    pct = round(100.0 * complete / universe, 1) if universe else 0.0
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "runtime": snap,
        "progress": {
            "universe": universe,
            "complete": complete,
            "percent": pct,
            "pending": pipe.get("pending"),
            "running": pipe.get("running"),
            "failed": pipe.get("failed"),
            "waiting_hvie": pipe.get("waiting_hvie"),
            "waiting_rie": pipe.get("waiting_rie"),
            "waiting_statements": pipe.get("waiting_statements"),
        },
        "pipeline": pipe,
        "plain_english": (
            f"{complete} of {universe} companies have a stored forecast ({pct}%). "
            "Press Start to keep building explainable outlooks from warehouse + UVE/HVIE/VARIE/RIE."
            if universe
            else "No forecast queue yet. Press Start to load the universe."
        ),
        "what_this_does": (
            "Forecast Intelligence Engine builds evidence-based business, growth, profitability, "
            "valuation outlook and bull/base/bear scenarios. No target prices. No BUY/SELL. "
            "Never calls vendors."
        ),
    }


def status() -> dict[str, Any]:
    snap = _runtime_snapshot()
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "runtime": snap,
        "pipeline": pipeline_counts(),
    }


def start(*, interval_seconds: Optional[float] = None, batch: Optional[int] = None) -> dict[str, Any]:
    global _THREAD
    if not _owned_here():
        return {
            "ok": False,
            "enabled": False,
            "reason": "forecast_runtime_owned_by_gather_worker",
            "process_role": _role(),
        }
    if not _truthy("FIE_RUNTIME", "true"):
        return {"ok": True, "enabled": False, "reason": "FIE_RUNTIME=false"}
    if _THREAD and _THREAD.is_alive():
        return {"ok": True, "enabled": True, "already_running": True, "runtime": status().get("runtime")}

    interval = float(interval_seconds or os.getenv("FIE_INTERVAL_SECONDS") or 120)
    batch_n = int(batch or os.getenv("FIE_BATCH") or 3)

    def _loop() -> None:
        with _LOCK:
            _STATE["status"] = "running"
            _STATE["started_at"] = _now()
            _STATE["started_mono"] = time.time()
            _STATE["stopped"] = False
            _STATE["completed_this_session"] = 0
            _STATE["failed_this_session"] = 0
            _STATE["processed_this_session"] = 0
            _STATE["last_error"] = None
        try:
            sync_universe()
        except Exception as exc:
            with _LOCK:
                _STATE["last_error"] = f"sync_failed:{exc}"[:300]
        while True:
            with _LOCK:
                if _STATE.get("stopped"):
                    break
            try:
                process_batch(batch=batch_n)
            except Exception as exc:
                with _LOCK:
                    _STATE["last_error"] = str(exc)[:300]
            time.sleep(max(30.0, interval))
        with _LOCK:
            _STATE["status"] = "stopped"

    _THREAD = threading.Thread(target=_loop, name="fie-runtime", daemon=True)
    _THREAD.start()
    return {"ok": True, "enabled": True, "interval_seconds": interval, "batch": batch_n, "version": VERSION}


def stop() -> dict[str, Any]:
    with _LOCK:
        _STATE["stopped"] = True
        _STATE["status"] = "stopped"
    return {"ok": True, "stopped": True}


def resume() -> dict[str, Any]:
    sync_universe()
    return start()
