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
    "outcome_cursor": 0,
    "outcomes_evaluated_this_session": 0,
    "vintage_cursor": 0,
    "vintages_repaired_this_session": 0,
    "strategy_validation_cursor": 0,
    "last_strategy_validation_mono": 0.0,
    "strategy_validations_this_session": 0,
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
    if not _owned_here():
        return {
            "ok": False,
            "attempted": 0,
            "completed": 0,
            "failed": 0,
            "reason": "forecast_runtime_owned_by_gather_worker",
            "process_role": _role(),
        }
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
    try:
        outcome_batch = int(os.getenv("FIE_OUTCOME_BATCH", "25"))
    except (TypeError, ValueError):
        outcome_batch = 25
    repair = repair_prediction_vintages(batch=1)
    outcome = sweep_outcomes(batch=max(batch, outcome_batch))
    try:
        validation_interval = max(900.0, float(os.getenv("STRATEGY_VALIDATION_INTERVAL_SECONDS", "1800")))
    except (TypeError, ValueError):
        validation_interval = 1800.0
    with _LOCK:
        validation_due = time.monotonic() - float(_STATE.get("last_strategy_validation_mono") or 0) >= validation_interval
    strategy_validation = sweep_strategy_validation() if validation_due else {
        "ok": True, "attempted": 0, "reason": "interval_not_elapsed",
    }
    evaluated = int(outcome.get("accuracy_rows_written") or 0)
    evaluation_errors = int(outcome.get("errors") or 0)
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
        "accuracy_rows_written": evaluated,
        "accuracy_errors": evaluation_errors,
        "outcome_sweep": outcome,
        "vintage_repair": repair,
        "strategy_validation": strategy_validation,
        "elapsed_seconds": round(elapsed, 2),
        "pipeline": pipeline_counts(),
        "results": results,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def repair_prediction_vintages(*, batch: int = 1) -> dict[str, Any]:
    """Rebuild stored summaries that predate immutable metric vintages."""
    from institutional_warehouse import store

    summaries = store.all_rows("forecast_company", limit=50000)
    predicted = set(store.entities("forecast_metric_predictions"))
    missing = sorted({
        str(row.get("symbol") or "").strip().upper()
        for row in summaries
        if row.get("symbol") and str(row.get("symbol") or "").strip().upper() not in predicted
    })
    if not missing:
        return {"ok": True, "missing_before": 0, "attempted": 0, "repaired": 0, "errors": 0}
    size = max(1, min(int(batch), 10))
    with _LOCK:
        start = int(_STATE.get("vintage_cursor") or 0) % len(missing)
    selected = [missing[(start + index) % len(missing)] for index in range(min(size, len(missing)))]
    repaired = 0
    errors = 0
    results: list[dict[str, Any]] = []
    for symbol in selected:
        try:
            pack = build_forecast(symbol)
            rows = store.all_rows("forecast_metric_predictions", entity=symbol, limit=1)
            success = bool(pack.get("ok") and rows)
            repaired += int(success)
            errors += int(not success)
            results.append({
                "symbol": symbol,
                "ok": success,
                "forecast_status": pack.get("status"),
                "prediction_rows_present": bool(rows),
            })
        except Exception as exc:
            errors += 1
            results.append({"symbol": symbol, "ok": False, "error": str(exc)[:200]})
    with _LOCK:
        _STATE["vintage_cursor"] = (start + len(selected)) % len(missing)
        _STATE["vintages_repaired_this_session"] += repaired
    return {
        "ok": errors == 0,
        "missing_before": len(missing),
        "attempted": len(selected),
        "repaired": repaired,
        "errors": errors,
        "results": results,
    }


def sweep_outcomes(*, batch: int = 25) -> dict[str, Any]:
    """Revisit forecast vintages independently of the generation queue.

    Annual actuals commonly arrive after the forecast queue has drained. A
    bounded rotating sweep ensures those forecasts are graded when the exact
    target period becomes available without coupling evaluation to regeneration.
    """
    from forecast_intelligence_engine.accuracy import evaluate_symbol
    from institutional_warehouse import store

    symbols = store.entities("forecast_metric_predictions")
    size = max(1, min(int(batch), 250))
    with _LOCK:
        start = int(_STATE.get("outcome_cursor") or 0)
    if not symbols:
        return {"ok": True, "symbols_with_predictions": 0, "attempted": 0,
                "evaluations_written": 0, "accuracy_rows_written": 0, "errors": 0,
                "next_cursor": 0}
    start %= len(symbols)
    selected = [symbols[(start + index) % len(symbols)] for index in range(min(size, len(symbols)))]
    evaluations_written = 0
    accuracy_written = 0
    errors = 0
    results: list[dict[str, Any]] = []
    for symbol in selected:
        try:
            result = evaluate_symbol(symbol)
            evaluations_written += int(result.get("evaluations_written") or 0)
            accuracy_written += int(result.get("written") or 0)
            results.append(result)
        except Exception as exc:
            errors += 1
            results.append({"ok": False, "symbol": symbol, "error": str(exc)[:200]})
    next_cursor = (start + len(selected)) % len(symbols)
    with _LOCK:
        _STATE["outcome_cursor"] = next_cursor
        _STATE["outcomes_evaluated_this_session"] += accuracy_written
    return {
        "ok": errors == 0,
        "symbols_with_predictions": len(symbols),
        "attempted": len(selected),
        "evaluations_written": evaluations_written,
        "accuracy_rows_written": accuracy_written,
        "errors": errors,
        "next_cursor": next_cursor,
        "results": results,
    }


def sweep_strategy_validation() -> dict[str, Any]:
    """Run one governed strategy backtest per sweep and persist its gate receipts."""
    from strategy_lab.production import IMPLEMENTED_STRATEGIES, backtest

    strategies = sorted(IMPLEMENTED_STRATEGIES)
    if not strategies:
        return {"ok": True, "attempted": 0, "reason": "no_implemented_strategies"}
    with _LOCK:
        cursor = int(_STATE.get("strategy_validation_cursor") or 0) % len(strategies)
    strategy_id = strategies[cursor]
    try:
        result = backtest(strategy_id, {})
        persistence = result.get("persistence") or {}
        validation = result.get("validation") or {}
        out = {
            "ok": bool(result.get("ok") and persistence.get("ok")),
            "attempted": 1,
            "strategy_id": strategy_id,
            "backtest_status": validation.get("status"),
            "economic_gates_passed": bool(validation.get("economic_gates_passed")),
            "point_in_time_status": result.get("point_in_time_status"),
            "corporate_actions_verified": bool(result.get("corporate_actions_verified")),
            "persistence": persistence.get("status"),
            "error": result.get("error") or persistence.get("error"),
        }
    except Exception as exc:
        out = {"ok": False, "attempted": 1, "strategy_id": strategy_id, "error": str(exc)[:240]}
    with _LOCK:
        _STATE["strategy_validation_cursor"] = (cursor + 1) % len(strategies)
        _STATE["last_strategy_validation_mono"] = time.monotonic()
        _STATE["strategy_validations_this_session"] += int(bool(out.get("ok")))
    return out


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
