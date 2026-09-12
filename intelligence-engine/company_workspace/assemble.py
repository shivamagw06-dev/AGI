"""Assemble Company Workspace from existing modules — presentation only."""

from __future__ import annotations

import time
from typing import Any, Mapping, Optional, Sequence

from company_workspace.collectors import (
    collect_module,
    collect_portfolios,
    collect_research,
    collect_watchlists,
    profile_stub,
)
from company_workspace.schema import (
    CW01_DOMAIN,
    CW01_PRODUCT,
    CW01_RECOMMENDATION_POLICY,
    CW01_REPORT_TYPE,
    CW01_ROLE,
    CW01_SPEC,
    CW01_SURFACE_ID,
    CW01_VERSION,
    CW01_WORKSTREAM_ID,
    SECTION_SOURCES,
    WORKSPACE_SECTIONS,
)
from company_workspace import store as cw_store
from office_sdk.contracts import (
    SCHEMA_RESPONSE,
    confidence_summary,
    evidence_block,
    evidence_reference,
    office_metadata,
    office_request,
    office_response,
    office_section,
    provenance_bundle,
)


def _conf_of(payload: Mapping[str, Any]) -> float:
    if not isinstance(payload, Mapping):
        return 0.0
    for key in ("confidence", "mean_confidence", "quality_confidence"):
        v = payload.get(key)
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, Mapping) and isinstance(v.get("mean_confidence"), (int, float)):
            return float(v["mean_confidence"])
    return 0.0


def _evidence_ids(payload: Mapping[str, Any]) -> list[str]:
    ids: list[str] = []
    if not isinstance(payload, Mapping):
        return ids
    for key in ("evidence_ids", "evidence_references", "references"):
        raw = payload.get(key)
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, str) and item.strip():
                    ids.append(item.strip())
                elif isinstance(item, Mapping):
                    eid = item.get("evidence_id") or item.get("id")
                    if eid:
                        ids.append(str(eid))
    return ids[:40]


def _section_from_module(
    key: str,
    *,
    title: str,
    order: int,
    collected: Mapping[str, Any],
    ticker: str,
) -> dict[str, Any]:
    mod = str(collected.get("module") or SECTION_SOURCES.get(key) or key)
    payload = collected.get("payload") if isinstance(collected.get("payload"), Mapping) else {}
    available = bool(collected.get("available"))
    conf = _conf_of(payload) if available else 0.0
    eids = _evidence_ids(payload) if available else []
    if available:
        text = f"{title} for {ticker} — pass-through from {mod} (source={collected.get('source')})."
    else:
        text = (
            f"{title} for {ticker} — no cached intelligence from {mod}. "
            "Workspace does not run analysis."
        )
    block = evidence_block(
        text,
        module=mod,
        evidence_ids=eids,
        confidence=conf,
        tickers=[ticker],
        kind="presentation",
        extras={
            "available": available,
            "source": collected.get("source"),
            "reason": collected.get("reason"),
        },
    )
    return office_section(
        key,
        title=title,
        order=order,
        blocks=[block],
        board={
            "available": available,
            "module": mod,
            "source": collected.get("source"),
            "payload": dict(payload) if available else {},
            "error": collected.get("error"),
        },
    )


