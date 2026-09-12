"""Knowledge Operations desk aggregate — control room payload."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from knowledge_operations.missing_inbox import build_missing_inbox
from knowledge_operations.schema import (
    CHECKLIST_ORDER,
    CLASS_LABELS,
    COLLECTOR_NAMES,
    KOC_PLATFORM,
    KOC_PRODUCT,
    KOC_SPEC,
    KOC_VERSION,
    KOC_WORKSTREAM_ID,
    MISSION,
    QUEUE_STAGES,
    UPLOAD_PIPELINE,
)
from knowledge_operations.upload import list_queue, list_uploads


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _soft(fn, default=None):
    try:
        return fn()
    except Exception as exc:
        if default is not None:
            return default
        return {"error": str(exc)[:160]}


def _company_rows(*, scope: str = "TOP20", deep: bool = False) -> List[Dict[str, Any]]:
    """Build coverage rows.

    Default (deep=False) uses ICF scores only — fast enough for the admin desk.
    deep=True also runs KIL integrate + research packs (slow; company detail path).
    """
    from institutional_coverage_factory.universe import top20_tickers, tier_for_ticker
    from institutional_coverage_factory.scorer.score import score_evidence_classes
    from institutional_coverage_factory.validator.icc import evaluate_icc
    from institutional_evidence.schema import PHASE1_TOP20

    names = {r["ticker"]: r["company"] for r in PHASE1_TOP20}
    tickers = top20_tickers()
    rows: List[Dict[str, Any]] = []
    for t in tickers:
        try:
            score = score_evidence_classes(t)
            icc = evaluate_icc(t, score=score)
            kc = None
            readiness = None
            claim_safe = None
            coverage_state = None
            classes_meta = score.get("classes") or {}
            evidence_count = sum(
                1 for meta in classes_meta.values() if (meta or {}).get("present")
            )
            last_updated = None
            if deep:
                try:
                    from institutional_evidence.integration.layer import integrate_company

                    kil = integrate_company(t, trigger_repair=False)
                    kc = (kil.get("knowledge_confidence") or {}).get("knowledge_confidence")
                    claim_safe = kil.get("claim_safe")
                    coverage_state = (kil.get("coverage_state") or {}).get("coverage_state")
                    readiness = 100.0 if kil.get("research_ready") else (
                        (kil.get("research_readiness") or {}).get("score")
                    )
                except Exception:
                    pass
                try:
                    from institutional_evidence.research_pack.builder import (
                        build_institutional_research_pack,
                    )

                    pack = build_institutional_research_pack(t)
                    reg = ((pack.get("evidence") or {}).get("registry") or {}).get("items") or []
                    evidence_count = len(reg)
                    claim_safe = pack.get("claim_safe") if claim_safe is None else claim_safe
                    rr = pack.get("research_readiness") or {}
                    if readiness is None:
                        readiness = rr.get("score") or (100.0 if pack.get("research_ready") else 0)
                    last_updated = pack.get("generated_at") or pack.get("as_of")
                except Exception:
                    pass

            classes = score.get("classes") or {}
            progress = {
                cid: (
                    "collected"
                    if (meta or {}).get("present")
                    else "missing"
                )
                for cid, meta in classes.items()
            }
            missing_labels = [
                CLASS_LABELS.get(c, c) for c in (score.get("missing_classes") or [])
            ]
            # Light mode: derive readiness proxies from coverage so KPIs are not empty.
            if not deep:
                cov = float(score.get("coverage_pct") or 0)
                readiness = cov if readiness is None else readiness
                claim_safe = bool(icc.get("institutional_coverage_complete")) if claim_safe is None else claim_safe
                kc = cov if kc is None else kc
            rows.append(
                {
                    "ticker": t,
                    "company": names.get(t, t),
                    "tier": tier_for_ticker(t),
                    "coverage_pct": score.get("coverage_pct"),
                    "knowledge_confidence": kc,
                    "research_readiness": readiness,
                    "claim_safe": bool(claim_safe) if claim_safe is not None else False,
                    "coverage_state": coverage_state or icc.get("status"),
                    "icc": bool(icc.get("institutional_coverage_complete")),
                    "last_updated": last_updated,
                    "evidence_count": evidence_count,
                    "missing_items": missing_labels,
                    "missing_classes": score.get("missing_classes"),
                    "progress": progress,
                    "status": icc.get("status"),
                    "deep": bool(deep),
                }
            )
        except Exception as exc:
            rows.append({"ticker": t, "company": names.get(t, t), "error": str(exc)[:160]})
    return rows


def _ingestion_timeline(limit: int = 20) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    try:
        from institutional_evidence.integration.events.bus import list_events

        listed = list_events(limit=limit)
        for e in listed.get("events") or listed.get("items") or []:
            events.append(
                {
                    "time": (e.get("emitted_at") or e.get("created_at") or "")[-8:][:5]
                    if e.get("emitted_at") or e.get("created_at")
                    else None,
                    "timestamp": e.get("emitted_at") or e.get("created_at"),
                    "ticker": e.get("ticker") or (e.get("companies") or [None])[0],
                    "event_type": e.get("event_type"),
                    "document_type": e.get("document_type") or e.get("phase") or "Knowledge",
                    "status": "Collected" if e.get("immutable") or e.get("ok", True) else "Failed",
                    "source": e.get("source") or "CGL",
                    "evidence_objects": e.get("evidence_added") or e.get("evidence_objects"),
                    "claims_extracted": e.get("claims_extracted") or e.get("claims"),
                    "knowledge_updated": True,
                    "research_invalidated": bool(e.get("research_invalidated")),
                    "raw": {k: e.get(k) for k in ("event_id", "run_id", "slot") if e.get(k)},
                }
            )
    except Exception:
        pass

    # Merge manual uploads into timeline
    ups = list_uploads(limit=limit).get("uploads") or []
    for u in ups:
        ts = u.get("uploaded_at") or ""
        events.append(
            {
                "time": ts[11:16] if len(ts) >= 16 else None,
                "timestamp": ts,
                "ticker": u.get("ticker"),
                "event_type": "ManualUpload",
                "document_type": u.get("document_type"),
                "status": "Collected",
                "source": "Manual Upload",
                "evidence_objects": len(u.get("evidence_ids") or []),
                "claims_extracted": None,
                "knowledge_updated": True,
                "research_invalidated": False,
                "filename": u.get("filename"),
            }
        )

    events.sort(key=lambda e: e.get("timestamp") or "", reverse=True)
    return events[:limit]


def _daily_summary(rows: List[Dict[str, Any]], timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
    missing_counts: Dict[str, int] = {}
    for r in rows:
        for c in r.get("missing_classes") or []:
            missing_counts[c] = missing_counts.get(c, 0) + 1

    snap = _soft(lambda: __import__(
        "institutional_evidence.integration.versioning.snapshots", fromlist=["get_latest_snapshot"]
    ).get_latest_snapshot())
    if isinstance(snap, dict) and snap.get("error"):
        snap = None

    uploads_today = list_uploads(limit=200).get("uploads") or []
    return {
        "companies_updated": len([r for r in rows if (r.get("evidence_count") or 0) > 0]),
        "documents_downloaded": len(timeline) + len(uploads_today),
        "evidence_objects_added": sum(int(e.get("evidence_objects") or 0) for e in timeline),
        "financial_statements_parsed": len(rows) - missing_counts.get("financial_statements", 0),
        "annual_reports": len(rows) - missing_counts.get("annual_reports", 0),
        "quarterly_results": len(rows) - missing_counts.get("quarterly_results", 0),
        "investor_presentations": len(rows) - missing_counts.get("earnings_presentations", 0),
        "transcripts": len(rows) - missing_counts.get("earnings_call_transcripts", 0),
        "shareholding_files": len(rows) - missing_counts.get("shareholding", 0),
        "corporate_actions": len(rows) - missing_counts.get("corporate_actions", 0),
        "management_guidance": len(rows) - missing_counts.get("management_guidance", 0),
        "segment_kpis": len(rows) - missing_counts.get("segment_kpis", 0),
        "macro_updates": None,
        "news_events": None,
        "knowledge_graph_updates": len(rows) - missing_counts.get("knowledge_graph", 0),
        "company_memory_refreshes": len(rows) - missing_counts.get("company_memory", 0),
        "research_pack_refreshes": sum(1 for r in rows if r.get("research_readiness")),
        "knowledge_version_created": (snap or {}).get("knowledge_version") if isinstance(snap, dict) else None,
        "missing_counts": missing_counts,
    }


def _collector_health() -> List[Dict[str, Any]]:
    cgl = _soft(
        lambda: __import__(
            "continuous_gather_learn.production", fromlist=["dashboard"]
        ).dashboard()
    )
    success = None
    latest = None
    degraded_n = 0
    if isinstance(cgl, dict):
        success = cgl.get("collector_success_rate")
        latest = cgl.get("latest_run") or {}
        ops = cgl.get("ops") or {}
        if isinstance(ops, dict) and isinstance(ops.get("degraded_collectors"), int):
            degraded_n = ops["degraded_collectors"]
    out = []
    for idx, name in enumerate(COLLECTOR_NAMES):
        # Soft: mark first N as degraded when CGL reports degraded collectors
        is_degraded = success is not None and (
            float(success) < 90 or (degraded_n > 0 and idx < degraded_n)
        )
        health = (
            "Healthy"
            if success is not None and not is_degraded and float(success) >= 90
            else ("Warning" if success is not None else "Unknown")
        )
        if is_degraded:
            health = "Warning"
        out.append(
            {
                "collector": name,
                "health": health,
                "latency_ms": (latest or {}).get("latency_ms") if isinstance(latest, dict) else None,
                "success_rate": success,
                "failures": (latest or {}).get("volumes", {}).get("collectors_failed")
                if isinstance(latest, dict)
                else None,
                "last_success": (latest or {}).get("generated_at") if isinstance(latest, dict) else None,
                "next_run": None,
                "retry_available": True,
            }
        )
    return out


def _heatmap(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    def band(vals: List[float]) -> Optional[float]:
        return round(sum(vals) / len(vals), 1) if vals else None

    cov = [float(r["coverage_pct"]) for r in rows if r.get("coverage_pct") is not None]
    kc = [
        float(r["knowledge_confidence"])
        for r in rows
        if isinstance(r.get("knowledge_confidence"), (int, float))
    ]
    rr = [
        float(r["research_readiness"])
        for r in rows
        if isinstance(r.get("research_readiness"), (int, float))
    ]
    return {
        "TOP20": {
            "coverage_pct": band(cov),
            "knowledge_confidence": band(kc),
            "research_ready": band(rr),
            "claim_safe_pct": round(
                100.0 * sum(1 for r in rows if r.get("claim_safe")) / max(1, len(rows)), 1
            ),
            "icc_complete": sum(1 for r in rows if r.get("icc")),
            "companies": len(rows),
        },
        "NIFTY50": {"note": "Expand scope via ?scope=NIFTY50"},
        "NIFTY100": {"note": "Expand scope via ?scope=NIFTY100"},
        "NIFTY500": {"note": "Gated until Top-20 ICC"},
    }


def build_desk(*, scope: str = "TOP20", deep: bool = False) -> Dict[str, Any]:
    rows = _company_rows(scope=scope, deep=deep)
    timeline = _ingestion_timeline(24)
    inbox = build_missing_inbox(scope=scope, limit=40)
    summary = _daily_summary(rows, timeline)
    queue = list_queue(limit=50)
    collectors = _collector_health()

    icc_n = sum(1 for r in rows if r.get("icc"))
    research_ready_n = sum(
        1 for r in rows if (r.get("research_readiness") or 0) >= 70 or r.get("claim_safe")
    )
    knowledge_ready_n = sum(
        1
        for r in rows
        if (r.get("coverage_state") or "")
        in {"KNOWLEDGE READY", "RESEARCH READY", "INSTITUTIONAL COVERAGE COMPLETE", "CONTINUOUS MONITORING"}
        or (r.get("coverage_pct") or 0) >= 50
    )
    kc_vals = [
        float(r["knowledge_confidence"])
        for r in rows
        if isinstance(r.get("knowledge_confidence"), (int, float))
    ]
    evidence_objects = sum(int(r.get("evidence_count") or 0) for r in rows)

    cgl = _soft(
        lambda: __import__(
            "continuous_gather_learn.production", fromlist=["dashboard"]
        ).dashboard()
    )
    sch = _soft(
        lambda: __import__(
            "institutional_coverage_factory.production", fromlist=["scheduler_status"]
        ).scheduler_status()
    )
    collector_success = cgl.get("collector_success_rate") if isinstance(cgl, dict) else None

    # Knowledge versions
    versions = []
    try:
        from institutional_evidence.integration.versioning.snapshots import list_snapshots

        snap_list = list_snapshots(limit=20)
        versions = snap_list.get("snapshots") or snap_list.get("items") or []
    except Exception:
        try:
            from institutional_evidence.integration.versioning.snapshots import get_latest_snapshot

            latest = get_latest_snapshot()
            if latest:
                versions = [latest]
        except Exception:
            pass

    from knowledge_operations.system_health import build_system_health
    from knowledge_operations.gap_ai import analyze_gaps
    from knowledge_operations.flags import is_koc_enabled

    system_health = build_system_health()
    gap_ai = analyze_gaps(scope=scope, limit=20)
    claim_safe_n = sum(1 for r in rows if r.get("claim_safe"))
    bar = system_health.get("bar") or {}

    # Enrich queue stages with repair backlog from CGL
    stage_counts = dict((queue or {}).get("stages") or {})
    if isinstance(cgl, dict):
        ops = cgl.get("ops") or {}
        if isinstance(ops, dict) and ops.get("repair_queue") is not None:
            stage_counts["Repair Queue"] = ops.get("repair_queue")
    queue_enriched = {
        **(queue or {}),
        "stages": stage_counts,
        "boards": [
            {
                "stage": s,
                "count": int(stage_counts.get(s) or 0),
                "oldest_item": None,
                "eta_minutes": None,
                "retry_available": True,
            }
            for s in QUEUE_STAGES
        ],
    }

    return {
        "ok": True,
        "workstream_id": KOC_WORKSTREAM_ID,
        "product": KOC_PRODUCT,
        "platform": KOC_PLATFORM,
        "version": KOC_VERSION,
        "spec": KOC_SPEC,
        "mission": MISSION,
        "generated_at": _now(),
        "scope": scope,
        "deep": bool(deep),
        "system_health": system_health,
        "kpis": {
            "companies_covered": len([r for r in rows if (r.get("evidence_count") or 0) > 0]),
            "companies_scoped": len(rows),
            "institutional_coverage_complete": icc_n,
            "claim_safe": claim_safe_n,
            "research_ready": research_ready_n,
            "knowledge_ready": knowledge_ready_n,
            "knowledge_confidence": round(sum(kc_vals) / len(kc_vals), 1) if kc_vals else None,
            "evidence_objects": evidence_objects,
            "documents_collected_today": len(timeline),
            "documents_processed_today": len(timeline),
            "claims_extracted_today": sum(int(e.get("claims_extracted") or 0) for e in timeline),
            "claims_created_today": sum(int(e.get("claims_extracted") or 0) for e in timeline),
            "knowledge_snapshots": len(versions),
            "company_memory_updates": summary.get("company_memory_refreshes"),
            "knowledge_graph_updates": summary.get("knowledge_graph_updates"),
            "research_refreshes": summary.get("research_pack_refreshes"),
            "research_invalidations": sum(1 for e in timeline if e.get("research_invalidated")),
            "research_invalidated_today": sum(
                1 for e in timeline if e.get("research_invalidated")
            ),
            "collector_success_pct": collector_success,
            "collector_health": (
                "Healthy"
                if collector_success is not None and float(collector_success) >= 90
                else ("Warning" if collector_success is not None else "Unknown")
            ),
            "scheduler_status": (bar.get("scheduler") or {}).get("status"),
            "scheduler_detail": sch if isinstance(sch, dict) else None,
            "knowledge_latency": (bar.get("knowledge_latency_minutes")),
            "cgl_status": (bar.get("cgl") or {}).get("status"),
            "kil_status": (bar.get("kil") or {}).get("status"),
            "icf_status": (bar.get("icf") or {}).get("status"),
            "koc_status": (bar.get("koc") or {}).get("status")
            or ("Running" if is_koc_enabled() else "Disabled"),
            "icc_entered_today": (sch or {}).get("icc_entered_today")
            if isinstance(sch, dict)
            else None,
            "repair_queue": bar.get("repair_queue"),
        },
        "missing_inbox": inbox,
        "gap_ai": gap_ai,
        "ingestion_timeline": timeline,
        "daily_summary": summary,
        "coverage_table": rows,
        "knowledge_queue": queue_enriched,
        "queue_stages": list(QUEUE_STAGES),
        "collector_health": collectors,
        "coverage_heatmap": _heatmap(rows),
        "knowledge_versions": versions,
        "upload_pipeline": list(UPLOAD_PIPELINE),
        "actions": [
            "run_cgl",
            "bootstrap_universe_learning",
            "learn_universe",
            "rebuild_structured_tables",
            "onboard_universe_tables",
            "run_kil",
            "run_full_coverage",
            "run_research_refresh",
            "run_company_memory_refresh",
            "rebuild_knowledge_graph",
            "run_auto_repair",
            "run_knowledge_validation",
            "run_coverage_scan",
            "run_institutional_coverage_check",
            "run_top20_audit",
        ],
        "security": {
            "admin_only": True,
            "audit_required": True,
            "evidence_immutable": True,
            "never_overwrite": True,
            "rollback_available": False,
            "nothing_permanently_deleted": True,
        },
    }


def company_detail(ticker: str) -> Dict[str, Any]:
    t = str(ticker or "").upper().strip()
    rows = _company_rows()
    row = next((r for r in rows if r.get("ticker") == t), None)
    inbox = build_missing_inbox(scope="TOP20", limit=100)
    company_gaps = [i for i in (inbox.get("items") or []) if i.get("ticker") == t]
    pack = _soft(
        lambda: __import__(
            "institutional_evidence.research_pack.builder",
            fromlist=["build_institutional_research_pack"],
        ).build_institutional_research_pack(t)
    )
    progress = dict((row or {}).get("progress") or {})
    # Expand checklist with registry / research pack / optional types
    if isinstance(pack, dict):
        reg = ((pack.get("evidence") or {}).get("registry") or {}).get("items") or []
        progress["evidence_registry"] = "collected" if len(reg) >= 2 else "missing"
        progress["research_pack"] = (
            "collected" if pack.get("research_ready") or pack.get("claim_safe") else "missing"
        )
        dtypes = {str(i.get("document_type") or "") for i in reg}
        if "credit_rating" in dtypes or "credit_ratings" in dtypes:
            progress["credit_rating"] = "collected"
        else:
            progress.setdefault("credit_rating", "missing")
        if "investor_day" in dtypes:
            progress["investor_day"] = "collected"
        else:
            progress.setdefault("investor_day", "missing")

    checklist = []
    for key in CHECKLIST_ORDER:
        state = progress.get(key) or "missing"
        checklist.append(
            {
                "id": key,
                "label": CLASS_LABELS.get(key, key.replace("_", " ").title()),
                "state": state,
            }
        )

    graph = _soft(
        lambda: __import__(
            "institutional_evidence.production", fromlist=["get_evidence_graph"]
        ).get_evidence_graph(t)
    )

    return {
        "ok": True,
        "ticker": t,
        "company": (row or {}).get("company") or t,
        "row": row,
        "missing_inbox": company_gaps,
        "progress": progress,
        "checklist": checklist,
        "coverage_pct": (row or {}).get("coverage_pct"),
        "knowledge_confidence": (row or {}).get("knowledge_confidence"),
        "research_readiness": (row or {}).get("research_readiness"),
        "claim_safe": (row or {}).get("claim_safe"),
        "icc": (row or {}).get("icc"),
        "knowledge_graph": graph if isinstance(graph, dict) else None,
        "pack_summary": {
            "research_ready": (pack or {}).get("research_ready") if isinstance(pack, dict) else None,
            "claim_safe": (pack or {}).get("claim_safe") if isinstance(pack, dict) else None,
            "evidence_count": len(
                (((pack or {}).get("evidence") or {}).get("registry") or {}).get("items") or []
            )
            if isinstance(pack, dict)
            else 0,
        },
    }

