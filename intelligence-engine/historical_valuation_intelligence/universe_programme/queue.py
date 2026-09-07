"""Warehouse-persisted HVIE universe queue — never in-memory-only."""

from __future__ import annotations

import threading
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional

from historical_valuation_intelligence.models import ENGINE_CODE
from historical_valuation_intelligence.universe_programme.models import (
    LIFE_COMPLETE,
    LIFE_NOT_STARTED,
    LIFE_READY,
    PROGRAMME_CODE,
    QUEUE_COMPLETED,
    QUEUE_FAILED,
    QUEUE_PENDING,
    QUEUE_RETRY,
    QUEUE_RUNNING,
    QUEUE_SKIPPED,
    STAGE_CLASSIFY,
    STAGE_COMPLETE,
)

# RUNNING rows newer than this are left alone (active worker).
_STALE_RUNNING_SECONDS = 30 * 60
_COUNTS_TTL_SEC = 6.0

_LOCK = threading.RLock()
_CACHE: dict[str, Any] = {"rows_ts": 0.0, "rows": None, "counts_ts": 0.0, "counts": None}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _invalidate_cache() -> None:
    _CACHE["rows_ts"] = 0.0
    _CACHE["rows"] = None
    _CACHE["counts_ts"] = 0.0
    _CACHE["counts"] = None


def _paged_rows(tab_id: str, *, max_rows: int = 100_000) -> list[dict[str, Any]]:
    from institutional_warehouse import store

    page_size = 5000
    offset = 0
    out: list[dict[str, Any]] = []
    while offset < max_rows:
        try:
            page = store.fetch(tab_id, limit=page_size, offset=offset)
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


