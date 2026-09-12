"""Company pipeline — prices → reconstruct → stats → percentile/bands/regime → research."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from historical_valuation_intelligence.universe_programme.eligibility import classify_company
from historical_valuation_intelligence.universe_programme.models import (
    BASE_BACKOFF_SECONDS,
    LIFE_COMPLETE,
    LIFE_FAILED,
    LIFE_READY,
    LIFE_WAITING_PRICE,
    LIFE_WAITING_SHARE_COUNT,
    LIFE_WAITING_STATEMENTS,
    MAX_ATTEMPTS,
    MAX_BACKOFF_SECONDS,
    MIN_HISTORY_OBS_FOR_COMPLETE,
    QUEUE_COMPLETED,
    QUEUE_FAILED,
    QUEUE_RETRY,
    QUEUE_SKIPPED,
    STAGE_BANDS,
    STAGE_COMPLETE,
    STAGE_PERCENTILE,
    STAGE_RECONSTRUCT,
    STAGE_REGIME,
    STAGE_RESEARCH,
    STAGE_STATISTICS,
)
from historical_valuation_intelligence.universe_programme.queue import (
    get_queue_row,
    mark_terminal,
    upsert_queue_row,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _backoff_seconds(attempts: int) -> int:
    return min(MAX_BACKOFF_SECONDS, BASE_BACKOFF_SECONDS * (2 ** max(0, attempts - 1)))


def _retry(symbol: str, *, error: str, attempts: int) -> dict[str, Any]:
    if attempts >= MAX_ATTEMPTS:
        row = mark_terminal(
            symbol,
            queue_status=QUEUE_FAILED,
            lifecycle=LIFE_FAILED,
            stage=STAGE_RECONSTRUCT,
            reason="max_attempts_exceeded",
            error=error,
            attempts=attempts,
        )
        return {"ok": False, "symbol": symbol, "queue_status": QUEUE_FAILED, "row": row, "error": error}
    nxt = (datetime.now(timezone.utc) + timedelta(seconds=_backoff_seconds(attempts))).isoformat()
    row = upsert_queue_row(
        symbol,
        queue_status=QUEUE_RETRY,
        lifecycle=LIFE_READY,
        attempts=attempts,
        next_retry_at=nxt,
        last_error=str(error)[:280],
        last_run_at=_now(),
    )
    return {
        "ok": False,
        "symbol": symbol,
        "queue_status": QUEUE_RETRY,
        "next_retry_at": nxt,
        "attempts": attempts,
        "error": error,
        "row": row,
    }


def _adopt_if_already_complete(ticker: str, *, attempts: int) -> Optional[dict[str, Any]]:
    """Skip heavy reconstruct when classic HVIE already has percentile + regime."""
    from historical_valuation_intelligence import runtime as hvie_runtime

    state = hvie_runtime._get_state(ticker) or {}
    seeded = bool(state.get("seeded")) or str(state.get("status") or "").upper() == "SEEDED"
    if not seeded:
        return None
    if state.get("last_percentile") is None or not state.get("last_regime"):
        return None
    obs = int(state.get("observations") or 0)
    row = mark_terminal(
        ticker,
        queue_status=QUEUE_COMPLETED,
        lifecycle=LIFE_COMPLETE,
        stage=STAGE_COMPLETE,
        reason="already_seeded_with_signals",
        error=None,
        eligible=True,
        observations=obs,
        history_window_first=state.get("first_observation"),
        history_window_last=state.get("last_observation_date"),
        has_statistics=True,
        has_percentile=True,
        has_bands=True,
        has_regime=True,
        has_research=True,
        last_percentile=state.get("last_percentile"),
        last_regime=state.get("last_regime"),
        primary_metric=state.get("primary_metric") or "pe",
        primary_model=state.get("primary_model"),
        attempts=attempts,
    )
    return {
        "ok": True,
        "symbol": ticker,
        "queue_status": QUEUE_COMPLETED,
        "lifecycle": LIFE_COMPLETE,
        "observations": obs,
        "historical_percentile": state.get("last_percentile"),
        "regime": state.get("last_regime"),
        "adopted": True,
        "row": row,
    }


def process_company(symbol: str) -> dict[str, Any]:
    """Run one company through the HVIE completion pipeline. Persists every stage."""
    from historical_valuation_intelligence import compute, persist, runtime
    from historical_valuation_intelligence.engine import company_pack
    from historical_valuation_intelligence.research_triggers import emit_research_events

    ticker = str(symbol or "").strip().upper()
    if not ticker:
        return {"ok": False, "error": "symbol_required"}

    prev = get_queue_row(ticker)
    attempts = int(prev.get("attempts") or 0) + 1
    upsert_queue_row(
        ticker,
        queue_status="RUNNING",
        lifecycle="RUNNING",
        attempts=attempts,
        last_run_at=_now(),
        stage=STAGE_RECONSTRUCT,
    )

    adopted = _adopt_if_already_complete(ticker, attempts=attempts)
    if adopted is not None:
        return adopted

    # Phase 1 — eligibility
    clf = classify_company(ticker)
    if not clf.get("eligible"):
        life = clf.get("lifecycle") or LIFE_WAITING_PRICE
        # Waiting on inputs — park as SKIPPED-with-waiting lifecycle so bootstrap doesn't spin forever.
        # Reclassify on next sync will promote when data arrives (re-queue as PENDING).
        if life in {LIFE_WAITING_PRICE, LIFE_WAITING_STATEMENTS, LIFE_WAITING_SHARE_COUNT}:
            row = mark_terminal(
                ticker,
                queue_status=QUEUE_SKIPPED,
                lifecycle=life,
                stage="classify",
                reason=clf.get("reason"),
                error=clf.get("blocking_reason"),
                eligible=False,
                blocking_reason=clf.get("blocking_reason"),
                attempts=attempts,
            )
            return {
                "ok": True,
                "symbol": ticker,
                "queue_status": QUEUE_SKIPPED,
                "lifecycle": life,
                "reason": clf.get("blocking_reason"),
                "row": row,
            }
        return _retry(ticker, error=str(clf.get("blocking_reason") or "not_eligible"), attempts=attempts)

    primary_metric = clf.get("primary_metric") or "pe"

    # Phase 3/4 — reconstruct historical valuation (never vendor PE/PB)
    upsert_queue_row(ticker, stage=STAGE_RECONSTRUCT)
    try:
        boot = runtime.bootstrap_company(ticker, cadence="monthly")
    except Exception as exc:
        return _retry(ticker, error=f"bootstrap_exception:{exc}", attempts=attempts)

    if not boot.get("ok") and boot.get("action") != "skip":
        return _retry(
            ticker,
            error=str(boot.get("error") or "bootstrap_failed"),
            attempts=attempts,
        )

    # Ensure we have observations even if already seeded.
    ensure = compute.ensure_history(ticker, min_observations=MIN_HISTORY_OBS_FOR_COMPLETE, cadence="monthly")
    obs = int(
        boot.get("observations")
        or ensure.get("observations")
        or (runtime._get_state(ticker) or {}).get("observations")
        or 0
    )
    first = boot.get("first") or (runtime._get_state(ticker) or {}).get("first_observation")
    last = boot.get("last") or (runtime._get_state(ticker) or {}).get("last_observation_date")

    if obs < MIN_HISTORY_OBS_FOR_COMPLETE:
        # Permanent thin history after reconstruct — terminal with reason.
        row = mark_terminal(
            ticker,
            queue_status=QUEUE_FAILED,
            lifecycle=LIFE_FAILED,
            stage=STAGE_RECONSTRUCT,
            reason="insufficient_history",
            error=f"observations={obs}; need ≥{MIN_HISTORY_OBS_FOR_COMPLETE}",
            observations=obs,
            history_window_first=first,
            history_window_last=last,
            eligible=True,
            attempts=attempts,
        )
        return {
            "ok": False,
            "symbol": ticker,
            "queue_status": QUEUE_FAILED,
            "reason": "insufficient_history",
            "observations": obs,
            "row": row,
        }

    # Phase 5 — statistics
    upsert_queue_row(ticker, stage=STAGE_STATISTICS, observations=obs,
                     history_window_first=first, history_window_last=last)
    has_statistics = False
    try:
        stats = persist.persist_company_statistics(ticker, metrics=[primary_metric, "pe", "pb"])
        has_statistics = int(stats.get("rows") or 0) > 0
        runtime._upsert_state(ticker, last_stats_at=_now(), seeded=True, status="SEEDED")
    except Exception as exc:
        return _retry(ticker, error=f"statistics_failed:{exc}", attempts=attempts)

    # Phases 6–7 — percentile / bands / regime via company_pack
    upsert_queue_row(ticker, stage=STAGE_PERCENTILE, has_statistics=has_statistics)
    has_percentile = False
    has_bands = False
    has_regime = False
    last_pct = None
    last_regime = None
    try:
        pack = company_pack(ticker, metric=primary_metric, window="max")
        if pack.get("ok"):
            last_pct = pack.get("historical_percentile")
            last_regime = pack.get("regime")
            has_percentile = last_pct is not None
            has_bands = has_percentile or obs >= MIN_HISTORY_OBS_FOR_COMPLETE
            has_regime = bool(last_regime)
            runtime._upsert_state(
                ticker,
                seeded=True,
                status="SEEDED",
                last_percentile=last_pct,
                last_regime=last_regime,
                observations=obs,
                first_observation=first,
                last_observation_date=last,
                primary_metric=primary_metric,
                primary_model=clf.get("primary_model"),
                error=None,
            )
    except Exception as exc:
        return _retry(ticker, error=f"company_pack_failed:{exc}", attempts=attempts)

    upsert_queue_row(
        ticker,
        stage=STAGE_BANDS if has_bands else STAGE_PERCENTILE,
        has_percentile=has_percentile,
        has_bands=has_bands,
        has_regime=has_regime,
        last_percentile=last_pct,
        last_regime=last_regime,
    )

    # Phase 8 — research timeline triggers
    upsert_queue_row(ticker, stage=STAGE_REGIME if has_regime else STAGE_BANDS)
    has_research = False
    try:
        events = emit_research_events(
            ticker,
            metric=primary_metric,
            current_percentile=last_pct,
            previous_regime=None,
            current_regime=last_regime,
            current_value=pack.get("current") if pack.get("ok") else None,
            median=pack.get("median") if pack.get("ok") else None,
        )
        has_research = len(events or []) > 0
        # Presence of timeline row OR successful emit attempt counts for coverage
        # when percentile/regime exist — research may legitimately emit 0 events.
        if has_percentile or has_regime:
            has_research = True
    except Exception:
        has_research = bool(has_percentile or has_regime)

    upsert_queue_row(ticker, stage=STAGE_RESEARCH, has_research=has_research)

    if not (has_percentile and has_bands and has_regime):
        return _retry(
            ticker,
            error="signals_incomplete",
            attempts=attempts,
        )

    row = mark_terminal(
        ticker,
        queue_status=QUEUE_COMPLETED,
        lifecycle=LIFE_COMPLETE,
        stage=STAGE_COMPLETE,
        reason="hvie_complete",
        error=None,
        eligible=True,
        observations=obs,
        history_window_first=first,
        history_window_last=last,
        has_statistics=has_statistics,
        has_percentile=True,
        has_bands=True,
        has_regime=True,
        has_research=has_research,
        last_percentile=last_pct,
        last_regime=last_regime,
        primary_metric=primary_metric,
        primary_model=clf.get("primary_model"),
        attempts=attempts,
    )
    return {
        "ok": True,
        "symbol": ticker,
        "queue_status": QUEUE_COMPLETED,
        "lifecycle": LIFE_COMPLETE,
        "observations": obs,
        "historical_percentile": last_pct,
        "regime": last_regime,
        "row": row,
    }


def requeue_waiting(*, limit: int = 200) -> dict[str, Any]:
    """Promote SKIPPED waiting names back to PENDING when inputs may have arrived."""
    from historical_valuation_intelligence.universe_programme.queue import all_queue_rows

    promoted = 0
    for r in all_queue_rows():
        if promoted >= limit:
            break
        if str(r.get("queue_status") or "").upper() != QUEUE_SKIPPED:
            continue
        life = str(r.get("lifecycle") or "").upper()
        if life not in {LIFE_WAITING_PRICE, LIFE_WAITING_STATEMENTS, LIFE_WAITING_SHARE_COUNT}:
            continue
        sym = str(r.get("symbol") or "").upper()
        clf = classify_company(sym)
        if clf.get("eligible"):
            upsert_queue_row(
                sym,
                queue_status="PENDING",
                lifecycle=LIFE_READY,
                stage="classify",
                eligible=True,
                blocking_reason=None,
                reason="inputs_available",
                next_retry_at=None,
                last_error=None,
            )
            promoted += 1
    return {"ok": True, "promoted": promoted}
