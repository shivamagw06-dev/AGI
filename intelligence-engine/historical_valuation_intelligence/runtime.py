"""HVIE Continuous Runtime — self-maintaining historical valuation service.

Bootstrap once per company → daily append → quarterly forward rebuild →
corporate-action rebuild → weekly stats → monthly health. Never a full
recompute of immutable history unless a corporate action requires it.
"""

from __future__ import annotations

import os
import threading
import time
from datetime import date, datetime, timezone
from typing import Any, Optional

from historical_valuation_intelligence import compute, persist
from historical_valuation_intelligence.models import ENGINE_CODE, VERSION
from historical_valuation_intelligence.research_triggers import emit_research_events

_STATE_LOCK = threading.Lock()
_RUNTIME = {
    "status": "idle",  # idle | running | stopped
    "mode": None,  # bootstrap | daily | weekly | monthly | forward | ca
    "started_at": None,
    "stopped": False,
    "last_tick": None,
    "last_error": None,
    "counters": {
        "bootstrap_done": 0,
        "bootstrap_failed": 0,
        "daily_appended": 0,
        "forward_rebuilds": 0,
        "ca_rebuilds": 0,
        "stats_refreshed": 0,
        "research_events": 0,
    },
}
_THREAD: Optional[threading.Thread] = None


def _truthy(name: str, default: str = "false") -> bool:
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return date.today().isoformat()


def _upsert_state(symbol: str, **fields: Any) -> None:
    from institutional_warehouse import gateway, store

    ticker = str(symbol).upper()
    existing = None
    try:
        rows = store.fetch("hvie_company_state", filters={"symbol": ticker}, limit=1).get("rows") or []
        existing = rows[0] if rows else None
    except Exception:
        existing = None
    row = {"symbol": ticker, **(existing or {}), **fields}
    # Drop warehouse system keys that must not be re-written blindly.
    for k in list(row.keys()):
        if str(k).startswith("sys_") or k in {"row_id", "_meta"}:
            row.pop(k, None)
    gateway.write(
        "hvie_company_state", [row], source=ENGINE_CODE, actor="hvie_runtime",
        reason="hvie_state_upsert",
    )


def _get_state(symbol: str) -> dict[str, Any]:
    from institutional_warehouse import store

    ticker = str(symbol).upper()
    try:
        rows = store.fetch("hvie_company_state", filters={"symbol": ticker}, limit=1).get("rows") or []
        return rows[0] if rows else {}
    except Exception:
        return {}


def _universe() -> list[str]:
    from institutional_warehouse import store

    rows = store.all_rows("company_master", limit=6000) or []
    out = []
    for r in rows:
        sym = str(r.get("symbol") or "").strip().upper()
        if sym:
            out.append(sym)
    return out


def _policy_metric(symbol: str) -> tuple[str, Optional[str]]:
    try:
        from valuation_policy import evaluate

        policy = evaluate(symbol) or {}
        if policy.get("ok"):
            return (
                str(policy.get("primary_metric") or "pe"),
                str(policy.get("primary_model") or ""),
            )
    except Exception:
        pass
    return "pe", None


def bootstrap_company(symbol: str, *, cadence: str = "monthly") -> dict[str, Any]:
    """One-time full history seed. Never rebuild again once SEEDED."""
    ticker = str(symbol or "").strip().upper()
    state = _get_state(ticker)
    if state.get("seeded") or str(state.get("status") or "").upper() == "SEEDED":
        return {
            "ok": True,
            "symbol": ticker,
            "action": "skip",
            "reason": "already_seeded",
            "observations": state.get("observations"),
        }

    _upsert_state(ticker, status="BOOTSTRAPPING", error=None)
    primary_metric, primary_model = _policy_metric(ticker)
    result = compute.reconstruct(
        ticker, cadence=cadence, limit_observations=8000, actor="hvie_bootstrap",
    )
    if not result.get("ok"):
        _upsert_state(
            ticker,
            status="FAILED",
            seeded=False,
            error=str(result.get("error") or "bootstrap_failed")[:280],
            primary_metric=primary_metric,
            primary_model=primary_model,
        )
        with _STATE_LOCK:
            _RUNTIME["counters"]["bootstrap_failed"] += 1
        return result

    _upsert_state(
        ticker,
        status="SEEDED",
        seeded=True,
        bootstrap_at=_now(),
        last_observation_date=result.get("last"),
        first_observation=result.get("first"),
        observations=result.get("observations") or 0,
        primary_metric=primary_metric,
        primary_model=primary_model,
        error=None,
    )
    with _STATE_LOCK:
        _RUNTIME["counters"]["bootstrap_done"] += 1
    return {**result, "action": "bootstrap", "status": "SEEDED"}


