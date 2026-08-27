"""Watchlist Queue Report (WQR) — Office SDK contracts only."""

from __future__ import annotations

import time
from typing import Any, Mapping, Optional

from office_sdk.contracts import (
    confidence_summary,
    evidence_block,
    evidence_reference,
    flatten_blocks,
    office_metadata,
    office_request,
    office_response,
    office_section,
    provenance_bundle,
)
from office_sdk.schema import DOMAIN_PORTFOLIO
from watchlist_office.schema import (
    WO01_OFFICE_ID,
    WO01_PRODUCT,
    WO01_VERSION,
    WO01_WORKSTREAM_ID,
    WQR_SECTION_TITLES,
    WQR_SECTIONS,
)
from watchlist_office.service import research_queue
from watchlist_office import store as wl_store
from watchlist_office.events import ensure_subscriptions


def build_wqr(
    watchlist_id: str,
    *,
    question: Optional[str] = None,
    request: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    ensure_subscriptions()
    t0 = time.perf_counter()
    wl = wl_store.resolve_watchlist(watchlist_id)
    if not wl:
        raise ValueError(f"watchlist not found: {watchlist_id}")
    queue = research_queue(str(wl.get("watchlist_id")))
    meta = wl.get("metadata") or {}
    recent = wl_store.recent_events(limit=20)

    def blk(text: str, module: str = "WO-01", eids=None, confidence: float = 1.0, kind: str = "queue"):
        return evidence_block(
            text,
            module=module,
            evidence_ids=list(eids or []),
            confidence=float(confidence),
            kind=kind,
        )

    section_map: dict[str, list] = {}
    section_map["watchlist_summary"] = [
        blk(
            (
                f"Watchlist {meta.get('name')} ({wl.get('watchlist_id')}) — research queue. "
                f"Active={queue['counts']['active']} archived={queue['counts']['archived']}. "
                "WO-01 does not perform research; it references IO-01 / FIRE outputs via events."
            ),
            kind="summary",
        )
    ]
    section_map["research_queue"] = [
        blk(
            (
                f"{e.get('ticker')} ({e.get('company')}): status={e.get('status')} "
                f"priority={e.get('priority')} tags={e.get('tags')} "
                f"last_research={e.get('last_research_at')} "
                f"last_event={e.get('last_event_type')}"
            ),
            kind="entry",
        )
        for e in queue.get("queue") or []
    ] or [blk("Queue empty.", confidence=0.0)]

    by_status = queue["counts"]["by_status"]
    section_map["by_status"] = [
        blk(f"{k}: {v}", kind="status") for k, v in sorted(by_status.items())
    ] or [blk("No status rows.", confidence=0.0)]

    by_pri = queue["counts"]["by_priority"]
    section_map["by_priority"] = [
        blk(f"{k}: {v}", kind="priority") for k, v in sorted(by_pri.items())
    ] or [blk("No priority rows.", confidence=0.0)]

    section_map["recent_events"] = [
        blk(
            f"{r.get('event_type')} tickers={r.get('tickers')} updated={r.get('entries_updated')} at={r.get('at')}",
            module="PEB-01",
            eids=[r.get("event_id")] if r.get("event_id") else [],
            kind="event",
        )
        for r in recent
    ] or [blk("No PEB events applied yet.", module="PEB-01", confidence=0.0)]

    # Confidence: fraction of active entries with at least one intelligence timestamp
    active = queue.get("queue") or []
    touched = sum(
        1
        for e in active
        if e.get("last_research_at")
        or e.get("last_comparison_at")
        or e.get("last_business_quality_at")
        or e.get("last_execution_at")
    )
    mean_c = (touched / len(active)) if active else 0.0
    section_map["confidence_summary"] = [
        blk(
            f"Intelligence coverage {touched}/{len(active)} active entries (event-linked references only).",
            confidence=mean_c,
            kind="confidence",
        )
    ]

    refs = []
    for e in active:
        for r in e.get("research_refs") or []:
            if r.get("event_id"):
                refs.append(
                    evidence_reference(
                        str(r["event_id"]),
                        module=str(r.get("source") or "io-01"),
                        confidence=1.0,
                        ticker=e.get("ticker"),
                    )
                )
    section_map["evidence_references"] = [
        blk(
            f"{r.get('ticker')}: {r.get('evidence_id')} ← {r.get('module')}",
            module=str(r.get("module") or "WO-01"),
            eids=[r.get("evidence_id")],
            kind="reference",
        )
        for r in refs
    ] or [blk("No research event references yet.", confidence=0.0, kind="reference")]

    sections = []
    for i, key in enumerate(WQR_SECTIONS, start=1):
        sections.append(
            office_section(
                key,
                title=WQR_SECTION_TITLES.get(key, key),
                order=i,
                blocks=section_map.get(key) or [],
            )
        )

    assembly_ms = (time.perf_counter() - t0) * 1000.0
    metadata = office_metadata(
        office_id=WO01_OFFICE_ID,
        workstream_id=WO01_WORKSTREAM_ID,
        product=WO01_PRODUCT,
        version=WO01_VERSION,
        domain=DOMAIN_PORTFOLIO,
        role="research_queue_watchlist",
        orchestrates_only=True,
        buy_sell=False,
        valuation=False,
        recalculates=False,
        invents_conclusions=False,
        extras={"performs_research": False, "event_driven": True},
    )
    req = dict(request) if request else office_request(
        office_id=WO01_OFFICE_ID,
        intent="watchlist_queue",
        question=question,
        options={"watchlist_id": watchlist_id},
    )
    return office_response(
        metadata=metadata,
        request=req,
        report_type="watchlist_queue_report",
        sections=sections,
        confidence=confidence_summary(
            mean_confidence=mean_c,
            ok_count=touched,
            total=len(active),
        ),
        provenance=provenance_bundle(
            blocks=flatten_blocks(sections),
            references=refs,
            modules_invoked=["WO-01", "PEB-01"],
            modules_ok=["WO-01", "PEB-01"],
        ),
        routing={"intent": "watchlist_queue", "watchlist_id": wl.get("watchlist_id")},
        assembly_ms=assembly_ms,
        payload={
            "watchlist_id": wl.get("watchlist_id"),
            "watchlist": wl,
            "queue": queue,
            "recent_events": recent,
        },
        ok=True,
    )
