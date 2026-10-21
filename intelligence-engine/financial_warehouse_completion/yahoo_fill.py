"""Yahoo-first financial statement fill — fast path for EMPTY / thin companies.

Yahoo Finance typically supplies ~4–5 annual years and ~4–6 quarters. That will
not reach COMPLETE_10Y, but it is the fastest way to:

* fill companies with no statements (EMPTY)
* lift MINIMAL → PARTIAL
* refresh share counts from statement rows

CapIQ / filings remain the path to 10y depth. This module never writes vendor
PE/PB/EV.
"""

from __future__ import annotations

import re
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

from financial_warehouse_completion.models import ENGINE_CODE, PROGRAMME_CODE, PROGRAMME_VERSION

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
    "filled": 0,
    "skipped": 0,
    "failed": 0,
    "blocked": 0,
    "mode": "yahoo_fill",
    "pause_seconds": 0.35,
}
_THREAD: Optional[threading.Thread] = None

# ETF / fund-like tickers Yahoo will not give equity statements for.
_SKIP_RE = re.compile(
    r"(ETF|BEES|LIQUID|GOLDBEES|SILVERBEES|NIFTYBEES|JUNIORBEES|BANKBEES|"
    r"ABSLLIQUID|ABSLBAN|GROWW|MON100|MOM100|ICICINIFTY|UTINIFTETF|"
    r"^NIFTY|^BANKNIFTY|HDFCSENSEX|SETFNIF|ADD$|GOLD|SILVER)",
    re.I,
)

# Recent errors surfaced on the board (ring buffer).
_LAST_ERRORS: list[dict[str, Any]] = []
_LAST_ERRORS_MAX = 25


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _looks_non_equity(symbol: str, company_name: Any = None, isin: Any = None) -> bool:
    """Skip ETFs/funds. Indian mutual-fund / ETF ISINs use INF*; equities use INE*."""
    isin_s = str(isin or "").strip().upper()
    if isin_s.startswith("INF"):
        return True
    if _SKIP_RE.search(str(symbol or "")):
        return True
    name = str(company_name or "").upper()
    if "ETF" in name or "EXCHANGE TRADED" in name or "MUTUAL FUND" in name:
        return True
    # Company name equals ticker and Unknown sector + INF already caught; also
    # skip obvious index / gold products by name.
    if any(tok in name for tok in (" BEES", "GOLD", "SILVER ETF", "NIFTY ETF")):
        return True
    return False


def _note_error(symbol: str, error: Any) -> None:
    entry = {"symbol": symbol, "error": str(error or "")[:240], "at": _now()}
    _LAST_ERRORS.append(entry)
    if len(_LAST_ERRORS) > _LAST_ERRORS_MAX:
        del _LAST_ERRORS[: len(_LAST_ERRORS) - _LAST_ERRORS_MAX]


_QUEUE_CACHE: dict[str, Any] = {"at": 0.0, "payload": None, "include_thin": None}
_QUEUE_TTL_SEC = 45.0


