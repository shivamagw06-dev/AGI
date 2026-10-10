"""Research Office daily desk runner — consumes knowledge; never reasons."""

from __future__ import annotations

import time
import uuid
from typing import Any

from research_office import store
from research_office.publications.builders import build_all_morning_publications, build_company_note
from research_office.queue.builder import build_research_queue
from research_office.schema import FORBIDDEN_CLAIMS, FREEZE_LOCKS, PROGRAMME, RO_VERSION
from research_office.templates import knowledge as kn
from research_office.watchlists.engine import build_watchlists


def run_morning_desk(
    *,
    scheduler_run_id: str | None = None,
    company_triggers: list[str] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Execute Research Office after scheduler READY (or forced)."""
    t0 = time.time()
    run_id = f"ro_{uuid.uuid4().hex[:14]}"
    store.set_status(state="RUNNING", last_run_id=run_id, ready_for_users=False)

    # Gate on scheduler READY unless forced (scheduler soft-wire uses force=True)
    if not force:
        sched = kn.read_scheduler_context()
        st = (sched.get("status") or {}) if isinstance(sched, dict) else {}
        system_ready = bool(st.get("system_ready"))
        if not system_ready:
            store.set_status(state="BLOCKED", ready_for_users=False)
            return {
                "status": "blocked",
                "reason": "scheduler_not_ready",
                "run_id": run_id,
                "fabricated": False,
                "freeze_locks": FREEZE_LOCKS,
            }

    publications = build_all_morning_publications(scheduler_run_id=scheduler_run_id)

    # Company notes only when triggered by evidence / explicit tickers
    triggers = list(company_triggers or [])
    if not triggers:
        triggers = _detect_company_triggers()
    company_notes = []
    for ticker in triggers[:20]:
        company_notes.append(
            build_company_note(ticker, scheduler_run_id=scheduler_run_id, trigger_reason="new_evidence")
        )
    publications.extend(company_notes)

    queue = build_research_queue(publications=publications)
    watchlists = build_watchlists(publications=publications)

    ready_pubs = [p for p in publications if p.get("status") == "institutionally_ready"]
    duration_ms = int((time.time() - t0) * 1000)
    ready_for_users = len(ready_pubs) >= 4  # majority of core morning set

    run_row = {
        "run_id": run_id,
        "scheduler_run_id": scheduler_run_id,
        "programme": PROGRAMME,
        "version": RO_VERSION,
        "started_at": store.utc_now(),
        "duration_ms": duration_ms,
        "publication_ids": [p.get("id") for p in publications],
        "publications_count": len(publications),
        "institutionally_ready_count": len(ready_pubs),
        "company_notes": [p.get("id") for p in company_notes],
        "queue_summary": {
            "missing_evidence": len(queue.get("todays_missing_evidence") or []),
            "follow_ups": len(queue.get("todays_follow_ups") or []),
        },
        "watchlist_counts": {k: len(v) for k, v in watchlists.items()},
        "ready_for_users": ready_for_users,
        "forbidden_claims_policy": list(FORBIDDEN_CLAIMS),
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
        "reasoning_changed": False,
        "knowledge_only": True,
    }
    store.put_run(run_id, run_row)
    store.append_history(run_row)
    store.append_telemetry(
        {
            "run_id": run_id,
            "duration_ms": duration_ms,
            "publications": len(publications),
            "ready": len(ready_pubs),
            "ready_for_users": ready_for_users,
            "at": store.utc_now(),
        }
    )
    store.set_status(
        state="READY_FOR_USERS" if ready_for_users else "PARTIAL",
        last_run_id=run_id,
        ready_for_users=ready_for_users,
        publications_today=len(publications),
    )
    return {
        "status": "ok",
        "run_id": run_id,
        "scheduler_run_id": scheduler_run_id,
        "publications": [
            {
                "id": p.get("id"),
                "title": p.get("title"),
                "publication_type": p.get("publication_type"),
                "status": p.get("status"),
                "validation": p.get("validation"),
            }
            for p in publications
        ],
        "queue": queue,
        "watchlists": {k: len(v) for k, v in watchlists.items()},
        "ready_for_users": ready_for_users,
        "duration_ms": duration_ms,
        "version": RO_VERSION,
        "fabricated": False,
        "knowledge_only": True,
    }


def run_after_scheduler_ready(scheduler_result: dict[str, Any]) -> dict[str, Any]:
    """Soft-wire entry from InstitutionalScheduler after READY."""
    if not scheduler_result:
        return {"status": "skipped", "reason": "no_scheduler_result"}
    if not scheduler_result.get("system_ready"):
        return {
            "status": "skipped",
            "reason": "scheduler_not_ready",
            "state": scheduler_result.get("state"),
        }
    return run_morning_desk(
        scheduler_run_id=scheduler_result.get("run_id"),
        force=True,
    )


def _detect_company_triggers() -> list[str]:
    """Soft: trigger notes for entities present in company intelligence store."""
    try:
        from knowledge_factory.company_intelligence import store as ici_store

        if hasattr(ici_store, "list_tickers"):
            return list(ici_store.list_tickers())[:10]
        if hasattr(ici_store, "list_all"):
            rows = ici_store.list_all() or []
            out = []
            for r in rows:
                if isinstance(r, dict) and r.get("ticker"):
                    out.append(str(r["ticker"]).upper())
            return out[:10]
    except Exception:
        pass
    # Fallback: known seed if evidence feed exists
    for t in ("INFY", "TCS", "RELIANCE"):
        try:
            from knowledge_factory.production import evidence_feed

            if evidence_feed(t):
                return [t]
        except Exception:
            continue
    return []