def run_bootstrap_slice(*, batch: int = 20, cadence: str = "monthly") -> dict[str, Any]:
    """Seed the next unseeded companies (resumable)."""
    from institutional_warehouse import store

    batch = max(1, min(int(batch), 100))
    seeded = set()
    try:
        for r in store.all_rows("hvie_company_state", limit=6000) or []:
            if r.get("seeded") or str(r.get("status") or "").upper() == "SEEDED":
                seeded.add(str(r.get("symbol") or "").upper())
    except Exception:
        seeded = set()

    pending = [s for s in _universe() if s not in seeded][:batch]
    results = [bootstrap_company(s, cadence=cadence) for s in pending]
    ok = sum(1 for r in results if r.get("ok"))
    return {
        "ok": True,
        "mode": "bootstrap",
        "attempted": len(results),
        "succeeded": ok,
        "failed": len(results) - ok,
        "pending_remaining": max(0, len(_universe()) - len(seeded) - ok),
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def daily_append_company(symbol: str) -> dict[str, Any]:
    """Append today's observation only — no historical recomputation."""
    ticker = str(symbol or "").strip().upper()
    state = _get_state(ticker)
    if not (state.get("seeded") or str(state.get("status") or "").upper() in {"SEEDED", "DAILY"}):
        # Auto-bootstrap thin names so daily runtime remains self-maintaining.
        boot = bootstrap_company(ticker, cadence="monthly")
        if not boot.get("ok") and boot.get("action") != "skip":
            return {**boot, "mode": "daily", "bootstrap_attempted": True}

    prev_regime = state.get("last_regime")
    prev_pct = state.get("last_percentile")
    result = compute.incremental_price_update(ticker, actor="hvie_daily")
    primary_metric = state.get("primary_metric") or _policy_metric(ticker)[0]

    # Refresh signal fields + research triggers from current pack.
    research_n = 0
    try:
        from historical_valuation_intelligence.engine import company_pack

        pack = company_pack(ticker, metric=primary_metric, window="max")
        if pack.get("ok"):
            events = emit_research_events(
                ticker,
                metric=primary_metric,
                current_percentile=pack.get("historical_percentile"),
                previous_regime=prev_regime,
                current_regime=pack.get("regime"),
                current_value=pack.get("current"),
                median=pack.get("median"),
            )
            research_n = len(events)
            _upsert_state(
                ticker,
                status="DAILY",
                last_daily_at=_now(),
                last_observation_date=(pack.get("coverage") or {}).get("last") or _today(),
                last_regime=pack.get("regime"),
                last_percentile=pack.get("historical_percentile"),
                observations=(pack.get("coverage") or {}).get("observation_count") or state.get("observations"),
                error=None if result.get("ok") else str(result.get("error") or "")[:280],
            )
    except Exception as exc:
        _upsert_state(ticker, status="DAILY", last_daily_at=_now(), error=str(exc)[:280])

    with _STATE_LOCK:
        _RUNTIME["counters"]["daily_appended"] += 1
        _RUNTIME["counters"]["research_events"] += research_n
    return {
        **result,
        "mode": "daily",
        "research_events": research_n,
        "previous_percentile": prev_pct,
    }


def run_daily_append(*, batch: int = 80) -> dict[str, Any]:
    """Append for a batch of seeded companies (Node 18:30 tick / gather loop)."""
    from institutional_warehouse import store

    batch = max(1, min(int(batch), 400))
    seeded = []
    try:
        for r in store.all_rows("hvie_company_state", limit=6000) or []:
            if r.get("seeded") or str(r.get("status") or "").upper() in {"SEEDED", "DAILY"}:
                seeded.append(str(r.get("symbol") or "").upper())
    except Exception:
        seeded = []
    if not seeded:
        # Nothing seeded yet — bootstrap a small slice instead.
        return run_bootstrap_slice(batch=min(batch, 25))

    # Round-robin: prefer names whose last_daily_at is oldest / missing.
    states = {str(r.get("symbol") or "").upper(): r
              for r in (store.all_rows("hvie_company_state", limit=6000) or [])}
    seeded.sort(key=lambda s: str((states.get(s) or {}).get("last_daily_at") or ""))
    targets = seeded[:batch]
    results = [daily_append_company(s) for s in targets]
    ok = sum(1 for r in results if r.get("ok") or r.get("action") == "skip")
    return {
        "ok": True,
        "mode": "daily",
        "attempted": len(results),
        "succeeded": ok,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def forward_rebuild_company(
    symbol: str,
    release_date: Optional[str] = None,
    *,
    as_of: Optional[str] = None,
) -> dict[str, Any]:
    """Quarterly/annual: rebuild only from statement release date → today."""
    ticker = str(symbol or "").strip().upper()
    start = release_date or as_of
    if hasattr(start, "isoformat"):
        start = start.isoformat()
    _upsert_state(ticker, status="FORWARD_REBUILD")
    result = compute.recalculate_from_statement(
        ticker, release_date=start, actor="hvie_forward",
    )
    _upsert_state(
        ticker,
        status="SEEDED",
        seeded=True,
        last_forward_at=_now(),
        last_observation_date=result.get("last") or _today(),
        observations=result.get("observations") or _get_state(ticker).get("observations"),
        error=None if result.get("ok") else str(result.get("error") or "")[:280],
    )
    with _STATE_LOCK:
        _RUNTIME["counters"]["forward_rebuilds"] += 1
    return {**result, "mode": "forward"}


def corporate_action_rebuild(symbol: str) -> dict[str, Any]:
    """CA path: full reconstruct (share count / adjusted price chain changed)."""
    ticker = str(symbol or "").strip().upper()
    _upsert_state(ticker, status="CA_REBUILD", seeded=False)
    result = compute.reconstruct(
        ticker, cadence="daily", limit_observations=8000, actor="hvie_ca",
    )
    _upsert_state(
        ticker,
        status="SEEDED" if result.get("ok") else "FAILED",
        seeded=bool(result.get("ok")),
        bootstrap_at=_now() if result.get("ok") else _get_state(ticker).get("bootstrap_at"),
        last_ca_at=_now(),
        last_observation_date=result.get("last"),
        first_observation=result.get("first"),
        observations=result.get("observations") or 0,
        error=None if result.get("ok") else str(result.get("error") or "")[:280],
    )
    with _STATE_LOCK:
        _RUNTIME["counters"]["ca_rebuilds"] += 1
    return {**result, "mode": "corporate_action"}


def run_weekly_stats(*, batch: int = 40) -> dict[str, Any]:
    """Persist percentiles/bands/regimes (+ sector medians)."""
    from institutional_warehouse import store

    seeded = []
    for r in store.all_rows("hvie_company_state", limit=6000) or []:
        if r.get("seeded"):
            seeded.append(str(r.get("symbol") or "").upper())
    seeded.sort(key=lambda s: str((_get_state(s) or {}).get("last_stats_at") or ""))
    targets = seeded[: max(1, min(int(batch), 200))]
    done = 0
    for sym in targets:
        persist.persist_company_statistics(sym)
        _upsert_state(sym, last_stats_at=_now(), status="SEEDED")
        done += 1
        with _STATE_LOCK:
            _RUNTIME["counters"]["stats_refreshed"] += 1
    # Persist primary metrics used by MSI sector lenses (not PE alone).
    sector_packs = {}
    for metric in ("pe", "pb", "ev_ebitda"):
        try:
            sector_packs[metric] = persist.persist_sector_medians(metric=metric)
        except Exception as exc:  # noqa: BLE001
            sector_packs[metric] = {"ok": False, "error": str(exc)[:160]}
    return {
        "ok": True,
        "mode": "weekly",
        "companies": done,
        "sector_medians": sector_packs.get("pe"),
        "sector_medians_by_metric": sector_packs,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def run_monthly_health() -> dict[str, Any]:
    """Coverage / missing / DQIV repair scan."""
    from institutional_warehouse import store

    states = store.all_rows("hvie_company_state", limit=6000) or []
    universe = _universe()
    seeded = [r for r in states if r.get("seeded")]
    failed = [r for r in states if str(r.get("status") or "").upper() == "FAILED"]
    missing_obs = [r for r in seeded if int(r.get("observations") or 0) < 6]
    # Repair: re-bootstrap failed / thin names (small batch).
    repaired = 0
    for r in (failed + missing_obs)[:25]:
        sym = str(r.get("symbol") or "").upper()
        if not sym:
            continue
        _upsert_state(sym, seeded=False, status="PENDING", error=None)
        out = bootstrap_company(sym, cadence="monthly")
        if out.get("ok"):
            repaired += 1
    return {
        "ok": True,
        "mode": "monthly",
        "universe": len(universe),
        "seeded": len(seeded),
        "failed": len(failed),
        "thin_history": len(missing_obs),
        "repaired": repaired,
        "coverage_pct": round(100.0 * len(seeded) / len(universe), 1) if universe else 0.0,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def coverage_dashboard(*, limit: int = 200) -> dict[str, Any]:
    """Per-company coverage board for admin / UI."""
    from institutional_warehouse import store

    states = store.all_rows("hvie_company_state", limit=6000) or []
    states = sorted(states, key=lambda r: str(r.get("symbol") or ""))[: max(1, min(int(limit), 2000))]
    rows = []
    for r in states:
        rows.append({
            "symbol": r.get("symbol"),
            "status": r.get("status"),
            "seeded": bool(r.get("seeded")),
            "price_history": f"{r.get('first_observation') or '—'} → {r.get('last_observation_date') or '—'}",
            "pe_history": f"{r.get('first_observation') or '—'} → {r.get('last_observation_date') or '—'}"
            if (r.get("primary_metric") or "pe") == "pe" else "policy_primary",
            "primary_metric": r.get("primary_metric"),
            "primary_model": r.get("primary_model"),
            "observations": r.get("observations"),
            "regime": r.get("last_regime"),
            "percentile": r.get("last_percentile"),
            "last_daily_at": r.get("last_daily_at"),
            "confidence": "HIGH" if int(r.get("observations") or 0) >= 60 else (
                "MEDIUM" if int(r.get("observations") or 0) >= 24 else "LOW"
            ),
        })
    universe = len(_universe())
    seeded_n = sum(1 for r in (store.all_rows("hvie_company_state", limit=6000) or []) if r.get("seeded"))
    return {
        "ok": True,
        "universe": universe,
        "seeded": seeded_n,
        "coverage_pct": round(100.0 * seeded_n / universe, 1) if universe else 0.0,
        "rows": rows,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def status() -> dict[str, Any]:
    with _STATE_LOCK:
        snap = {**_RUNTIME, "counters": dict(_RUNTIME["counters"])}
    dash = coverage_dashboard(limit=5)
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "runtime": snap,
        "coverage_pct": dash.get("coverage_pct"),
        "universe": dash.get("universe"),
        "seeded": dash.get("seeded"),
        "schedules": {
            "daily": "18:30 IST weekdays — append today's observation",
            "bootstrap": "continuous gather-worker slice until universe seeded",
            "weekly": "Sunday — persist statistics + sector medians",
            "monthly": "1st — health / repair",
            "quarterly": "on statement ingest — forward rebuild",
            "corporate_action": "on CA ingest — full reconstruct",
        },
    }


def run_once(mode: str = "auto", **kwargs: Any) -> dict[str, Any]:
    """Execute one runtime slice. Used by Node tick + gather loop + admin."""
    mode = str(mode or "auto").lower()
    with _STATE_LOCK:
        _RUNTIME["last_tick"] = _now()
        _RUNTIME["mode"] = mode
        _RUNTIME["status"] = "running"

    try:
        if mode == "bootstrap":
            out = run_bootstrap_slice(batch=int(kwargs.get("batch") or 20))
        elif mode == "daily":
            out = run_daily_append(batch=int(kwargs.get("batch") or 80))
        elif mode == "weekly":
            out = run_weekly_stats(batch=int(kwargs.get("batch") or 40))
        elif mode == "monthly":
            out = run_monthly_health()
        elif mode == "forward":
            out = forward_rebuild_company(
                str(kwargs.get("symbol") or ""),
                release_date=kwargs.get("release_date"),
            )
        elif mode in {"ca", "corporate_action"}:
            out = corporate_action_rebuild(str(kwargs.get("symbol") or ""))
        elif mode in {"universe", "universe_bootstrap", "completion"}:
            from historical_valuation_intelligence.universe_programme import runtime as univ

            out = univ.process_batch(batch=int(kwargs.get("batch") or 15))
        elif mode == "auto":
            # Prefer finishing the persisted universe queue; else daily maintenance.
            from historical_valuation_intelligence.universe_programme import runtime as univ
            from historical_valuation_intelligence.universe_programme import queue as univ_queue

            try:
                univ_queue.sync_universe()
                pipe = univ_queue.pipeline_counts()
                remaining = (
                    int(pipe.get("pending") or 0)
                    + int(pipe.get("retry") or 0)
                    + int(pipe.get("running") or 0)
                )
            except Exception:
                remaining = -1
            if remaining != 0:
                out = univ.process_batch(batch=int(kwargs.get("batch") or 15))
            else:
                out = run_daily_append(batch=int(kwargs.get("batch") or 80))
        else:
            out = {"ok": False, "error": f"unknown_mode:{mode}"}
        return out
    except Exception as exc:
        with _STATE_LOCK:
            _RUNTIME["last_error"] = str(exc)[:300]
        return {"ok": False, "error": str(exc)[:300], "mode": mode}
    finally:
        with _STATE_LOCK:
            if not _RUNTIME.get("stopped"):
                _RUNTIME["status"] = "idle"


def start_loop(*, interval_seconds: Optional[float] = None) -> dict[str, Any]:
    """Background loop for gather_worker — drains universe queue + light daily."""
    global _THREAD
    if not _truthy("HVIE_RUNTIME", "true"):
        return {"ok": True, "enabled": False, "reason": "HVIE_RUNTIME=false"}
    # Also start the dedicated universe completion runtime (persisted queue).
    universe_start = None
    try:
        from historical_valuation_intelligence.universe_programme import runtime as univ

        universe_start = univ.start(interval_seconds=interval_seconds)
    except Exception as exc:
        universe_start = {"ok": False, "error": str(exc)[:200]}

    if _THREAD and _THREAD.is_alive():
        return {
            "ok": True,
            "enabled": True,
            "already_running": True,
            "universe_programme": universe_start,
        }

    interval = float(interval_seconds or os.getenv("HVIE_RUNTIME_INTERVAL_SECONDS") or 120)

    def _loop() -> None:
        with _STATE_LOCK:
            _RUNTIME["status"] = "running"
            _RUNTIME["started_at"] = _now()
            _RUNTIME["stopped"] = False
        while True:
            with _STATE_LOCK:
                if _RUNTIME.get("stopped"):
                    break
            run_once("auto", batch=int(os.getenv("HVIE_RUNTIME_BATCH") or 15))
            time.sleep(max(15.0, interval))
        with _STATE_LOCK:
            _RUNTIME["status"] = "stopped"

    _THREAD = threading.Thread(target=_loop, name="hvie-runtime", daemon=True)
    _THREAD.start()
    return {
        "ok": True,
        "enabled": True,
        "interval_seconds": interval,
        "engine": ENGINE_CODE,
        "universe_programme": universe_start,
    }


def stop_loop() -> dict[str, Any]:
    with _STATE_LOCK:
        _RUNTIME["stopped"] = True
        _RUNTIME["status"] = "stopped"
    universe_stop = None
    try:
        from historical_valuation_intelligence.universe_programme import runtime as univ

        universe_stop = univ.stop()
    except Exception as exc:
        universe_stop = {"ok": False, "error": str(exc)[:200]}
    return {"ok": True, "stopped": True, "universe_programme": universe_stop}