def queue_candidates(*, limit: int = 200, include_thin: bool = True, use_cache: bool = True) -> dict[str, Any]:
    """Rank symbols for Yahoo fill: EMPTY → MINIMAL → thin annual/quarterly."""
    from financial_warehouse_completion.audit import (
        CLASS_EMPTY,
        CLASS_MINIMAL,
        CLASS_PARTIAL,
        _annual_stats,
        _classify,
        _index_by_symbol,
        _load_rows,
        _quarterly_stats,
    )

    if use_cache and _QUEUE_CACHE.get("payload") is not None:
        age = time.monotonic() - float(_QUEUE_CACHE.get("at") or 0.0)
        if age < _QUEUE_TTL_SEC and _QUEUE_CACHE.get("include_thin") == bool(include_thin):
            cached = dict(_QUEUE_CACHE["payload"])
            rows = list(cached.get("rows") or [])[: max(1, min(int(limit), 5000))]
            cached["rows"] = rows
            counts = dict(cached.get("counts") or {})
            counts["queued"] = len(rows)
            cached["counts"] = counts
            return cached

    masters = _load_rows("company_master", limit=100000)
    annual_ix = _index_by_symbol(_load_rows("financials_annual", limit=500000))
    quarterly_ix = _index_by_symbol(_load_rows("financials_quarterly", limit=500000))

    empty: list[dict[str, Any]] = []
    minimal: list[dict[str, Any]] = []
    thin: list[dict[str, Any]] = []
    skipped_non_equity = 0

    for m in masters:
        sym = str(m.get("symbol") or "").strip().upper()
        if not sym:
            continue
        if _looks_non_equity(sym, m.get("company_name"), m.get("isin")):
            skipped_non_equity += 1
            continue
        a = _annual_stats(annual_ix.get(sym) or [])
        q = _quarterly_stats(quarterly_ix.get(sym) or [])
        years = int(a["years"])
        quarters = int(q["quarters"])
        klass = _classify(years, quarters)
        isin = str(m.get("isin") or "")
        # Prefer real equities (INE*) over unknowns when ranking EMPTY.
        equity_rank = 0 if isin.upper().startswith("INE") else 1
        row = {
            "symbol": sym,
            "company_name": m.get("company_name"),
            "sector": m.get("sector") or "Unknown",
            "isin": m.get("isin"),
            "classification": klass,
            "annual_years": years,
            "quarters": quarters,
            "priority": 1 if klass == CLASS_EMPTY else 2 if klass == CLASS_MINIMAL else 3,
            "equity_rank": equity_rank,
        }
        if klass == CLASS_EMPTY:
            empty.append(row)
        elif klass == CLASS_MINIMAL:
            minimal.append(row)
        elif include_thin and (
            years < 4 or quarters < 5 or klass == CLASS_PARTIAL and years < 4
        ):
            # Yahoo's ceiling is ~4–5y / ~5–6q — only re-hit names below that.
            thin.append(row)

    ranked = empty + minimal + thin
    ranked.sort(
        key=lambda r: (
            r["priority"],
            r.get("equity_rank", 1),
            r["annual_years"],
            r["quarters"],
            r["symbol"],
        )
    )
    cap = max(1, min(int(limit), 5000))
    payload = {
        "ok": True,
        "programme": PROGRAMME_CODE,
        "engine": ENGINE_CODE,
        "version": PROGRAMME_VERSION,
        "source": "yahoo_finance_statements",
        "yahoo_ceiling": {"annual_years": "≈4–5", "quarters": "≈4–6"},
        "counts": {
            "empty": len(empty),
            "minimal": len(minimal),
            "thin": len(thin),
            "queued": min(len(ranked), cap),
            "total_candidates": len(ranked),
            "skipped_non_equity": skipped_non_equity,
            "universe": len(masters),
        },
        "rows": ranked[:cap],
        "plain_english": (
            f"Yahoo queue: {len(empty)} EMPTY, {len(minimal)} MINIMAL, "
            f"{len(thin)} thin (<4y or <5q). Skipping {skipped_non_equity} ETF/fund-like. "
            f"Yahoo will not create 10y history — CapIQ still needed for COMPLETE_10Y."
        ),
        "checked_at": _now(),
    }
    # Cache full ranked list so batch slices share one scan.
    full = dict(payload)
    full["rows"] = ranked
    full["counts"] = {**payload["counts"], "queued": len(ranked)}
    _QUEUE_CACHE["at"] = time.monotonic()
    _QUEUE_CACHE["include_thin"] = bool(include_thin)
    _QUEUE_CACHE["payload"] = full
    return payload


def clear_queue_cache() -> None:
    _QUEUE_CACHE["at"] = 0.0
    _QUEUE_CACHE["payload"] = None


