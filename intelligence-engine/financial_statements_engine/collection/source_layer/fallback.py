"""Fallback engine — try next official source on failure (FSE-02.3).

Never stops after a single failure. Logs every attempt.
Does not call Parser / VFQE / Warehouse / DME.
"""

from __future__ import annotations

import time
from typing import Any

from financial_statements_engine.collection.source_layer import config as cfg
from financial_statements_engine.collection.source_layer.base import SourceAdapter
from financial_statements_engine.collection.source_layer.metrics import record_source_attempt
from financial_statements_engine.collection.source_layer.registry import select_sources
from financial_statements_engine.util import now_iso


def collect_with_fallback(
    ticker: str,
    *,
    filing_type: str | None = None,
    period_end: str | None = None,
    adapters: list[SourceAdapter] | None = None,
    max_retries: int | None = None,
) -> dict[str, Any]:
    """Discover + download via priority order until one source succeeds.

    Returns download bytes + winning discovery metadata + attempt log.
    Does **not** ingest — caller must call ``ingest()``.
    """
    t = ticker.upper().strip()
    ordered = adapters if adapters is not None else select_sources(filing_type=filing_type, healthy_only=True)
    retries = cfg.max_download_retries() if max_retries is None else max_retries
    attempts: list[dict[str, Any]] = []
    discovered_all: list[dict[str, Any]] = []

    for idx, adapter in enumerate(ordered):
        is_fallback = idx > 0
        t_disc0 = time.perf_counter()
        try:
            rows = adapter.discover(t, period_end=period_end, filing_type=filing_type)
        except Exception as exc:  # noqa: BLE001
            attempt = {
                "source_id": adapter.source_id,
                "phase": "discover",
                "ok": False,
                "fallback": is_fallback,
                "error": str(exc)[:160],
                "latency_ms": round((time.perf_counter() - t_disc0) * 1000.0, 2),
                "ticker": t,
                "filing_type": filing_type,
                "period_end": period_end,
                "ts": now_iso(),
            }
            attempts.append(attempt)
            record_source_attempt(attempt)
            continue

        if period_end:
            rows = [r for r in rows if not r.get("period_end") or str(r.get("period_end"))[:10] == str(period_end)[:10]]
        discovered_all.extend(rows)

        if not rows:
            attempt = {
                "source_id": adapter.source_id,
                "phase": "discover",
                "ok": False,
                "fallback": is_fallback,
                "error": "no_discoveries",
                "latency_ms": round((time.perf_counter() - t_disc0) * 1000.0, 2),
                "ticker": t,
                "filing_type": filing_type,
                "period_end": period_end,
            }
            attempts.append(attempt)
            record_source_attempt(attempt)
            continue

        # Prefer first matching discovery; retry download up to max_retries
        row = rows[0]
        meta = adapter.metadata(row)
        download_ok = False
        last_dl: dict[str, Any] = {}
        for attempt_i in range(retries + 1):
            t0 = time.perf_counter()
            try:
                last_dl = adapter.download(row)
            except Exception as exc:  # noqa: BLE001
                last_dl = {"ok": False, "error": str(exc)[:160]}
            latency = round((time.perf_counter() - t0) * 1000.0, 2)
            ok = bool(last_dl.get("ok") and last_dl.get("bytes") is not None)
            attempt = {
                "source_id": adapter.source_id,
                "phase": "download",
                "ok": ok,
                "fallback": is_fallback,
                "attempt": attempt_i,
                "error": None if ok else (last_dl.get("error") or "download_failed"),
                "latency_ms": latency,
                "ticker": t,
                "filing_type": meta.get("filing_type") or filing_type,
                "period_end": meta.get("period_end") or period_end,
                "source_url": meta.get("source_url"),
            }
            attempts.append(attempt)
            record_source_attempt(attempt)
            if ok:
                download_ok = True
                break

        if download_ok:
            return {
                "ok": True,
                "ticker": t,
                "source_id": adapter.source_id,
                "source_priority": getattr(adapter, "priority", meta.get("source_priority")),
                "discovery": meta,
                "bytes": last_dl["bytes"],
                "download": last_dl,
                "attempts": attempts,
                "discovered_n": len(discovered_all),
                "fallback_used": is_fallback,
                "alternate_discoveries": [r for r in discovered_all if r.get("source_id") != adapter.source_id],
            }

    return {
        "ok": False,
        "ticker": t,
        "error": "all_sources_failed",
        "attempts": attempts,
        "discovered_n": len(discovered_all),
        "fallback_used": any(a.get("fallback") for a in attempts),
    }
