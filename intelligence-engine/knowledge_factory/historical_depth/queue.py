"""Persistent historical backfill backlog queue — survives restarts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.completion import history_years
from knowledge_factory.historical_depth.universe_priority import (
    prioritised_universe,
    priority_tier,
    supported_universe,
    tier_label,
)

QUEUE_REPORT = "historical_backfill_queue"
ENGINE_STATE = "historical_backfill_engine_state"
QUEUE_VERSION = "hd-queue-v1.0.0"

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETE = "complete"
STATUS_FAILED = "failed"
STATUS_COOLDOWN = "cooldown"
STATUS_MAINTENANCE = "maintenance"
STATUS_DELISTED = "delisted"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def load_queue() -> dict[str, Any]:
    raw = hd_store.get_report(QUEUE_REPORT) or {}
    companies = list(raw.get("companies") or [])
    return {
        "queue_version": QUEUE_VERSION,
        "companies": companies,
        "updated_at": raw.get("updated_at"),
    }


def save_queue(payload: dict[str, Any]) -> dict[str, Any]:
    companies = list(payload.get("companies") or [])
    pending_like = {
        STATUS_PENDING,
        STATUS_RUNNING,
        STATUS_FAILED,
        STATUS_COOLDOWN,
    }
    body = {
        **payload,
        "queue_version": QUEUE_VERSION,
        "updated_at": _now_iso(),
        "queue_length": len([c for c in companies if str(c.get("status")) in pending_like]),
        "completed_count": len(
            [c for c in companies if str(c.get("status")) in {STATUS_COMPLETE, STATUS_MAINTENANCE}]
        ),
        "coverage_finished": False,
        "always_ready": True,
    }
    # Crash-safe durable mirror + locked write
    try:
        from institutional_data.persistence.queue_persistence import QueuePersistence

        QueuePersistence().save_queue(body)
    except Exception:
        hd_store.put_report(QUEUE_REPORT, body)
    else:
        hd_store.put_report(QUEUE_REPORT, body)
    return body


def load_engine_state() -> dict[str, Any]:
    return hd_store.get_report(ENGINE_STATE) or {
        "mode": "deep_backfill",
        "deep_backfill_enabled": True,
        "maintenance_only": False,
        "completed_at": None,
        "companies_processed_today": 0,
        "day_key": None,
    }


def save_engine_state(state: dict[str, Any]) -> dict[str, Any]:
    body = {**state, "updated_at": _now_iso()}
    hd_store.put_report(ENGINE_STATE, body)
    return body


def enqueue_company(
    symbol: str,
    *,
    reason: str = "manual",
    listing_date: str | None = None,
) -> dict[str, Any]:
    """Add or reopen a company on the backlog (e.g. new IPO / listing)."""
    e = symbol.upper().strip()
    q = load_queue()
    companies = list(q.get("companies") or [])
    found = None
    for row in companies:
        if str(row.get("company") or "").upper() == e:
            found = row
            break
    if found is None:
        found = {
            "company": e,
            "priority": priority_tier(e),
            "tier": tier_label(priority_tier(e)),
            "status": STATUS_PENDING,
            "attempts": 0,
            "last_run": None,
            "coverage": 0.0,
            "years": history_years(e),
            "errors": [],
            "mode": "backfill",
            "listing_date": listing_date,
            "enqueued_reason": reason,
            "enqueued_at": _now_iso(),
        }
        companies.append(found)
    else:
        # Reopen from maintenance/delisted into backfill for listing-date history
        if str(found.get("status")) in {STATUS_MAINTENANCE, STATUS_COMPLETE, STATUS_DELISTED}:
            found["status"] = STATUS_PENDING
            found["mode"] = "backfill"
            found["enqueued_reason"] = reason
            found["enqueued_at"] = _now_iso()
            found["listing_date"] = listing_date or found.get("listing_date")
            found.pop("cooldown_until", None)
    companies.sort(
        key=lambda c: (int(c.get("priority") or 99), float(c.get("years") or 0.0), str(c.get("company")))
    )
    q["companies"] = companies
    save_queue(q)
    # Reopen deep mode if we were in maintenance-only
    state = load_engine_state()
    if state.get("maintenance_only"):
        save_engine_state(
            {
                **state,
                "mode": "deep_backfill",
                "deep_backfill_enabled": True,
                "maintenance_only": False,
                "reopened_at": _now_iso(),
                "reopen_reason": reason,
                "note": "New listing/IPO enqueued — deep backfill reopened; coverage never permanently finished",
            }
        )
    return found


def mark_delisted(symbol: str) -> None:
    e = symbol.upper()
    q = load_queue()
    for row in q.get("companies") or []:
        if str(row.get("company") or "").upper() == e:
            row["status"] = STATUS_DELISTED
            row["mode"] = "delisted"
            row["delisted_at"] = _now_iso()
            break
    save_queue(q)


def ensure_queue(*, force_refresh: bool = False) -> dict[str, Any]:
    """Ensure every supported listed company is on the queue.

    Also soft-syncs the living universe so new listings/IPOs are auto-enqueued.
    The queue may be empty of pending work but is never retired.
    """
    # Living universe sync (lazy) — detects IPO listings / delists
    try:
        from knowledge_factory.historical_depth.living_universe import sync_listed_universe

        sync_listed_universe()
    except Exception:
        pass

    q = load_queue()
    existing = {str(c.get("company") or "").upper(): c for c in (q.get("companies") or [])}
    years_map = {s: history_years(s) for s in supported_universe()}
    ordered = prioritised_universe(coverage_years=years_map)
    for s in ordered:
        if s in existing:
            row = existing[s]
            if str(row.get("status")) == STATUS_DELISTED:
                continue
            row["years"] = years_map.get(s, 0.0)
            row["priority"] = priority_tier(s)
            row["tier"] = tier_label(priority_tier(s))
            continue
        existing[s] = {
            "company": s,
            "priority": priority_tier(s),
            "tier": tier_label(priority_tier(s)),
            "status": STATUS_PENDING,
            "attempts": 0,
            "last_run": None,
            "coverage": 0.0,
            "years": years_map.get(s, 0.0),
            "errors": [],
            "mode": "backfill",
        }
    companies = list(existing.values())
    companies.sort(
        key=lambda c: (int(c.get("priority") or 99), float(c.get("years") or 0.0), str(c.get("company")))
    )
    q["companies"] = companies
    q["always_ready"] = True
    q["coverage_finished"] = False
    return save_queue(q)


def _backoff_seconds(attempts: int) -> float:
    # Exponential: 2^min(attempts,8) minutes, capped ~4h
    mins = min(240.0, float(2 ** min(max(1, attempts), 8)))
    return mins * 60.0


def next_batch(*, batch_size: int = 12, maintenance: bool = False) -> list[dict[str, Any]]:
    """Select next companies respecting cooldown and priority."""
    q = ensure_queue()
    now = _now()
    selected: list[dict[str, Any]] = []
    companies = list(q.get("companies") or [])
    # Sort: priority, then lowest years, then oldest last_run
    companies.sort(
        key=lambda c: (
            int(c.get("priority") or 99),
            float(c.get("years") or 0.0),
            str(c.get("last_run") or ""),
            str(c.get("company") or ""),
        )
    )
    for row in companies:
        if len(selected) >= batch_size:
            break
        status = str(row.get("status") or STATUS_PENDING)
        if status == STATUS_DELISTED:
            continue
        if maintenance:
            if status not in {STATUS_COMPLETE, STATUS_MAINTENANCE}:
                continue
        else:
            if status in {STATUS_COMPLETE, STATUS_MAINTENANCE}:
                continue
            if status == STATUS_COOLDOWN:
                ready = _parse_iso(row.get("cooldown_until"))
                if ready and ready > now:
                    continue
        selected.append(row)
    return selected


def mark_running(company: str) -> None:
    _update_row(company, status=STATUS_RUNNING, last_run=_now_iso())


def mark_result(company: str, evaluation: dict[str, Any], *, error: str | None = None) -> dict[str, Any]:
    e = company.upper()
    q = load_queue()
    rows = list(q.get("companies") or [])
    out_row = None
    for row in rows:
        if str(row.get("company") or "").upper() != e:
            continue
        row["attempts"] = int(row.get("attempts") or 0) + 1
        row["last_run"] = _now_iso()
        row["years"] = evaluation.get("history_years") or row.get("years") or 0.0
        row["coverage"] = evaluation.get("coverage_pct") or 0.0
        if error:
            errs = list(row.get("errors") or [])
            errs.insert(0, {"at": _now_iso(), "error": error[:200]})
            row["errors"] = errs[:10]
            delay = _backoff_seconds(int(row["attempts"]))
            row["status"] = STATUS_COOLDOWN
            row["cooldown_until"] = (_now() + timedelta(seconds=delay)).isoformat()
            row["mode"] = "backfill"
        elif evaluation.get("hard_ok") or evaluation.get("complete"):
            # Hard requirements gate maintenance; soft % is informational only
            row["status"] = STATUS_MAINTENANCE
            row["mode"] = "maintenance"
            row["completed_at"] = row.get("completed_at") or _now_iso()
            row["hard_pct"] = evaluation.get("hard_pct")
            row["soft_pct"] = evaluation.get("soft_pct")
            row["overall_pct"] = evaluation.get("overall_pct")
            row["density"] = (evaluation.get("density") or {}).get("density")
            row["errors"] = []
            row.pop("cooldown_until", None)
        else:
            row["status"] = STATUS_PENDING
            row["mode"] = "backfill"
            row["hard_pct"] = evaluation.get("hard_pct")
            row["soft_pct"] = evaluation.get("soft_pct")
            row["overall_pct"] = evaluation.get("overall_pct")
            # Light backoff even on partial progress to rotate fairly
            if int(row["attempts"]) > 3 and float(row.get("hard_pct") or row.get("coverage") or 0) < 50:
                delay = _backoff_seconds(int(row["attempts"]) // 2)
                row["status"] = STATUS_COOLDOWN
                row["cooldown_until"] = (_now() + timedelta(seconds=delay)).isoformat()
        out_row = row
        break
    q["companies"] = rows
    save_queue(q)
    return out_row or {}


def _update_row(company: str, **fields: Any) -> None:
    e = company.upper()
    q = load_queue()
    for row in q.get("companies") or []:
        if str(row.get("company") or "").upper() == e:
            row.update(fields)
            break
    save_queue(q)


def backlog_stats() -> dict[str, Any]:
    """Queue-plane stats + verified data-plane coverage when available.

    Coverage / remaining prefer reconciliation so an empty queue never
    masquerades as historical completeness.
    """
    q = ensure_queue()
    companies = list(q.get("companies") or [])
    active = [c for c in companies if str(c.get("status")) != STATUS_DELISTED]
    remaining = [
        c
        for c in active
        if str(c.get("status")) not in {STATUS_COMPLETE, STATUS_MAINTENANCE}
    ]
    done = [c for c in active if str(c.get("status")) in {STATUS_COMPLETE, STATUS_MAINTENANCE}]
    years = [float(c.get("years") or 0.0) for c in active] or [0.0]
    state = load_engine_state()
    hard_avg = 0.0
    soft_avg = 0.0
    hard_vals = [float(c.get("hard_pct") or 0) for c in active if c.get("hard_pct") is not None]
    soft_vals = [float(c.get("soft_pct") or 0) for c in active if c.get("soft_pct") is not None]
    if hard_vals:
        hard_avg = round(sum(hard_vals) / len(hard_vals), 2)
    if soft_vals:
        soft_avg = round(sum(soft_vals) / len(soft_vals), 2)

    queue_remaining = len(remaining)
    queue_done = len(done)
    verified = hd_store.get_report("coverage_reconciliation") or {}
    if verified.get("incomplete") is not None:
        remaining_n = int(verified.get("incomplete") or 0)
        done_n = int(verified.get("verified_complete") or 0)
        total_n = int(verified.get("universe_scanned") or len(active) or 1)
        coverage_pct = float(verified.get("verified_hard_coverage_pct") or 0)
        avg_years = float(verified.get("average_history_years") or (sum(years) / max(1, len(years))))
        if verified.get("verified_hard_coverage_pct") is not None:
            hard_avg = coverage_pct
    else:
        remaining_n = queue_remaining
        done_n = queue_done
        total_n = len(active)
        coverage_pct = round(100.0 * done_n / max(1, total_n), 2)
        avg_years = round(sum(years) / max(1, len(years)), 2)

    return {
        "total_companies": total_n if verified else len(active),
        "fully_backfilled": done_n,
        "remaining": remaining_n,
        "queue_length": queue_remaining,
        "queue_fully_backfilled": queue_done,
        "average_years": avg_years,
        "coverage_pct": coverage_pct,
        "hard_coverage_pct": hard_avg,
        "soft_coverage_pct": soft_avg,
        "mode": state.get("mode") or "deep_backfill",
        "maintenance_only": bool(state.get("maintenance_only")),
        "completed_at": state.get("completed_at"),
        "companies_processed_today": int(state.get("companies_processed_today") or 0),
        "coverage_finished": False,
        "queue_always_ready": True,
        "authority": (
            (verified.get("authority") or "evidence_based_completion") if verified else "queue_state"
        ),
        "dataset_coverage": (verified.get("dataset_coverage") if verified else None),
        "maintenance_allowed": verified.get("maintenance_allowed") if verified else None,
    }


def maybe_transition_to_maintenance() -> dict[str, Any]:
    """Maintenance only when verified coverage thresholds pass — never from empty queue alone."""
    # Refresh data-plane reconciliation (throttled inside helper)
    try:
        from knowledge_factory.historical_depth.coverage_reconcile import maybe_reconcile

        maybe_reconcile(enqueue=True)
    except Exception:
        try:
            from knowledge_factory.historical_depth.coverage_reconcile import reconcile_universe

            reconcile_universe(enqueue=True)
        except Exception:
            pass

    stats = backlog_stats()
    state = load_engine_state()
    verified = hd_store.get_report("coverage_reconciliation") or {}
    allowed = bool(verified.get("maintenance_allowed")) if verified else False

    if allowed and int(stats.get("remaining") or 0) == 0 and int(stats.get("total_companies") or 0) > 0:
        if not state.get("maintenance_only"):
            state = save_engine_state(
                {
                    **state,
                    "mode": "maintenance",
                    "deep_backfill_enabled": False,
                    "maintenance_only": True,
                    "completed_at": state.get("completed_at") or _now_iso(),
                    "coverage_finished": False,
                    "verified_gate": True,
                    "note": (
                        "Verified data-plane coverage thresholds met — maintenance-only. "
                        "Queue remains ready; new IPOs/listings auto-enqueue and reopen deep backfill."
                    ),
                }
            )
        return {**stats, "transitioned": True, "engine": state, "verified_gate": True}

    # Empty queue is NOT enough — reopen when verification fails
    if state.get("maintenance_only") and not allowed:
        state = save_engine_state(
            {
                **state,
                "mode": "deep_backfill",
                "deep_backfill_enabled": True,
                "maintenance_only": False,
                "reopened_at": _now_iso(),
                "verified_gate": False,
                "note": "Reopened: verified coverage below maintenance thresholds",
            }
        )
        return {**stats, "transitioned": False, "reopened": True, "engine": state, "verified_gate": False}

    if state.get("maintenance_only") and int(stats.get("remaining") or 0) > 0:
        state = save_engine_state(
            {
                **state,
                "mode": "deep_backfill",
                "deep_backfill_enabled": True,
                "maintenance_only": False,
                "reopened_at": _now_iso(),
                "note": "Backlog non-empty (new listing or incomplete hard dims) — deep backfill active",
            }
        )
        return {**stats, "transitioned": False, "reopened": True, "engine": state}

    state = save_engine_state(
        {
            **state,
            "mode": "deep_backfill" if not state.get("maintenance_only") else "maintenance",
            "deep_backfill_enabled": not bool(state.get("maintenance_only")),
            "coverage_finished": False,
            "verified_gate": allowed,
        }
    )
    return {**stats, "transitioned": False, "engine": state, "verified_gate": allowed}


def bump_processed_today(n: int = 1) -> None:
    state = load_engine_state()
    day = _now().date().isoformat()
    if state.get("day_key") != day:
        state["day_key"] = day
        state["companies_processed_today"] = 0
    state["companies_processed_today"] = int(state.get("companies_processed_today") or 0) + n
    save_engine_state(state)


def eta_days(*, processed_today: int | None = None, remaining: int | None = None) -> float | None:
    stats = backlog_stats()
    rem = remaining if remaining is not None else int(stats.get("remaining") or 0)
    today = processed_today if processed_today is not None else int(stats.get("companies_processed_today") or 0)
    # Prefer last-batch rate from report
    last = hd_store.get_report("historical_backfill_last") or {}
    processed = int(last.get("processed") or 0)
    runtime = float(last.get("runtime_seconds") or 0) or 0.0
    if processed > 0 and runtime > 0:
        per_day = (processed / runtime) * 86400.0
        if per_day > 0:
            return round(rem / per_day, 1)
    if today > 0:
        return round(rem / max(today, 1), 1)
    return None
