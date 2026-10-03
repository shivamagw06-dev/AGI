"""Scale testing — throughput / latency / memory over large universes."""

from __future__ import annotations

import time
from typing import Any, Callable

from production_hardening.util import now_iso, rss_mb
from production_hardening.universe import resolve_universe


def run_scale_test(
    *,
    preset: str = "smoke",
    limit: int | None = None,
    symbols: list[str] | None = None,
    mode: str = "opportunity",  # opportunity | memory_cache | collect
    max_errors: int = 50,
    progress_every: int = 50,
    worker: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Run compiled-intelligence workload across a universe.

    Modes (no raw market API fan-out by default):
      - opportunity: OIE with cached memory inject when available
      - memory_cache: load_current only
      - collect: investment_operations.collect_company (soft)
    """
    uni = resolve_universe(preset=preset, limit=limit, symbols=symbols)
    tickers = uni["symbols"]
    fn = worker or _default_worker(mode)

    latencies: list[float] = []
    ok_n = 0
    fail_n = 0
    errors: list[dict[str, Any]] = []
    rss_start = rss_mb()
    t0 = time.perf_counter()
    checkpoints = []

    for i, t in enumerate(tickers, 1):
        s = time.perf_counter()
        try:
            out = fn(t)
            ms = (time.perf_counter() - s) * 1000.0
            latencies.append(ms)
            if isinstance(out, dict) and (out.get("ok") or out.get("_ok") or out.get("entity")):
                ok_n += 1
            else:
                fail_n += 1
                if len(errors) < max_errors:
                    errors.append({"ticker": t, "error": (out or {}).get("error") or "not_ok"})
        except Exception as exc:  # noqa: BLE001
            ms = (time.perf_counter() - s) * 1000.0
            latencies.append(ms)
            fail_n += 1
            if len(errors) < max_errors:
                errors.append({"ticker": t, "error": f"{type(exc).__name__}:{str(exc)[:120]}"})

        if progress_every and i % progress_every == 0:
            elapsed = time.perf_counter() - t0
            checkpoints.append(
                {
                    "n": i,
                    "ok_n": ok_n,
                    "elapsed_s": round(elapsed, 2),
                    "throughput_per_min": round(i / max(elapsed, 1e-6) * 60.0, 1),
                    "rss_mb": rss_mb(),
                }
            )

    elapsed = time.perf_counter() - t0
    lat_sorted = sorted(latencies)
    def pct(p: float) -> float | None:
        if not lat_sorted:
            return None
        idx = min(len(lat_sorted) - 1, max(0, int(round((p / 100.0) * (len(lat_sorted) - 1)))))
        return round(lat_sorted[idx], 2)

    return {
        "as_of": now_iso(),
        "mode": mode,
        "universe": {k: uni[k] for k in uni if k != "symbols"},
        "n": len(tickers),
        "ok_n": ok_n,
        "fail_n": fail_n,
        "success_rate_pct": round(100.0 * ok_n / max(1, len(tickers)), 1),
        "elapsed_s": round(elapsed, 2),
        "throughput_per_min": round(len(tickers) / max(elapsed, 1e-6) * 60.0, 1),
        "latency_ms": {
            "avg": round(sum(latencies) / len(latencies), 2) if latencies else None,
            "p50": pct(50),
            "p95": pct(95),
            "p99": pct(99),
            "max": round(max(latencies), 2) if latencies else None,
            "min": round(min(latencies), 2) if latencies else None,
        },
        "memory": {
            "rss_mb_start": rss_start,
            "rss_mb_end": rss_mb(),
            "rss_mb_delta": round(rss_mb() - rss_start, 2),
        },
        "checkpoints": checkpoints,
        "errors": errors,
        "recommendation_policy": "hardening_diagnostics_only_no_buy_sell",
    }


def _default_worker(mode: str) -> Callable[[str], dict[str, Any]]:
    mode = (mode or "opportunity").lower()

    def memory_cache(ticker: str) -> dict[str, Any]:
        from knowledge_delta_engine.versioning import load_current

        mem = load_current(ticker)
        if isinstance(mem, dict) and mem.get("ok"):
            return mem
        try:
            from company_memory.persist import load_memory

            mem2 = load_memory(ticker)
            return mem2 if isinstance(mem2, dict) else {"ok": False, "entity": ticker}
        except Exception:
            return {"ok": False, "entity": ticker, "error": "cache_miss"}

    def opportunity(ticker: str) -> dict[str, Any]:
        from opportunity_intelligence.production import analyse

        mem = memory_cache(ticker)
        if mem.get("ok"):
            return analyse(
                ticker,
                injected_memory=mem,
                compile_if_missing=False,
                persist_memory=False,
            )
        # Soft: still try analyse without forcing full live rebuild
        return analyse(ticker, compile_if_missing=True, persist_memory=False)

    def collect(ticker: str) -> dict[str, Any]:
        from investment_operations.collect import collect_company

        return collect_company(ticker, persist_memory=False, include_soft_reasoning=False)

    return {"memory_cache": memory_cache, "opportunity": opportunity, "collect": collect}.get(
        mode, opportunity
    )
