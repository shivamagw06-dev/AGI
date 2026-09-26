"""Daily verification jobs — reconfirm, stale detection, confidence refresh."""

from __future__ import annotations

import datetime as _dt

from app.eve.confidence import confidence_for_evidence, freshness_from_timestamp
from app.eve.health import recompute_all_health
from app.eve.models import VerificationTask
from app.eve.store import EveStore


def run_daily_verification(store: EveStore) -> dict:
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    stale = 0
    refreshed = 0
    broken = 0
    for ev in list(store.active_evidence()):
        fresh = freshness_from_timestamp(ev.last_confirmed_at or ev.created_at)
        if fresh < 0.4:
            stale += 1
            store.evidence[ev.evidence_id] = ev.model_copy(update={"verification_status": "stale"})
            store.add_task(
                VerificationTask(
                    kind="reconfirm_stale_fact",
                    company_id=ev.company_id,
                    fact_key=ev.fact_key,
                    title=f"Reconfirm stale fact: {ev.fact_key}",
                    detail=f"Freshness {fresh}; last confirmed {ev.last_confirmed_at or ev.created_at}",
                    priority="medium",
                )
            )
        # Broken link heuristic
        if ev.provenance.url and "invalid" in ev.provenance.url:
            broken += 1
            store.add_task(
                VerificationTask(
                    kind="broken_link",
                    company_id=ev.company_id,
                    fact_key=ev.fact_key,
                    title=f"Broken/placeholder link: {ev.fact_key}",
                    detail=ev.provenance.url,
                    priority="low",
                )
            )
        # Refresh confidence
        peers = store.active_evidence(company_id=ev.company_id, fact_key=ev.fact_key)
        new_conf = confidence_for_evidence(ev, peers=peers, source_category=ev.provenance.source_name)
        if abs(new_conf - float(ev.confidence)) >= 0.01:
            store.evidence[ev.evidence_id] = store.evidence[ev.evidence_id].model_copy(
                update={"confidence": new_conf, "last_confirmed_at": now}
            )
            refreshed += 1

    # Open conflict tasks already exist; nudge unresolved
    open_conflicts = [c for c in store.conflicts.values() if c.status == "open"]
    for c in open_conflicts:
        store.add_task(
            VerificationTask(
                kind="resolve_conflict",
                company_id=c.company_id,
                fact_key=c.fact_key,
                title=c.verification_task or f"Resolve conflict on {c.fact_key}",
                detail=f"{c.left_value[:80]} vs {c.right_value[:80]}",
                priority=c.severity,  # type: ignore[arg-type]
            )
        )

    health = recompute_all_health(store)
    store.audit_event("daily_verification_job", detail=now)
    return {
        "ran_at": now,
        "stale_facts": stale,
        "confidence_refreshed": refreshed,
        "broken_links": broken,
        "open_conflicts": len(open_conflicts),
        "companies_scored": len(health),
        "tasks_open": len([t for t in store.tasks if t.status == "open"]),
    }