def _clean(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for k in list(out.keys()):
        if str(k).startswith("sys_") or k in {"row_id", "_meta"}:
            out.pop(k, None)
    return out


def upsert_queue_row(symbol: str, **fields: Any) -> dict[str, Any]:
    from institutional_warehouse import gateway, store

    ticker = str(symbol or "").strip().upper()
    existing = {}
    try:
        rows = store.fetch("hvie_universe_queue", filters={"symbol": ticker}, limit=1).get("rows") or []
        existing = rows[0] if rows else {}
    except Exception:
        existing = {}
    row = _clean({**existing, "symbol": ticker, **fields})
    gateway.write(
        "hvie_universe_queue",
        [row],
        source=ENGINE_CODE,
        actor=PROGRAMME_CODE,
        reason="hvie_universe_queue_upsert",
    )
    _invalidate_cache()
    return row


def get_queue_row(symbol: str) -> dict[str, Any]:
    from institutional_warehouse import store

    ticker = str(symbol or "").strip().upper()
    try:
        rows = store.fetch("hvie_universe_queue", filters={"symbol": ticker}, limit=1).get("rows") or []
        return rows[0] if rows else {}
    except Exception:
        return {}


def all_queue_rows(*, force: bool = False) -> list[dict[str, Any]]:
    now = time.time()
    with _LOCK:
        if (
            not force
            and _CACHE["rows"] is not None
            and (now - float(_CACHE["rows_ts"] or 0)) < _COUNTS_TTL_SEC
        ):
            return list(_CACHE["rows"])
    rows = _paged_rows("hvie_universe_queue", max_rows=50_000)
    with _LOCK:
        _CACHE["rows"] = rows
        _CACHE["rows_ts"] = now
    return list(rows)


def _parse_ts(value: Any) -> Optional[float]:
    if not value:
        return None
    try:
        s = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return None


def _is_stale_running(row: dict[str, Any], *, now_ts: float) -> bool:
    last = _parse_ts(row.get("last_run_at"))
    if last is None:
        return True
    return (now_ts - last) >= _STALE_RUNNING_SECONDS


def import_existing_hvie_progress() -> dict[str, Any]:
    """
    Adopt companies already finished by classic HVIE into the universe queue.

    Without this, a redeploy leaves ~200 seeded names as PENDING/NOT_STARTED
    and the runtime re-does heavy work (or looks stuck at 0% complete).
    """
    states = _paged_rows("hvie_company_state", max_rows=20_000)
    existing = {
        str(r.get("symbol") or "").strip().upper(): r
        for r in all_queue_rows(force=True)
        if r.get("symbol")
    }
    adopted = 0
    already = 0
    seeded_found = 0
    for st in states:
        sym = str(st.get("symbol") or "").strip().upper()
        if not sym:
            continue
        seeded = bool(st.get("seeded")) or str(st.get("status") or "").upper() == "SEEDED"
        if not seeded:
            continue
        if st.get("last_percentile") is None:
            continue
        if not st.get("last_regime"):
            continue
        seeded_found += 1
        prev = existing.get(sym) or {}
        if str(prev.get("queue_status") or "").upper() == QUEUE_COMPLETED:
            already += 1
            continue
        mark_terminal(
            sym,
            queue_status=QUEUE_COMPLETED,
            lifecycle=LIFE_COMPLETE,
            stage=STAGE_COMPLETE,
            reason="imported_existing_hvie",
            error=None,
            eligible=True,
            observations=int(st.get("observations") or prev.get("observations") or 0),
            history_window_first=st.get("first_observation") or prev.get("history_window_first"),
            history_window_last=st.get("last_observation_date") or prev.get("history_window_last"),
            has_statistics=True,
            has_percentile=True,
            has_bands=True,
            has_regime=True,
            has_research=True,
            last_percentile=st.get("last_percentile"),
            last_regime=st.get("last_regime"),
            primary_metric=st.get("primary_metric") or prev.get("primary_metric") or "pe",
            primary_model=st.get("primary_model") or prev.get("primary_model"),
            sector=prev.get("sector") or st.get("sector"),
            industry=prev.get("industry") or st.get("industry"),
        )
        adopted += 1
    return {
        "ok": True,
        "adopted": adopted,
        "already_complete": already,
        "seeded_with_signals": seeded_found,
    }


def sync_universe(
    *,
    force_reclassify: bool = False,
    recover_running: bool = True,
    adopt_existing: bool = True,
) -> dict[str, Any]:
    """Ensure every company_master symbol has a queue row. Nothing unclassified."""
    masters = _paged_rows("company_master", max_rows=20_000)
    existing = {
        str(r.get("symbol") or "").strip().upper(): r
        for r in all_queue_rows(force=True)
        if r.get("symbol")
    }
    created = 0
    repaired = 0
    for m in masters:
        sym = str(m.get("symbol") or "").strip().upper()
        if not sym:
            continue
        prev = existing.get(sym)
        if prev and not force_reclassify:
            # Only repair missing status/lifecycle — do not rewrite every row.
            if not prev.get("queue_status") or not prev.get("lifecycle"):
                upsert_queue_row(
                    sym,
                    queue_status=prev.get("queue_status") or QUEUE_PENDING,
                    lifecycle=prev.get("lifecycle") or LIFE_NOT_STARTED,
                    stage=prev.get("stage") or STAGE_CLASSIFY,
                    sector=m.get("sector") or prev.get("sector"),
                    industry=m.get("industry") or m.get("industry_dna") or prev.get("industry"),
                )
                repaired += 1
            continue

        upsert_queue_row(
            sym,
            queue_status=QUEUE_PENDING,
            lifecycle=LIFE_NOT_STARTED,
            stage=STAGE_CLASSIFY,
            eligible=None,
            sector=m.get("sector"),
            industry=m.get("industry") or m.get("industry_dna"),
            attempts=0,
            classified_at=None,
        )
        created += 1

    recovered = 0
    if recover_running:
        now_ts = time.time()
        for r in all_queue_rows(force=True):
            if str(r.get("queue_status") or "").upper() != QUEUE_RUNNING:
                continue
            if not _is_stale_running(r, now_ts=now_ts):
                continue
            upsert_queue_row(
                str(r.get("symbol")),
                queue_status=QUEUE_RETRY,
                lifecycle=LIFE_READY,
                next_retry_at=_now(),
                last_error="recovered_from_stale_running",
            )
            recovered += 1

    adopted = {"adopted": 0}
    if adopt_existing:
        adopted = import_existing_hvie_progress()

    return {
        "ok": True,
        "universe": len(masters),
        "created": created,
        "updated": repaired,
        "recovered_running": recovered,
        "adopted_existing": int(adopted.get("adopted") or 0),
        "queue_total": len(all_queue_rows(force=True)),
    }


def next_batch(*, batch: int = 20, now: Optional[str] = None) -> list[dict[str, Any]]:
    """Claim next PENDING/RETRY rows (eligible or unclassified)."""
    batch = max(1, min(int(batch), 100))
    now_s = now or _now()
    rows = all_queue_rows(force=True)
    candidates: list[dict[str, Any]] = []
    for r in rows:
        status = str(r.get("queue_status") or "").upper()
        if status == QUEUE_PENDING:
            candidates.append(r)
        elif status == QUEUE_RETRY:
            nxt = str(r.get("next_retry_at") or "")
            if not nxt or nxt <= now_s:
                candidates.append(r)
    # Prefer never-tried / fewer attempts, then alphabetical for stability.
    candidates.sort(
        key=lambda r: (
            int(r.get("attempts") or 0),
            str(r.get("symbol") or ""),
        )
    )
    claimed: list[dict[str, Any]] = []
    for r in candidates[:batch]:
        sym = str(r.get("symbol") or "").upper()
        row = upsert_queue_row(
            sym,
            queue_status=QUEUE_RUNNING,
            lifecycle="RUNNING",
            last_run_at=_now(),
        )
        claimed.append(row)
    return claimed


def queue_counts() -> dict[str, int]:
    c = Counter(str(r.get("queue_status") or "UNKNOWN").upper() for r in all_queue_rows())
    return {k: int(v) for k, v in c.items()}


def lifecycle_counts() -> dict[str, int]:
    c = Counter(str(r.get("lifecycle") or "UNKNOWN").upper() for r in all_queue_rows())
    return {k: int(v) for k, v in c.items()}


def pipeline_counts() -> dict[str, int]:
    now = time.time()
    with _LOCK:
        if _CACHE["counts"] is not None and (now - float(_CACHE["counts_ts"] or 0)) < _COUNTS_TTL_SEC:
            return dict(_CACHE["counts"])

    rows = all_queue_rows()
    counts = {
        "universe": len(rows),
        "classified": sum(1 for r in rows if r.get("lifecycle") and r.get("lifecycle") != LIFE_NOT_STARTED),
        "eligible": sum(1 for r in rows if r.get("eligible") is True),
        "seeded_history": sum(1 for r in rows if int(r.get("observations") or 0) > 0),
        "statistics": sum(1 for r in rows if r.get("has_statistics")),
        "percentiles": sum(1 for r in rows if r.get("has_percentile")),
        "bands": sum(1 for r in rows if r.get("has_bands")),
        "regimes": sum(1 for r in rows if r.get("has_regime")),
        "research": sum(1 for r in rows if r.get("has_research")),
        "complete": sum(
            1 for r in rows
            if str(r.get("lifecycle") or "").upper() == "COMPLETE"
            or str(r.get("queue_status") or "").upper() == QUEUE_COMPLETED
        ),
        "failed": sum(1 for r in rows if str(r.get("queue_status") or "").upper() == QUEUE_FAILED),
        "skipped": sum(1 for r in rows if str(r.get("queue_status") or "").upper() == QUEUE_SKIPPED),
        "pending": sum(1 for r in rows if str(r.get("queue_status") or "").upper() == QUEUE_PENDING),
        "retry": sum(1 for r in rows if str(r.get("queue_status") or "").upper() == QUEUE_RETRY),
        "running": sum(1 for r in rows if str(r.get("queue_status") or "").upper() == QUEUE_RUNNING),
    }
    with _LOCK:
        _CACHE["counts"] = counts
        _CACHE["counts_ts"] = now
    return dict(counts)


def mark_terminal(
    symbol: str,
    *,
    queue_status: str,
    lifecycle: str,
    stage: str,
    reason: Optional[str] = None,
    error: Optional[str] = None,
    **fields: Any,
) -> dict[str, Any]:
    payload = {
        "queue_status": queue_status,
        "lifecycle": lifecycle,
        "stage": stage,
        "last_run_at": _now(),
        **fields,
    }
    if reason is not None:
        payload["reason"] = reason
    if error is not None:
        payload["last_error"] = str(error)[:280]
    if queue_status == QUEUE_COMPLETED:
        payload["completed_at"] = _now()
    return upsert_queue_row(symbol, **payload)


def board_rows(*, limit_fail: int = 15, limit_next: int = 10) -> dict[str, Any]:
    """Light lists for the admin board (uses cached queue rows)."""
    rows = all_queue_rows()
    fails = sorted(
        (
            r for r in rows
            if str(r.get("queue_status") or "").upper() in {QUEUE_FAILED, QUEUE_RETRY, QUEUE_SKIPPED}
        ),
        key=lambda r: str(r.get("last_run_at") or ""),
        reverse=True,
    )[: max(1, min(int(limit_fail), 50))]
    nxt = sorted(
        (r for r in rows if str(r.get("queue_status") or "").upper() == QUEUE_PENDING),
        key=lambda r: (int(r.get("attempts") or 0), str(r.get("symbol") or "")),
    )[: max(1, min(int(limit_next), 50))]
    recent = sorted(
        (r for r in rows if str(r.get("queue_status") or "").upper() == QUEUE_COMPLETED),
        key=lambda r: str(r.get("completed_at") or r.get("last_run_at") or ""),
        reverse=True,
    )[:8]

    def _slim(r: dict[str, Any]) -> dict[str, Any]:
        return {
            "symbol": r.get("symbol"),
            "sector": r.get("sector"),
            "queue_status": r.get("queue_status"),
            "lifecycle": r.get("lifecycle"),
            "stage": r.get("stage"),
            "reason": r.get("reason") or r.get("blocking_reason"),
            "last_error": (str(r.get("last_error") or "")[:160] or None),
            "attempts": r.get("attempts"),
            "observations": r.get("observations"),
            "completed_at": r.get("completed_at"),
        }

    return {
        "failures": [_slim(r) for r in fails],
        "next_up": [_slim(r) for r in nxt],
        "recent_complete": [_slim(r) for r in recent],
    }
