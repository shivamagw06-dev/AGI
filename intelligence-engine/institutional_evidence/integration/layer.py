"""Knowledge Integration Layer — owns CGL → canonical → IEP integration."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .schema import (
    KIL_PHASE1_DEMO,
    KIL_PRODUCT,
    KIL_SPEC,
    KIL_VERSION,
    KIL_WORKSTREAM_ID,
    MISSION_STATEMENT,
)
from .events.bus import emit_cgl_events
from .transform.kf_to_canonical import transform_company_knowledge
from .versioning.snapshots import create_knowledge_snapshot, get_latest_snapshot
from .confidence.score import compute_knowledge_confidence
from .coverage_states.states import compute_coverage_state
from . import persist as kil_persist


# In-process company integration cache (hydrated from / mirrored to disk)
_COMPANY_STATE: Dict[str, Dict[str, Any]] = {}


def _companies_integrated_count() -> int:
    n_mem = len(_COMPANY_STATE)
    try:
        n_disk = kil_persist.company_count()
    except Exception:
        n_disk = 0
    return max(n_mem, n_disk)


def _cgl_kil_signal() -> Dict[str, Any]:
    """Read gather-side KIL outcome from shared CGL latest_run + heartbeats."""
    out: Dict[str, Any] = {
        "gather_sidecar_fresh": False,
        "latest_run_kil_ok": None,
        "latest_run_id": None,
        "knowledge_version": None,
    }
    try:
        from continuous_gather_learn import persist as cgl_persist

        hb = cgl_persist.read_gather_heartbeat()
        out["gather_sidecar_fresh"] = bool(hb.get("fresh"))
        run = cgl_persist.get_latest_run() or {}
        out["latest_run_id"] = run.get("run_id")
        kil = run.get("kil_integration") if isinstance(run.get("kil_integration"), dict) else {}
        if kil:
            out["latest_run_kil_ok"] = bool(kil.get("ok"))
            out["knowledge_version"] = kil.get("knowledge_version") or (
                (kil.get("summary") or {}).get("knowledge_version")
            )
    except Exception as exc:
        out["cgl_error"] = str(exc)[:160]
    try:
        out["kil_heartbeat"] = kil_persist.read_integration_heartbeat()
    except Exception:
        out["kil_heartbeat"] = {"fresh": False, "present": False}
    return out


def kil_status() -> Dict[str, Any]:
    snap = get_latest_snapshot()
    signal = _cgl_kil_signal()
    n = _companies_integrated_count()
    hb = signal.get("kil_heartbeat") or {}
    effective = bool(
        n > 0
        or snap
        or signal.get("latest_run_kil_ok")
        or hb.get("fresh")
        or signal.get("gather_sidecar_fresh")
    )
    # Mission Control agent_map probes health()/status — "ok" => working.
    if n > 0 or snap or signal.get("latest_run_kil_ok") or hb.get("fresh"):
        status = "ok"
    elif signal.get("gather_sidecar_fresh"):
        status = "ok"  # gather alive; integration soft-wired after each CGL cycle
    else:
        status = "ok"  # module live; empty state until first integrate
    return {
        "ok": True,
        "status": status,
        "enabled": True,
        "workstream_id": KIL_WORKSTREAM_ID,
        "product": KIL_PRODUCT,
        "version": KIL_VERSION,
        "spec": KIL_SPEC,
        "mission": MISSION_STATEMENT,
        "pipeline": [
            "External Providers",
            "Continuous Gather → Learn",
            "Knowledge Integration Layer",
            "Canonical Evidence",
            "Evidence Registry",
            "Company Memory",
            "Knowledge Graph",
            "Financial Intelligence",
            "Decision Eligibility",
            "Research Pack",
            "Research Writer",
            "Publishing",
        ],
        "rule": "There must never be two knowledge systems — one institutional knowledge pipeline",
        "phase1_demo": list(KIL_PHASE1_DEMO),
        "companies_integrated": n,
        "latest_snapshot": snap,
        "effective_integration": effective,
        "gather_sidecar_fresh": bool(signal.get("gather_sidecar_fresh")),
        "latest_run_kil_ok": signal.get("latest_run_kil_ok"),
        "latest_run_id": signal.get("latest_run_id"),
        "kil_heartbeat": hb,
        "store_root": str(kil_persist.store_root()),
        "note": (
            "KIL runs after each CGL cycle (gather sidecar). State is persisted so "
            "HTTP Mission Control can see companies_integrated / snapshots."
        ),
    }


def health() -> Dict[str, Any]:
    """Agent-map / ops health probe — must exist as health() (not only kil_status)."""
    return kil_status()


def _publish_canonical_to_registry(ticker: str, transformed: Dict[str, Any]) -> Dict[str, Any]:
    """Publish transformed knowledge into IEP acquisition/registry plane."""
    from ..acquisition.collector import acquire_company_documents
    from ..registry.store import register_documents
    from ..governance.layer0 import govern_inbound_dataset
    from ..entity.resolve import entity_id_for_ticker
    import hashlib

    t = ticker.upper()
    eid = entity_id_for_ticker(t)
    fin = (transformed.get("models") or {}).get("CanonicalFinancialStatements") or {}
    docs = []

    # Synthetic governed documents pointing at KIL-published canonical knowledge
    for dtype, payload in (
        ("quarterly_results", {"periods": fin.get("periods"), "period_count": fin.get("period_count")}),
        ("annual_report", {"annuals": [p for p in (fin.get("periods") or []) if p.get("period_type") == "annual"]}),
    ):
        if not payload.get("periods") and not payload.get("annuals"):
            continue
        blob = f"kil|{t}|{dtype}|{fin.get('period_count')}"
        h = hashlib.sha256(blob.encode()).hexdigest()
        gov = govern_inbound_dataset(
            {"hash": h, "version": 1},
            provider_id="knowledge_integration_layer",
            document_type=dtype,
            entity_id=eid,
        )
        docs.append(
            {
                "document_id": f"doc_kil_{h[:12]}",
                "company": transformed.get("company") or t,
                "ticker": t,
                "entity_id": eid,
                "document_type": dtype,
                "source": "knowledge_integration_layer",
                "hash": h,
                "checksum": h,
                "published_at": gov.get("governance", {}).get("admitted_at"),
                "downloaded_at": gov.get("governance", {}).get("admitted_at"),
                "status": "published_canonical",
                "governance": gov.get("governance"),
            }
        )

    acq = acquire_company_documents(t, company=transformed.get("company"))
    # Merge KIL docs into acquisition
    merged = {
        **acq,
        "documents": list(acq.get("documents") or []) + docs,
        "document_count": len(list(acq.get("documents") or []) + docs),
        "kil_published": len(docs),
    }
    reg = register_documents(merged)
    return {"acquisition": merged, "registry": reg, "kil_docs": len(docs)}


def _refresh_company_memory(ticker: str, transformed: Dict[str, Any], registry: Dict[str, Any]) -> Dict[str, Any]:
    from ..company_memory_bridge.bridge import build_company_memory_view

    fin = (transformed.get("models") or {}).get("CanonicalFinancialStatements") or {}
    return build_company_memory_view(ticker, canonical=fin, registry=registry)


def _invalidate_research(ticker: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
    from ..lifecycle.research_object import mark_stale_for_ticker, get_research_lifecycle, create_research_object

    reasons = sorted({e.get("event_type") for e in events if e.get("event_type")})
    reason = ", ".join(reasons) if reasons else "KnowledgeUpdated"
    # Ensure there is a published research object to invalidate for demo flows
    life = get_research_lifecycle(ticker)
    if not life.get("objects"):
        create_research_object(ticker, title=f"{ticker} institutional research", state="published")
    return mark_stale_for_ticker(ticker, reason=reason)


def integrate_company(
    ticker: str,
    *,
    events: Optional[List[Dict[str, Any]]] = None,
    trigger_repair: bool = True,
    knowledge_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Full KIL path for one company: transform → publish → memory → readiness → state."""
    t = str(ticker or "").upper().strip()
    events = list(events or [])

    transformed = transform_company_knowledge(t)

    # Automatic repair if mandatory financials missing
    repaired = None
    if trigger_repair and not transformed.get("financials_published"):
        from .repair.auto_repair import repair_missing_knowledge

        repaired = repair_missing_knowledge(t, missing=["financial_statements"])
        transformed = transform_company_knowledge(t)

    published = _publish_canonical_to_registry(t, transformed)
    memory = _refresh_company_memory(t, transformed, published.get("registry") or {})

    # Soft KG / FI refresh hooks
    kg_ok = False
    try:
        from institutional_knowledge_graph.production import refresh_company  # type: ignore

        refresh_company(t)
        kg_ok = True
    except Exception:
        kg_ok = False

    from ..research_pack.builder import build_institutional_research_pack
    from ..quality.engine import evaluate_evidence_quality
    from ..phase1_acceptance import evaluate_institutional_coverage
    from ..decision_eligibility.engine import evaluate_decision_eligibility

    pack = build_institutional_research_pack(t, auto_acquire=True)
    # Stamp knowledge versions onto pack
    snap = get_latest_snapshot()
    kv = knowledge_version or (snap or {}).get("knowledge_version")
    pack["knowledge_version"] = kv
    pack["evidence_version"] = (published.get("registry") or {}).get("evidence_count")
    pack["company_memory_version"] = memory.get("slot_coverage")
    pack["kil_integrated"] = True

    quality = evaluate_evidence_quality(
        canonical_financials=(transformed.get("models") or {}).get("CanonicalFinancialStatements"),
        registry_items=((published.get("registry") or {}).get("items") or []),
        documents=((published.get("acquisition") or {}).get("documents") or []),
    )
    from ..timeline.company_timeline import build_company_timeline

    timeline = build_company_timeline(t)
    kc = compute_knowledge_confidence(t, transformed=transformed, pack=pack, timeline=timeline)
    coverage = evaluate_institutional_coverage(t, pack=pack)
    state = compute_coverage_state(
        discovered=True,
        acquiring=False,
        transformed=transformed,
        quality=quality,
        pack=pack,
        coverage=coverage,
        knowledge_confidence=kc,
    )
    eligibility = evaluate_decision_eligibility(t, pack=pack, quality=quality)

    invalidated = None
    if events:
        invalidated = _invalidate_research(t, events)

    out = {
        "ok": True,
        "ticker": t,
        "entity_id": transformed.get("entity_id"),
        "knowledge_version": kv,
        "financials_published": transformed.get("financials_published"),
        "period_count": transformed.get("period_count"),
        "transformed": {
            "period_count": transformed.get("period_count"),
            "financials_published": transformed.get("financials_published"),
            "corporate_actions_count": transformed.get("corporate_actions_count"),
            "cgl_extract_present": transformed.get("cgl_extract_present"),
        },
        "published": {
            "kil_docs": published.get("kil_docs"),
            "evidence_count": (published.get("registry") or {}).get("evidence_count"),
        },
        "company_memory": {
            "slot_coverage": memory.get("slot_coverage"),
            "filled_slots": memory.get("filled_slots"),
        },
        "knowledge_graph_refreshed": kg_ok,
        "quality": quality,
        "knowledge_confidence": kc,
        "coverage_state": state,
        "institutional_coverage": {
            "complete": coverage.get("institutional_coverage_complete"),
            "pass_pct": coverage.get("pass_pct"),
            "failed": coverage.get("failed"),
        },
        "research_ready": pack.get("research_ready"),
        "claim_safe": pack.get("claim_safe"),
        "decision_eligibility": {
            "eligible": eligibility.get("eligible"),
            "permission": eligibility.get("permission"),
        },
        "research_invalidation": invalidated,
        "repaired": repaired is not None,
        "pack_summary": {
            "knowledge_version": pack.get("knowledge_version"),
            "evidence_version": pack.get("evidence_version"),
            "company_memory_version": pack.get("company_memory_version"),
            "claim_safe": pack.get("claim_safe"),
            "research_ready": pack.get("research_ready"),
        },
    }
    _COMPANY_STATE[t] = out
    try:
        kil_persist.put_company(t, out)
    except Exception:
        pass
    return out


