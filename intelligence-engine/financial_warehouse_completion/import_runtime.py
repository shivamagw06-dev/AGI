"""FWCP import runtime — bootstrap / daily / retry without live Ask vendors."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from financial_warehouse_completion import coverage as cov
from financial_warehouse_completion import share_count as sc
from financial_warehouse_completion.capital_iq_import import run_capital_iq_stage
from financial_warehouse_completion.models import (
    ENGINE_CODE,
    PROGRAMME_CODE,
    PROGRAMME_VERSION,
    TARGETS,
)

_LOCK = threading.Lock()
_RUNTIME: dict[str, Any] = {
    "status": "idle",  # idle | running | stopped
    "started_at": None,
    "stopped": False,
    "last_tick": None,
    "last_error": None,
    "last_batch": None,
    "ticks": 0,
    "processed": 0,
    "completed": 0,
    "failed": 0,
    "mode": None,
}
_THREAD: Optional[threading.Thread] = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _upsert_queue(symbol: str, **fields: Any) -> None:
    from institutional_warehouse import gateway

    row = {"symbol": str(symbol).upper(), "updated_at": _now(), "source": "fwcp", **fields}
    try:
        gateway.write("fwcp_import_queue", [row], source="fwcp", actor="fwcp", reason="queue_upsert")
    except Exception:
        pass


def _queue_snapshot() -> dict[str, int]:
    from institutional_warehouse import store
    from collections import Counter

    try:
        rows = store.all_rows("fwcp_import_queue", limit=100000) or []
    except Exception:
        rows = []
    counts = Counter(str(r.get("queue_status") or "PENDING").upper() for r in rows)
    return {k: int(v) for k, v in counts.items()}


def status() -> dict[str, Any]:
    with _LOCK:
        rt = dict(_RUNTIME)
    board = cov.financial_coverage()
    return {
        "ok": True,
        "programme": PROGRAMME_CODE,
        "engine": ENGINE_CODE,
        "version": PROGRAMME_VERSION,
        "runtime": rt,
        "queue": _queue_snapshot(),
        "coverage": {
            "universe": board.get("universe"),
            "metrics": board.get("metrics"),
            "counts": board.get("counts"),
        },
        "plain_english": board.get("plain_english"),
        "schedules": {
            "bootstrap": "drain missing statements + share counts until targets",
            "daily": "re-import changed / thin companies",
            "quarterly": "new statement wave",
            "event": "corrections / CapIQ re-export",
        },
    }


def board() -> dict[str, Any]:
    st = status()
    metrics = (st.get("coverage") or {}).get("metrics") or {}
    counts = (st.get("coverage") or {}).get("counts") or {}
    universe = int((st.get("coverage") or {}).get("universe") or 0)
    return {
        "ok": True,
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
        "runtime": st.get("runtime"),
        "queue": st.get("queue"),
        "progress": {
            "universe": universe,
            "financial_ok": counts.get("financial_ok"),
            "share_count_ok": counts.get("share_count_ok"),
            "hvie_ready": counts.get("hvie_ready"),
            "hvie_complete": counts.get("hvie_complete"),
            "annual_pct": metrics.get("annual_pct"),
            "quarterly_pct": metrics.get("quarterly_pct"),
            "share_count_pct": metrics.get("share_count_pct"),
            "company_financial_pct": metrics.get("company_financial_pct"),
            "hvie_eligible_pct": metrics.get("hvie_eligible_pct"),
            "hvie_complete_pct": metrics.get("hvie_complete_pct"),
        },
        "targets": TARGETS,
        "plain_english": st.get("plain_english"),
        "what_this_does": (
            "Completes annual/quarterly statements, share counts, ownership, peers and "
            "consensus in the Institutional Warehouse so HVIE/RIE/FIE stop stalling on missing inputs. "
            "Never imports vendor historical PE/PB/EV."
        ),
        "packs": [
            "company_master",
            "financials_annual",
            "financials_quarterly",
            "share_count_history",
            "consensus",
            "ownership",
            "peer_relationships",
            "profile_history",
        ],
    }


def _process_symbol(symbol: str, *, actor: str) -> dict[str, Any]:
    """One-company FWCP pass: CapIQ/Yahoo/Upstox soft stages + share-count harvest."""
    ticker = str(symbol).upper()
    _upsert_queue(ticker, queue_status="RUNNING", last_run_at=_now(), pack="financials")
    errors: list[str] = []
    actions: list[str] = []

    # 1) Yahoo statement backfill when thin
    try:
        from institutional_warehouse.backfill import statements as stmt_bf

        pack = cov.company_coverage(ticker)
        preferred = pack.get("preferred") or {}
        if not preferred.get("annual_10y") or not preferred.get("quarterly_8q"):
            if hasattr(stmt_bf, "backfill_company"):
                out = stmt_bf.backfill_company(ticker, actor=actor)
                actions.append("yahoo_statements")
                if not (out or {}).get("ok", True):
                    errors.append(str((out or {}).get("error") or "yahoo_statements_failed")[:160])
    except Exception as exc:
        errors.append(f"yahoo:{exc}"[:160])

    # 2) Upstox fundamentals bundle when available (no live Ask path — may no-op without keys)
    try:
        from upstox_fundamentals.ingest import ingest_bundle

        pack = cov.company_coverage(ticker)
        if not pack.get("financial_ok") or not pack.get("share_count_ok"):
            out = ingest_bundle(ticker, actor=actor)
            actions.append("upstox_fundamentals")
            if isinstance(out, dict) and out.get("ok") is False:
                errors.append(str(out.get("error") or "upstox_failed")[:160])
    except Exception as exc:
        # Soft — missing credentials are expected in some envs
        errors.append(f"upstox:{type(exc).__name__}")

    # 3) Share count harvest into dedicated tab
    sc_out = sc.sync_symbol(ticker, actor=actor)
    actions.append("share_count_sync")
    if not sc_out.get("ok") and sc_out.get("error"):
        errors.append(str(sc_out.get("error"))[:160])

    pack = cov.company_coverage(ticker)
    done = bool(pack.get("financial_ok") and pack.get("share_count_ok"))
    _upsert_queue(
        ticker,
        queue_status="COMPLETED" if done else ("RETRY" if errors else "PENDING"),
        lifecycle="COMPLETE" if done else "READY",
        annual_ok=bool(pack.get("packs", {}).get("financials_annual")),
        quarterly_ok=bool(pack.get("packs", {}).get("financials_quarterly")),
        share_count_ok=bool(pack.get("share_count_ok")),
        consensus_ok=bool(pack.get("packs", {}).get("consensus")),
        ownership_ok=bool(pack.get("packs", {}).get("ownership")),
        peers_ok=bool(pack.get("packs", {}).get("peer_relationships")),
        profile_ok=bool(pack.get("packs", {}).get("profile_history")),
        last_error="; ".join(errors)[:280] if errors else None,
        next_retry_at=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
        if not done
        else None,
        completed_at=_now() if done else None,
        blocking_reason=(
            None
            if done and pack.get("strategy_ready")
            else (
                "preferred_statement_depth"
                if done
                else ("missing_statements" if not pack.get("financial_ok") else "missing_share_count")
            )
        ),
    )
    return {
        "ok": done,
        "symbol": ticker,
        "actions": actions,
        "errors": errors,
        "coverage": pack,
        "engine": ENGINE_CODE,
    }


def run_batch(
    *,
    batch: int = 10,
    symbols: Optional[list[str]] = None,
    actor: str = "fwcp",
    include_capital_iq: bool = False,
) -> dict[str, Any]:
    """Process a batch of missing-statement / missing-share-count companies."""
    if include_capital_iq:
        capiq = run_capital_iq_stage(actor=actor)
    else:
        capiq = {"ok": True, "skipped": True}

    if symbols:
        todo = [str(s).upper() for s in symbols if s]
    else:
        miss_stmt = cov.missing_statements(limit=batch)
        miss_share = cov.missing_share_count(limit=batch)
        todo_set: list[str] = []
        for row in (miss_stmt.get("missing_annual") or []) + (miss_stmt.get("missing_quarterly") or []):
            sym = row.get("symbol")
            if sym and sym not in todo_set:
                todo_set.append(sym)
        for row in miss_share.get("rows") or []:
            sym = row.get("symbol")
            if sym and sym not in todo_set:
                todo_set.append(sym)
        todo = todo_set[: max(1, min(int(batch), 100))]

    results = []
    completed = failed = 0
    for sym in todo:
        with _LOCK:
            if _RUNTIME.get("stopped"):
                break
        try:
            out = _process_symbol(sym, actor=actor)
            results.append(out)
            if out.get("ok"):
                completed += 1
            else:
                failed += 1
        except Exception as exc:
            failed += 1
            results.append({"ok": False, "symbol": sym, "error": str(exc)[:200]})
        with _LOCK:
            _RUNTIME["processed"] = int(_RUNTIME.get("processed") or 0) + 1
            _RUNTIME["completed"] = int(_RUNTIME.get("completed") or 0) + completed
            _RUNTIME["failed"] = int(_RUNTIME.get("failed") or 0) + (1 if not results[-1].get("ok") else 0)
            _RUNTIME["last_tick"] = _now()
            _RUNTIME["ticks"] = int(_RUNTIME.get("ticks") or 0) + 1

    with _LOCK:
        _RUNTIME["last_batch"] = {
            "size": len(todo),
            "completed": completed,
            "failed": failed,
            "at": _now(),
        }
    return {
        "ok": True,
        "batch": len(todo),
        "completed": completed,
        "failed": failed,
        "capital_iq": capiq,
        "results": results[:50],
        "engine": ENGINE_CODE,
        "version": PROGRAMME_VERSION,
    }


def _loop(batch: int, actor: str) -> None:
    with _LOCK:
        _RUNTIME["status"] = "running"
        _RUNTIME["started_at"] = _RUNTIME.get("started_at") or _now()
        _RUNTIME["stopped"] = False
        _RUNTIME["mode"] = "bootstrap"
        _RUNTIME["last_error"] = None
    try:
        while True:
            with _LOCK:
                if _RUNTIME.get("stopped"):
                    break
            out = run_batch(batch=batch, actor=actor, include_capital_iq=False)
            if int(out.get("batch") or 0) == 0:
                break
            time.sleep(0.5)
    except Exception as exc:
        with _LOCK:
            _RUNTIME["last_error"] = str(exc)[:280]
    finally:
        with _LOCK:
            _RUNTIME["status"] = "stopped" if _RUNTIME.get("stopped") else "idle"
            _RUNTIME["mode"] = None


def start(*, batch: int = 15, actor: str = "fwcp") -> dict[str, Any]:
    global _THREAD
    with _LOCK:
        if _RUNTIME.get("status") == "running" and _THREAD and _THREAD.is_alive():
            return {"ok": True, "already_running": True, "runtime": dict(_RUNTIME)}
        _RUNTIME["stopped"] = False
    t = threading.Thread(target=_loop, kwargs={"batch": batch, "actor": actor}, daemon=True)
    _THREAD = t
    t.start()
    return {"ok": True, "started": True, "runtime": status().get("runtime")}


def stop() -> dict[str, Any]:
    with _LOCK:
        _RUNTIME["stopped"] = True
        _RUNTIME["status"] = "stopped"
    return {"ok": True, "stopped": True, "runtime": status().get("runtime")}


def resume(*, batch: int = 15, actor: str = "fwcp") -> dict[str, Any]:
    with _LOCK:
        _RUNTIME["stopped"] = False
    return start(batch=batch, actor=actor)


def retry(*, limit: int = 50, actor: str = "fwcp") -> dict[str, Any]:
    from institutional_warehouse import store

    try:
        rows = store.all_rows("fwcp_import_queue", limit=100000) or []
    except Exception:
        rows = []
    symbols = [
        str(r.get("symbol")).upper()
        for r in rows
        if str(r.get("queue_status") or "").upper() in {"RETRY", "FAILED", "PENDING"}
    ][: max(1, min(int(limit), 200))]
    if not symbols:
        # Fall back to coverage gaps
        return run_batch(batch=limit, actor=actor)
    return run_batch(batch=len(symbols), symbols=symbols, actor=actor)