def fill_company(symbol: str, *, actor: str = "yahoo_fill") -> dict[str, Any]:
    """Fetch Yahoo statements + harvest share counts for one symbol."""
    from institutional_warehouse.backfill import statements as stmt_bf
    from financial_warehouse_completion import share_count as sc
    from financial_warehouse_completion.audit import clear_audit_cache, company_audit

    ticker = str(symbol or "").strip().upper()
    if not ticker:
        return {"ok": False, "error": "missing_symbol"}

    before = company_audit(ticker)
    out = stmt_bf.backfill_company(ticker, actor=actor)
    sc_out = sc.sync_symbol(ticker, actor=actor)
    clear_audit_cache()
    clear_queue_cache()
    after = company_audit(ticker)

    annual_n = int((out or {}).get("annual_periods") or 0)
    quarterly_n = int((out or {}).get("quarterly_periods") or 0)
    filled = bool((out or {}).get("ok")) and (annual_n + quarterly_n) > 0
    err = (out or {}).get("error")
    if err:
        _note_error(ticker, err)
    blocked = bool(err) and "yahoo_fundamentals_blocked" in str(err)
    return {
        "ok": bool((out or {}).get("ok")),
        "filled": filled,
        "symbol": ticker,
        "source": "yahoo_finance_statements",
        "annual_periods": annual_n,
        "quarterly_periods": quarterly_n,
        "share_count": sc_out,
        "before": {
            "classification": before.get("classification"),
            "annual_years": (before.get("annual") or {}).get("years"),
            "quarters": (before.get("quarterly") or {}).get("quarters"),
        },
        "after": {
            "classification": after.get("classification"),
            "annual_years": (after.get("annual") or {}).get("years"),
            "quarters": (after.get("quarterly") or {}).get("quarters"),
        },
        "error": err,
        "yahoo_fundamentals_blocked": blocked,
        "engine": ENGINE_CODE,
        "version": PROGRAMME_VERSION,
    }


def run_batch(
    *,
    batch: int = 25,
    symbols: Optional[list[str]] = None,
    actor: str = "yahoo_fill",
    pause_seconds: Optional[float] = None,
    include_thin: bool = True,
) -> dict[str, Any]:
    pause = float(_RUNTIME.get("pause_seconds") if pause_seconds is None else pause_seconds)
    if symbols:
        todo = [str(s).upper() for s in symbols if s][: max(1, min(int(batch), 200))]
        queue_meta = {"counts": {"queued": len(todo)}, "source": "explicit"}
    else:
        q = queue_candidates(limit=max(1, min(int(batch), 200)), include_thin=include_thin)
        todo = [r["symbol"] for r in (q.get("rows") or [])]
        queue_meta = q

    results: list[dict[str, Any]] = []
    filled = failed = skipped = blocked = 0
    # Explicit one-shot runs ignore a prior Pause; the background loop still respects stop.
    respect_stop = symbols is None
    for i, sym in enumerate(todo):
        if respect_stop:
            with _LOCK:
                if _RUNTIME.get("stopped"):
                    break
        try:
            out = fill_company(sym, actor=actor)
            results.append(out)
            if out.get("filled"):
                filled += 1
            elif out.get("ok"):
                skipped += 1  # Yahoo ok but empty payload
            else:
                failed += 1
                if out.get("yahoo_fundamentals_blocked"):
                    blocked += 1
        except Exception as exc:
            failed += 1
            _note_error(sym, exc)
            results.append({"ok": False, "filled": False, "symbol": sym, "error": str(exc)[:200]})
        with _LOCK:
            _RUNTIME["processed"] = int(_RUNTIME.get("processed") or 0) + 1
            _RUNTIME["filled"] = int(_RUNTIME.get("filled") or 0) + (1 if results[-1].get("filled") else 0)
            _RUNTIME["failed"] = int(_RUNTIME.get("failed") or 0) + (0 if results[-1].get("ok") else 1)
            _RUNTIME["skipped"] = int(_RUNTIME.get("skipped") or 0) + (
                1 if results[-1].get("ok") and not results[-1].get("filled") else 0
            )
            _RUNTIME["blocked"] = int(_RUNTIME.get("blocked") or 0) + (
                1 if results[-1].get("yahoo_fundamentals_blocked") else 0
            )
            _RUNTIME["last_tick"] = _now()
            _RUNTIME["last_error"] = results[-1].get("error")
            _RUNTIME["ticks"] = int(_RUNTIME.get("ticks") or 0) + 1
        if pause > 0 and i < len(todo) - 1:
            time.sleep(pause)

    batch_summary = {
        "size": len(todo),
        "filled": filled,
        "failed": failed,
        "skipped_empty_yahoo": skipped,
        "yahoo_fundamentals_blocked": blocked,
        "at": _now(),
    }
    with _LOCK:
        _RUNTIME["last_batch"] = batch_summary

    return {
        "ok": True,
        "programme": PROGRAMME_CODE,
        "engine": ENGINE_CODE,
        "version": PROGRAMME_VERSION,
        "source": "yahoo_finance_statements",
        "read_only": False,
        "vendor_historical_multiples": False,
        "batch": batch_summary,
        "queue": {
            "counts": (queue_meta.get("counts") if isinstance(queue_meta, dict) else None),
            "plain_english": queue_meta.get("plain_english") if isinstance(queue_meta, dict) else None,
        },
        "results": results[:80],
        "last_errors": list(_LAST_ERRORS)[-10:],
        "plain_english": (
            f"Yahoo batch: {filled} filled, {failed} failed"
            + (f" ({blocked} fundamentals-blocked)" if blocked else "")
            + f", {skipped} empty Yahoo. "
            + (
                "Render/cloud IPs often get empty Yahoo fundamentals — prices still work. "
                if blocked
                else ""
            )
            + "Yahoo ceiling ≈4–5 annual years — CapIQ still required for 10y depth."
        ),
        "note": (
            "Yahoo is the fast fill for EMPTY/thin names. It will not produce COMPLETE_10Y. "
            "If every symbol fails with fundamentals_empty_chart_ok, Yahoo is blocking this host."
        ),
    }