def integrate_cgl_run(
    cgl_run: Optional[Dict[str, Any]] = None,
    *,
    companies: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Subscribe to a CGL cycle: emit events → transform → publish → refresh → invalidate.
    Called automatically after CGL run_cycle (soft-wired).
    """
    run = dict(cgl_run or {})
    if not run:
        try:
            from continuous_gather_learn.production import run as cgl_run_fn

            run = cgl_run_fn()
        except Exception as exc:
            return {"ok": False, "error": f"cgl_run_unavailable:{exc}"[:200]}

    # Determine companies to integrate
    tickers = [str(t).upper() for t in (companies or [])]
    if not tickers:
        # Prefer Phase-1 demo; also pull from run volumes/phases if present
        tickers = list(KIL_PHASE1_DEMO)
        for key in ("companies", "entities", "tickers"):
            if isinstance(run.get(key), list):
                tickers = [str(x).upper() for x in run[key]] or tickers

    events = emit_cgl_events(run, companies_updated=tickers)

    results = []
    evidence_added = 0
    fin_updated = 0
    invalidated_ids: List[str] = []
    for t in tickers:
        try:
            r = integrate_company(t, events=events, trigger_repair=True)
            results.append(r)
            evidence_added += int((r.get("published") or {}).get("kil_docs") or 0)
            if r.get("financials_published"):
                fin_updated += 1
            inv = r.get("research_invalidation") or {}
            invalidated_ids.extend(inv.get("marked_stale") or [])
        except Exception as exc:
            results.append({"ticker": t, "ok": False, "error": str(exc)[:200]})

    snap = create_knowledge_snapshot(
        run_id=str(run.get("run_id") or "unknown"),
        slot=str(run.get("slot") or "cycle"),
        companies_updated=tickers,
        evidence_added=evidence_added,
        financial_statements_updated=fin_updated,
        knowledge_graph_changes=sum(1 for r in results if r.get("knowledge_graph_refreshed")),
        research_invalidated=invalidated_ids,
    )

    # Stamp knowledge version onto company results
    for r in results:
        if isinstance(r, dict):
            r["knowledge_version"] = snap.get("knowledge_version")
            if r.get("ok") and r.get("ticker"):
                try:
                    kil_persist.put_company(r["ticker"], r)
                except Exception:
                    pass

    try:
        kil_persist.write_integration_heartbeat(
            {
                "ok": True,
                "cgl_run_id": run.get("run_id"),
                "companies": len(results),
                "knowledge_version": snap.get("knowledge_version"),
                "financials_updated": fin_updated,
            }
        )
    except Exception:
        pass

    return {
        "ok": True,
        "workstream_id": KIL_WORKSTREAM_ID,
        "cgl_run_id": run.get("run_id"),
        "events": events,
        "snapshot": snap,
        "companies": results,
        "summary": {
            "companies": len(results),
            "financials_updated": fin_updated,
            "evidence_added": evidence_added,
            "research_invalidated": len(invalidated_ids),
            "knowledge_version": snap.get("knowledge_version"),
        },
        "rule": "No manual refresh — KIL owns integration; CGL owns gathering",
    }


def get_integrated_company(ticker: str) -> Optional[Dict[str, Any]]:
    t = str(ticker or "").upper()
    if t in _COMPANY_STATE:
        return _COMPANY_STATE[t]
    try:
        row = kil_persist.get_company(t)
    except Exception:
        row = None
    if row:
        _COMPANY_STATE[t] = row
        return row
    return None
