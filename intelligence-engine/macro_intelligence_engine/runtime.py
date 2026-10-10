"""MIE runtime — refresh macro packs on cadence (daily/weekly/monthly/quarterly/event)."""

from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

from macro_intelligence_engine.composer import build_macro_pack
from macro_intelligence_engine.snapshot import save as save_snapshot
from macro_intelligence_engine.models import DEFAULT_COUNTRY, ENGINE_CODE, VERSION

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
    "last_mode": None,
    "started_mono": None,
    "last_public_data_run": None,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truthy(name: str, default: str = "true") -> bool:
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def _upsert_runtime(country: str, **fields: Any) -> None:
    try:
        from institutional_warehouse import gateway

        row = {"country": country, **fields, "updated_at": _now()}
        gateway.write(
            "macro_runtime",
            [row],
            source=ENGINE_CODE,
            actor="mie_runtime",
            reason="mie_runtime_upsert",
        )
    except Exception:
        pass


def run_refresh(*, mode: str = "daily", country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    """Compose and persist one country macro pack. Modes are labels for ops cadence."""
    ctry = (country or DEFAULT_COUNTRY).strip() or DEFAULT_COUNTRY
    mode_norm = (mode or "daily").strip().lower()
    _upsert_runtime(ctry, queue_status="RUNNING", lifecycle="REFRESHING", last_run_at=_now())
    t0 = time.perf_counter()
    try:
        public_data = None
        if ctry.lower() == DEFAULT_COUNTRY.lower() and _truthy("MIE_PUBLIC_DATA_ENABLED", "true"):
            last = _STATE.get("last_public_data_run")
            due = (
                mode_norm == "public_data"
                or not last
                or (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds() >= 86400
            )
            if due:
                try:
                    from macro_intelligence_engine.public_ingestion import run_public_ingestion
                    public_data = run_public_ingestion()
                except Exception as exc:
                    # Public-source collection must never prevent the existing
                    # macro pack from refreshing. Its receipt remains explicit.
                    public_data = {"ok": False, "error": str(exc)[:240]}
                with _LOCK:
                    _STATE["last_public_data_run"] = _now()
        pack = build_macro_pack(ctry)
        ok = bool(pack.get("ok"))
        # Publishing is part of the asynchronous runtime.  The web route reads
        # this output and must never rebuild a pack for a visitor.
        if ok:
            published = save_snapshot(pack, country=ctry)
            if not published.get("ok"):
                raise RuntimeError(
                    f"macro_snapshot_publish_failed:{(published.get('web_engine_publish') or {}).get('error') or 'unknown'}"
                )
        _upsert_runtime(
            ctry,
            queue_status="COMPLETE" if ok else "FAILED",
            lifecycle="READY" if ok else "NEEDS_RETRY",
            macro_confidence=(pack.get("macro_quality") or {}).get("macro_confidence"),
            last_run_at=_now(),
            completed_at=_now() if ok else None,
            last_error=None if ok else str((pack.get("dqiv") or {}).get("errors") or pack.get("error") or "")[:280],
            last_mode=mode_norm,
        )
        with _LOCK:
            _STATE["processed_this_session"] += 1
            if ok:
                _STATE["completed_this_session"] += 1
            else:
                _STATE["failed_this_session"] += 1
            _STATE["last_mode"] = mode_norm
            _STATE["last_tick"] = _now()
        return {
            "ok": ok,
            "mode": mode_norm,
            "country": ctry,
            "status": pack.get("status"),
            "regime": pack.get("regime"),
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            "engine": ENGINE_CODE,
            "version": VERSION,
            "public_data": public_data,
        }
    except Exception as exc:
        with _LOCK:
            _STATE["failed_this_session"] += 1
            _STATE["last_error"] = str(exc)[:280]
            _STATE["last_tick"] = _now()
        _upsert_runtime(ctry, queue_status="FAILED", lifecycle="NEEDS_RETRY", last_error=str(exc)[:280])
        return {"ok": False, "error": str(exc)[:280], "mode": mode_norm, "country": ctry}


def process_batch(*, batch: int = 1, mode: str = "daily") -> dict[str, Any]:
    # Country-level engine: batch maps to repeated refresh / multi-country later.
    countries = [DEFAULT_COUNTRY]
    # Optional second pass for Global if requested via env
    if _truthy("MIE_INCLUDE_GLOBAL", "false"):
        countries.append("Global")
    results = []
    for ctry in countries[: max(int(batch), 1)]:
        results.append(run_refresh(mode=mode, country=ctry))
    return {
        "ok": all(r.get("ok") for r in results) if results else False,
        "results": results,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def _loop() -> None:
    global _THREAD
    interval = max(30, int(os.getenv("MIE_RUNTIME_INTERVAL_SEC", "300")))
    mode = os.getenv("MIE_RUNTIME_MODE", "daily")
    while True:
        with _LOCK:
            if _STATE["stopped"]:
                _STATE["status"] = "idle"
                break
            _STATE["status"] = "running"
            _STATE["last_tick"] = _now()
        try:
            # When Global is explicitly enabled, publish both the India
            # read-through and global snapshot in this worker cycle.
            process_batch(batch=2 if _truthy("MIE_INCLUDE_GLOBAL", "false") else 1, mode=mode)
        except Exception as exc:
            with _LOCK:
                _STATE["last_error"] = str(exc)[:280]
        time.sleep(interval)
    with _LOCK:
        _STATE["status"] = "idle"
        _THREAD = None


def start() -> dict[str, Any]:
    global _THREAD
    with _LOCK:
        if _STATE["status"] == "running" and _THREAD and _THREAD.is_alive():
            return {"ok": True, "already_running": True, "status": status()}
        _STATE.update({
            "status": "running",
            "started_at": _now(),
            "stopped": False,
            "last_error": None,
            "completed_this_session": 0,
            "failed_this_session": 0,
            "processed_this_session": 0,
            "started_mono": time.monotonic(),
        })
        _THREAD = threading.Thread(target=_loop, name="mie-runtime", daemon=True)
        _THREAD.start()
    return {"ok": True, "started": True, "status": status()}


def stop() -> dict[str, Any]:
    with _LOCK:
        _STATE["stopped"] = True
        _STATE["status"] = "stopping"
    return {"ok": True, "stopping": True, "status": status()}


def resume() -> dict[str, Any]:
    return start()


def status() -> dict[str, Any]:
    with _LOCK:
        st = dict(_STATE)
    return {
        "ok": True,
        "runtime": st,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def board() -> dict[str, Any]:
    st = status()
    runtime = st.get("runtime") or {}
    # Best-effort warehouse counts
    complete = 0
    failed = 0
    pending = 0
    try:
        from institutional_warehouse import store

        page = store.fetch("macro_runtime", limit=200)
        rows = page.get("rows") or []
        for r in rows:
            qs = str(r.get("queue_status") or "").upper()
            if qs == "COMPLETE":
                complete += 1
            elif qs == "FAILED":
                failed += 1
            else:
                pending += 1
    except Exception:
        rows = []
    progress = {
        "universe": max(complete + failed + pending, 1),
        "complete": complete,
        "failed": failed,
        "pending": pending,
        "percent": round(100.0 * complete / max(complete + failed + pending, 1), 1),
    }
    return {
        "ok": True,
        "runtime": runtime,
        "progress": progress,
        "plain_english": (
            f"MIE runtime is {runtime.get('status', 'idle')}. "
            f"Last mode {runtime.get('last_mode') or '—'}. "
            f"Completed this session: {runtime.get('completed_this_session', 0)}."
        ),
        "what_this_does": (
            "Refreshes explainable India macro regime, sector/industry impact, scenarios and risks "
            "from warehouse + CMKP/HMIP/MRI/HMAI/MFI. No vendor calls at compose time. No BUY/SELL."
        ),
        "cadence": {
            "daily": "FX, commodities, yields, liquidity",
            "weekly": "slower indicators + relationships",
            "monthly": "CPI, IIP, PMI, credit, fiscal",
            "quarterly": "GDP, sector impact, macro forecasts",
            "event": "RBI / Budget / major CB / geopolitics",
        },
        "engine": ENGINE_CODE,
        "version": VERSION,
    }