def probe(symbol: str = "RELIANCE") -> dict[str, Any]:
    """One-symbol Yahoo connectivity probe for ops / admin."""
    from institutional_warehouse.backfill.sources import yahoo_history

    ticker = str(symbol or "RELIANCE").strip().upper()
    started = time.monotonic()
    payload = yahoo_history.fetch_statements(ticker)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    err = str(payload.get("error") or "")
    return {
        "ok": bool(payload.get("ok")),
        "symbol": ticker,
        "annual_periods": len(payload.get("annual") or []),
        "quarterly_periods": len(payload.get("quarterly") or []),
        "error": err or None,
        "yahoo_fundamentals_blocked": "yahoo_fundamentals_blocked" in err,
        "transport": payload.get("transport"),
        "elapsed_ms": elapsed_ms,
        "curl_cffi": _curl_cffi_available(),
        "diagnosis": (
            "Yahoo fundamentals blocked on this host (chart/prices may still work). "
            "Need residential egress, CapIQ, or Upstox statement payloads."
            if "yahoo_fundamentals_blocked" in err
            else (
                "Yahoo returned statements."
                if payload.get("ok")
                else "Yahoo returned no statements for this symbol."
            )
        ),
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
    }


def _curl_cffi_available() -> bool:
    try:
        import curl_cffi  # noqa: F401

        return True
    except Exception:
        return False