def assemble_workspace(
    ticker: str,
    *,
    profile: Optional[Mapping[str, Any]] = None,
    prebuilt: Optional[Mapping[str, Mapping[str, Any]]] = None,
    question: Optional[str] = None,
    section_filter: Optional[Sequence[str]] = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Build a Company Workspace OfficeResponse for one ticker."""
    t0 = time.perf_counter()
    t = str(ticker or "").strip().upper()
    if not t:
        return office_response(
            metadata=office_metadata(
                office_id=CW01_SURFACE_ID,
                workstream_id=CW01_WORKSTREAM_ID,
                product=CW01_PRODUCT,
                version=CW01_VERSION,
                domain=CW01_DOMAIN,
                role=CW01_ROLE,
                orchestrates_only=True,
                buy_sell=False,
                valuation=False,
                recalculates=False,
                invents_conclusions=False,
                extras={"not_an_office": True, "not_an_engine": True},
            ),
            report_type=CW01_REPORT_TYPE,
            ok=False,
            error="ticker required",
        )

    if use_cache:
        cached = cw_store.get_workspace(t)
        if cached and not prebuilt and not profile:
            return cached

    # Persist any prebuilt modules into cache for subsequent event-driven refreshes
    if prebuilt:
        cw_store.put_module_cache(t, dict(prebuilt))

    prof = profile_stub(t, profile=profile)
    fire01 = collect_module(t, "FIRE-01", prebuilt=prebuilt)
    fire02 = collect_module(t, "FIRE-02", prebuilt=prebuilt)
    fire03 = collect_module(t, "FIRE-03", prebuilt=prebuilt)
    fire04 = collect_module(t, "FIRE-04", prebuilt=prebuilt)
    fire05 = collect_module(t, "FIRE-05", prebuilt=prebuilt)
    fire06 = collect_module(t, "FIRE-06", prebuilt=prebuilt)
    watch = collect_watchlists(t)
    ports = collect_portfolios(t)
    research = collect_research(t)

    # Cache available module payloads for timeline / future refreshes
    to_cache: dict[str, dict[str, Any]] = {}
    for label, coll in (
        ("FIRE-01", fire01),
        ("FIRE-02", fire02),
        ("FIRE-03", fire03),
        ("FIRE-04", fire04),
        ("FIRE-05", fire05),
        ("FIRE-06", fire06),
    ):
        if coll.get("available") and isinstance(coll.get("payload"), Mapping):
            to_cache[label] = dict(coll["payload"])
            cw_store.record_coverage(hit=True)
        else:
            cw_store.record_coverage(hit=False)
    if to_cache:
        cw_store.put_module_cache(t, to_cache)

    modules_ok = [m for m, c in (
        ("FIRE-01", fire01),
        ("FIRE-02", fire02),
        ("FIRE-03", fire03),
        ("FIRE-04", fire04),
        ("FIRE-05", fire05),
        ("FIRE-06", fire06),
        ("WO-01", watch),
        ("PO-01", ports),
        ("IO-01", research),
    ) if c.get("available")]
    modules_invoked = ["FIRE-01", "FIRE-02", "FIRE-03", "FIRE-04", "FIRE-05", "FIRE-06", "WO-01", "PO-01", "IO-01"]

    conf_rows = []
    confs: list[float] = []
    for mod, coll in (
        ("FIRE-01", fire01),
        ("FIRE-02", fire02),
        ("FIRE-03", fire03),
        ("FIRE-04", fire04),
        ("FIRE-05", fire05),
        ("FIRE-06", fire06),
    ):
        c = _conf_of(coll.get("payload") or {}) if coll.get("available") else 0.0
        conf_rows.append({"module": mod, "confidence": c, "available": bool(coll.get("available"))})
        if coll.get("available"):
            confs.append(c)
    mean_c = sum(confs) / len(confs) if confs else 0.0

    coverage = {
        "modules_available": len(modules_ok),
        "modules_total": len(modules_invoked),
        "ratio": round(len(modules_ok) / len(modules_invoked), 4) if modules_invoked else 0.0,
        "by_module": {m: (m in modules_ok) for m in modules_invoked},
    }

    research_status = "No research on file"
    if research.get("available"):
        latest = research.get("latest") or {}
        research_status = str(latest.get("package_type") or latest.get("status") or "Research available")

    overview_board = {
        "company": prof.get("company"),
        "ticker": t,
        "sector": prof.get("sector"),
        "industry": prof.get("industry"),
        "exchange": prof.get("exchange"),
        "current_research_status": research_status,
        "last_updated": (research.get("latest") or {}).get("recorded_at"),
        "coverage": coverage,
        "confidence": round(mean_c, 4),
    }

    timeline_rows = cw_store.list_timeline(t, limit=100)
    # Seed timeline from available module timestamps when empty
    if not timeline_rows:
        for mod, coll in (
            ("FIRE-06", fire06),
            ("FIRE-05", fire05),
            ("FIRE-01", fire01),
            ("IO-01", research),
        ):
            if not coll.get("available"):
                continue
            payload = coll.get("payload") if isinstance(coll.get("payload"), Mapping) else {}
            at = None
            if isinstance(payload, Mapping):
                at = payload.get("as_of") or payload.get("updated_at") or payload.get("recorded_at")
            if mod == "IO-01" and research.get("latest"):
                at = (research["latest"] or {}).get("recorded_at")
            cw_store.append_timeline(
                t,
                {
                    "at": at,
                    "event_type": f"{mod.lower().replace('-', '_')}.present",
                    "source": mod,
                    "summary": f"{mod} intelligence present in workspace",
                    "payload": {"available": True},
                },
            )
        timeline_rows = cw_store.list_timeline(t, limit=100)

    outstanding: list[str] = []
    for mod, coll in (
        ("FIRE-01", fire01),
        ("FIRE-02", fire02),
        ("FIRE-03", fire03),
        ("FIRE-04", fire04),
        ("FIRE-05", fire05),
        ("FIRE-06", fire06),
    ):
        if not coll.get("available"):
            outstanding.append(f"Awaiting cached {mod} intelligence")
    if not research.get("available"):
        outstanding.append("No Institutional Research Package on file")

    # Evidence references (preserved, never rewritten)
    refs: list[dict[str, Any]] = []
    for mod, coll in (
        ("FIRE-01", fire01),
        ("FIRE-02", fire02),
        ("FIRE-03", fire03),
        ("FIRE-04", fire04),
        ("FIRE-05", fire05),
        ("FIRE-06", fire06),
    ):
        if not coll.get("available"):
            continue
        for eid in _evidence_ids(coll.get("payload") or {}):
            refs.append(
                evidence_reference(
                    eid,
                    module=mod,
                    confidence=_conf_of(coll.get("payload") or {}),
                    ticker=t,
                    source=str(coll.get("source") or ""),
                )
            )

    sections = [
        office_section(
            "overview",
            title="Overview",
            order=1,
            blocks=[
                evidence_block(
                    f"{prof.get('company') or t} ({t}) — coverage {coverage['ratio']:.0%}, "
                    f"confidence {mean_c:.2f}, research: {research_status}.",
                    module="CW-01",
                    confidence=mean_c,
                    tickers=[t],
                    kind="overview",
                )
            ],
            board=overview_board,
        ),
        office_section(
            "company_profile",
            title="Company Profile",
            order=2,
            blocks=[
                evidence_block(
                    f"Profile stub for {t}: sector={prof.get('sector')}, "
                    f"industry={prof.get('industry')}, exchange={prof.get('exchange')}.",
                    module="CW-01",
                    tickers=[t],
                    kind="profile",
                )
            ],
            board=prof,
        ),
        _section_from_module(
            "business_quality", title="Business Quality", order=3, collected=fire06, ticker=t
        ),
        _section_from_module(
            "financial_trends", title="Financial Trends", order=4, collected=fire01, ticker=t
        ),
        _section_from_module(
            "financial_relationships",
            title="Financial Relationships",
            order=5,
            collected=fire02,
            ticker=t,
        ),
        _section_from_module(
            "management_execution",
            title="Management Execution",
            order=6,
            collected=fire05,
            ticker=t,
        ),
        _section_from_module(
            "evidence_alignment",
            title="Evidence Alignment",
            order=7,
            collected=fire04,
            ticker=t,
        ),
        _section_from_module(
            "business_strategy",
            title="Business Strategy",
            order=8,
            collected=fire03,
            ticker=t,
        ),
        office_section(
            "historical_timeline",
            title="Historical Timeline",
            order=9,
            blocks=[
                evidence_block(
                    f"Unified timeline for {t}: {len(timeline_rows)} events.",
                    module="CW-01",
                    tickers=[t],
                    kind="timeline",
                )
            ],
            board={"events": timeline_rows, "count": len(timeline_rows)},
        ),
        office_section(
            "research_notes",
            title="Research Notes",
            order=10,
            blocks=[
                evidence_block(
                    f"Research history for {t}: {research.get('count') or 0} package(s).",
                    module="IO-01",
                    tickers=[t],
                    kind="research",
                )
            ],
            board={
                "institutional_research_package": research.get("latest"),
                "latest_research_note": research.get("latest"),
                "research_history": research.get("history") or [],
            },
        ),
        office_section(
            "watchlist_status",
            title="Watchlist Status",
            order=11,
            blocks=[
                evidence_block(
                    f"Watchlist memberships for {t}: {watch.get('count') or 0}.",
                    module="WO-01",
                    tickers=[t],
                    kind="watchlist",
                )
            ],
            board={"watchlists": watch.get("entries") or [], "count": watch.get("count") or 0},
        ),
        office_section(
            "portfolio_references",
            title="Portfolio References",
            order=12,
            blocks=[
                evidence_block(
                    f"Portfolio memberships for {t}: {ports.get('count') or 0}.",
                    module="PO-01",
                    tickers=[t],
                    kind="portfolio",
                )
            ],
            board={
                "memberships": ports.get("memberships") or [],
                "count": ports.get("count") or 0,
            },
        ),
        office_section(
            "recent_events",
            title="Recent Events",
            order=13,
            blocks=[
                evidence_block(
                    f"Recent PEB/workspace events for {t}: {len(timeline_rows[-10:])}.",
                    module="PEB-01",
                    tickers=[t],
                    kind="events",
                )
            ],
            board={"events": timeline_rows[-10:], "count": len(timeline_rows[-10:])},
        ),
        office_section(
            "outstanding_questions",
            title="Outstanding Questions",
            order=14,
            blocks=[
                evidence_block(
                    "; ".join(outstanding) if outstanding else f"No coverage gaps recorded for {t}.",
                    module="CW-01",
                    tickers=[t],
                    kind="questions",
                )
            ],
            board={"questions": outstanding},
        ),
        office_section(
            "confidence_summary",
            title="Confidence Summary",
            order=15,
            blocks=[
                evidence_block(
                    f"Mean confidence {mean_c:.2f} across {len(confs)} available FIRE modules.",
                    module="CW-01",
                    confidence=mean_c,
                    tickers=[t],
                    kind="confidence",
                )
            ],
            board=confidence_summary(
                mean_confidence=mean_c,
                by_module=conf_rows,
                ok_count=len(modules_ok),
                total=len(modules_invoked),
            ),
        ),
        office_section(
            "evidence_references",
            title="Evidence References",
            order=16,
            blocks=[
                evidence_block(
                    f"{len(refs)} evidence reference(s) preserved for {t}.",
                    module="CW-01",
                    evidence_ids=[r["evidence_id"] for r in refs],
                    tickers=[t],
                    kind="evidence",
                )
            ],
            board={"references": refs, "count": len(refs)},
        ),
    ]

    if section_filter:
        allow = {str(s).strip().lower() for s in section_filter if str(s).strip()}
        sections = [s for s in sections if str(s.get("key") or "").lower() in allow]

    req = office_request(
        office_id=CW01_SURFACE_ID,
        intent="workspace",
        tickers=[t],
        question=question,
        modules=modules_invoked,
        options={"presentation_only": True, "sections": list(WORKSPACE_SECTIONS)},
    )
    meta = office_metadata(
        office_id=CW01_SURFACE_ID,
        workstream_id=CW01_WORKSTREAM_ID,
        product=CW01_PRODUCT,
        version=CW01_VERSION,
        domain=CW01_DOMAIN,
        role=CW01_ROLE,
        orchestrates_only=True,
        buy_sell=False,
        valuation=False,
        recalculates=False,
        invents_conclusions=False,
        extras={
            "not_an_office": True,
            "not_an_engine": True,
            "recommendation_policy": CW01_RECOMMENDATION_POLICY,
            "spec": CW01_SPEC,
        },
    )
    ms = (time.perf_counter() - t0) * 1000.0
    blocks_n = sum(len(s.get("blocks") or []) for s in sections)
    cw_store.record_coverage(hit=True, evidence_blocks=blocks_n)

    resp = office_response(
        metadata=meta,
        request=req,
        report_type=CW01_REPORT_TYPE,
        sections=sections,
        confidence=confidence_summary(
            mean_confidence=mean_c,
            by_module=conf_rows,
            ok_count=len(modules_ok),
            total=len(modules_invoked),
        ),
        provenance=provenance_bundle(
            blocks=[b for s in sections for b in (s.get("blocks") or [])],
            references=refs,
            modules_invoked=modules_invoked,
            modules_ok=modules_ok,
        ),
        routing={
            "surface": CW01_SURFACE_ID,
            "section_sources": dict(SECTION_SOURCES),
            "presentation_only": True,
            "runs_fire": False,
            "creates_buy_sell": False,
        },
        assembly_ms=ms,
        payload={
            "ticker": t,
            "overview": overview_board,
            "profile": prof,
            "coverage": coverage,
            "watchlists": watch.get("entries") or [],
            "portfolios": ports.get("memberships") or [],
            "research": research,
            "timeline": timeline_rows,
            "outstanding_questions": outstanding,
        },
        ok=True,
    )
    assert resp.get("schema") == SCHEMA_RESPONSE
    cw_store.put_workspace(t, resp)
    return resp