def status() -> dict[str, Any]:
    with _LOCK:
        rt = dict(_RUNTIME)
    q = queue_candidates(limit=25, include_thin=True)
    blocked_n = int(rt.get("blocked") or 0)
    failed_n = int(rt.get("failed") or 0)
    diagnosis = None
    if failed_n and blocked_n >= max(1, failed_n // 2):
        diagnosis = (
            "Yahoo fundamentals appear blocked on this host "
            "(empty statements while prices/chart still work). "
            "Pause Yahoo fill; use CapIQ/Upstox or run Yahoo from a non-datacenter egress."
        )
    return {
        "ok": True,
        "programme": PROGRAMME_CODE,
        "engine": ENGINE_CODE,
        "version": PROGRAMME_VERSION,
        "source": "yahoo_finance_statements",
        "runtime": rt,
        "queue_preview": q,
        "last_errors": list(_LAST_ERRORS)[-10:],
        "curl_cffi": _curl_cffi_available(),
        "diagnosis": diagnosis,
        "yahoo_ceiling": {"annual_years": "≈4–5", "quarters": "≈4–6"},
        "plain_english": (
            f"Yahoo fill is {rt.get('status')}. "
            f"Processed {rt.get('processed') or 0}, filled {rt.get('filled') or 0}, "
            f"failed {rt.get('failed') or 0}"
            + (f" (blocked {blocked_n})" if blocked_n else "")
            + ". "
            + (diagnosis + " " if diagnosis else "")
            + f"{(q.get('plain_english') or '')}"
        ),
    }


def board() -> dict[str, Any]:
    st = status()
    q = st.get("queue_preview") or {}
    counts = (q.get("counts") or {})
    return {
        "ok": True,
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
        "source": "yahoo_finance_statements",
        "runtime": st.get("runtime"),
        "progress": {
            "empty_waiting": counts.get("empty"),
            "minimal_waiting": counts.get("minimal"),
            "thin_waiting": counts.get("thin"),
            "total_candidates": counts.get("total_candidates"),
            "skipped_non_equity": counts.get("skipped_non_equity"),
            "processed": (st.get("runtime") or {}).get("processed"),
            "filled": (st.get("runtime") or {}).get("filled"),
            "failed": (st.get("runtime") or {}).get("failed"),
            "blocked": (st.get("runtime") or {}).get("blocked"),
        },
        "last_errors": st.get("last_errors"),
        "diagnosis": st.get("diagnosis"),
        "curl_cffi": st.get("curl_cffi"),
        "yahoo_ceiling": st.get("yahoo_ceiling"),
        "plain_english": st.get("plain_english"),
        "what_this_does": (
            "Pulls annual + quarterly statements from Yahoo Finance into the warehouse "
            "for EMPTY and thin companies, then harvests share counts. Fast. "
            "Does not import vendor PE/PB/EV. Will not reach 10-year COMPLETE depth alone. "
            "Skips INF* fund ISINs. If Render blocks Yahoo fundamentals, every symbol fails "
            "with fundamentals_empty_chart_ok — pause and switch source."
        ),
    }


def _loop(batch: int, actor: str, pause_seconds: float, include_thin: bool) -> None:
    with _LOCK:
        _RUNTIME["status"] = "running"
        _RUNTIME["started_at"] = _RUNTIME.get("started_at") or _now()
        _RUNTIME["stopped"] = False
        _RUNTIME["mode"] = "yahoo_fill"
        _RUNTIME["pause_seconds"] = pause_seconds
        _RUNTIME["last_error"] = None
    try:
        idle_rounds = 0
        while True:
            with _LOCK:
                if _RUNTIME.get("stopped"):
                    break
            out = run_batch(
                batch=batch,
                actor=actor,
                pause_seconds=pause_seconds,
                include_thin=include_thin,
            )
            size = int((out.get("batch") or {}).get("size") or 0)
            if size == 0:
                idle_rounds += 1
                if idle_rounds >= 2:
                    break
                time.sleep(2.0)
                continue
            idle_rounds = 0
            time.sleep(0.25)
    except Exception as exc:
        with _LOCK:
            _RUNTIME["last_error"] = str(exc)[:280]
    finally:
        with _LOCK:
            _RUNTIME["status"] = "stopped" if _RUNTIME.get("stopped") else "idle"


def start(
    *,
    batch: int = 25,
    actor: str = "yahoo_fill",
    pause_seconds: float = 0.35,
    include_thin: bool = True,
) -> dict[str, Any]:
    global _THREAD
    with _LOCK:
        if _RUNTIME.get("status") == "running" and _THREAD and _THREAD.is_alive():
            return {"ok": True, "already_running": True, "runtime": dict(_RUNTIME)}
        _RUNTIME["stopped"] = False
        # Reset session counters for a fresh Start.
        _RUNTIME["processed"] = 0
        _RUNTIME["filled"] = 0
        _RUNTIME["failed"] = 0
        _RUNTIME["skipped"] = 0
        _RUNTIME["blocked"] = 0
        _RUNTIME["ticks"] = 0
        _RUNTIME["started_at"] = _now()
        _LAST_ERRORS.clear()
    t = threading.Thread(
        target=_loop,
        kwargs={
            "batch": max(1, min(int(batch), 100)),
            "actor": actor,
            "pause_seconds": max(0.0, float(pause_seconds)),
            "include_thin": bool(include_thin),
        },
        daemon=True,
    )
    _THREAD = t
    t.start()
    return {"ok": True, "started": True, "runtime": status().get("runtime"), "board": board()}


def stop() -> dict[str, Any]:
    with _LOCK:
        _RUNTIME["stopped"] = True
        _RUNTIME["status"] = "stopped"
    return {"ok": True, "stopped": True, "runtime": status().get("runtime")}


def resume(
    *,
    batch: int = 25,
    actor: str = "yahoo_fill",
    pause_seconds: float = 0.35,
    include_thin: bool = True,
) -> dict[str, Any]:
    with _LOCK:
        _RUNTIME["stopped"] = False
    return start(
        batch=batch,
        actor=actor,
        pause_seconds=pause_seconds,
        include_thin=include_thin,
    )
