"""LEO production bridge — soft adapters for locked engines (no redesign)."""

from __future__ import annotations

from typing import Any

from leo.dossier import get_dossier, list_dossiers, update_dossier
from leo.fetchers import fetch_for_plan
from leo.gates import assess_quality_gate, quality_gates_report
from leo.normalize import normalize_bundles
from leo.planner import build_evidence_plan
from leo.ranking import rank_evidence, summarize_usage
from leo.schema import LEO_VERSION
from leo.sources import configured_sources, select_sources
from leo.usage import get_leo_store
from leo.verify import verify_evidence_objects


def is_leo_enabled() -> bool:
    try:
        from app.core.config import get_settings

        return bool(getattr(get_settings(), "leo", True))
    except Exception:
        return True


def package_for_query(
    query: str,
    *,
    ticker: str | None = None,
    engine: str = "ask_agi",
    eve: Any | None = None,
    kip: Any | None = None,
    aoi: Any | None = None,
    mee: Any | None = None,
    record: bool = True,
) -> dict[str, Any]:
    """
    Orchestrate live evidence before reasoning.
    Returns a soft package for Ask AGI / CAE / IRP / SIF (evidence_supplied).
    """
    if not is_leo_enabled():
        return {
            "enabled": False,
            "leo_version": LEO_VERSION,
            "bypassed": True,
            "answer_policy": "leo_disabled",
            "evidence_objects": [],
            "provenance": {"influenced": False, "reason": "leo_disabled"},
        }

    plan = build_evidence_plan(query, ticker=ticker)
    sources = select_sources(plan)
    fetched = fetch_for_plan(plan, sources, eve=eve, kip=kip, aoi=aoi, mee=mee)
    bundles = fetched.get("bundles") or []
    api_calls = fetched.get("api_calls") or []
    resolved_ticker = fetched.get("ticker") or plan.get("ticker")

    objects = normalize_bundles(bundles, ticker=resolved_ticker, plan=plan)
    verified_pack = verify_evidence_objects(objects, eve=eve, ticker=resolved_ticker)
    ranked = rank_evidence(verified_pack.get("evidence_objects") or [])
    usage = summarize_usage(ranked, api_calls)

    # Update missing evidence on plan
    present_types = {o.get("evidence_type") for o in ranked}
    plan["missing_evidence"] = [t for t in (plan.get("required_evidence") or []) if t not in present_types]
    plan["present_evidence"] = sorted(present_types)

    gate = assess_quality_gate(plan, ranked, usage)
    # Soft-attach SIF for CID sector KPIs when available
    sif_for_cid: dict[str, Any] = {}
    try:
        from sif.production import analyse_query as sif_analyse

        sif_for_cid = sif_analyse(
            query,
            ticker=resolved_ticker,
            engine="leo_cid",
            record=False,
        ) or {}
    except Exception:
        sif_for_cid = {}
    dossier = update_dossier(
        resolved_ticker,
        ranked,
        plan=plan,
        sif_pkg=sif_for_cid,
    )

    # Provenance / contribution
    influenced = bool(ranked) and bool(usage.get("external_api_contributed") or usage.get("documents_used"))
    docs = dossier.get("documents") or {}
    package = {
        "enabled": True,
        "leo_version": LEO_VERSION,
        "engine": engine,
        "query": (query or "").strip(),
        "intent": plan.get("intent"),
        "ticker": resolved_ticker,
        "entity": plan.get("entity"),
        "sector_id": plan.get("sector_id") or (dossier.get("identity") or {}).get("sector_id"),
        "evidence_plan": plan,
        "sources_selected": [{"source_id": s["source_id"], "selected_for": s.get("selected_for")} for s in sources],
        "sources_queried": usage.get("sources_queried") or [],
        "sources_used": usage.get("sources_used") or [],
        "api_calls": api_calls,
        "documents_used": usage.get("documents_used") or [],
        "announcements_used": usage.get("announcements_used") or [],
        "market_data_used": usage.get("market_data_used") or [],
        "macro_data_used": usage.get("macro_data_used") or [],
        "evidence_objects": ranked[:80],
        "evidence_count": len(ranked),
        "conflicts": verified_pack.get("conflicts") or [],
        "evidence_confidence": verified_pack.get("evidence_confidence") or 0.0,
        "missing_evidence": plan.get("missing_evidence") or [],
        "quality_gate": gate,
        "company_dossier": {
            "ticker": dossier.get("ticker"),
            "cid_version": dossier.get("cid_version"),
            "coverage_score": dossier.get("coverage_score"),
            "coverage_grade": dossier.get("coverage_grade"),
            "updated_at": dossier.get("updated_at"),
            "sector_id": (dossier.get("sector_framework") or {}).get("sector_id"),
            "missing_evidence": dossier.get("missing_evidence") or [],
            "latest_announcement": dossier.get("latest_announcement"),
            "latest_filing": dossier.get("latest_filing"),
            "latest_presentation": dossier.get("latest_presentation"),
            "counts": {
                "annual_reports": len(docs.get("annual_reports") or []),
                "quarterly_results": len(docs.get("quarterly_results") or []),
                "investor_presentations": len(docs.get("investor_presentations") or []),
                "corporate_announcements": len(dossier.get("announcements") or []),
                "financial_statements": len((dossier.get("financial_statements") or {}).get("versions") or []),
                "timeline_events": len(dossier.get("evidence_timeline") or []),
            },
        },
        "sector_intelligence": sif_for_cid if isinstance(sif_for_cid, dict) else {},
        "sif_evidence_supplied": gate.get("sif_evidence_supplied") or {},
        "usage": usage,
        "eve": {
            "touched": verified_pack.get("eve_touched"),
            "ingest_attempts": verified_pack.get("eve_ingest_attempts"),
        },
        "influenced_reasoning": influenced,
        "answer_policy": "live_evidence_before_reasoning",
        "answer_hints": _hints(plan, ranked, gate, usage),
        "reasoning_trace": {
            "steps": [
                "entity_detection",
                "intent_detection",
                "evidence_plan",
                "source_selection",
                "vendor_fetch",
                "normalize",
                "eve_verify",
                "rank",
                "dossier_update",
                "quality_gate",
                "package_for_cae",
            ],
            "external_contribution": usage.get("external_api_contributed"),
            "document_contribution": bool(usage.get("documents_used")),
            "final_confidence": verified_pack.get("evidence_confidence") or 0.0,
        },
        "provenance": {
            "influenced": influenced,
            "orchestrator": "LEO",
            "leo_version": LEO_VERSION,
            "sources_used": usage.get("sources_used") or [],
            "external_sources_used": usage.get("external_sources_used") or [],
        },
    }

    if record:
        get_leo_store().record(package)
    return package


def attach_for_engine(
    engine: str,
    query: str,
    *,
    ticker: str | None = None,
    payload: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    pkg = payload if isinstance(payload, dict) and payload.get("leo_version") else package_for_query(
        query, ticker=ticker, engine=engine, **kwargs
    )
    return {"live_evidence": pkg, "attached": bool(pkg.get("enabled")) and not pkg.get("bypassed")}


def enrich_reasoning(reasoning: dict[str, Any], leo_pkg: dict[str, Any]) -> dict[str, Any]:
    """Soft-enrich IRP/Ask AGI reasoning dict with LEO citations (additive)."""
    if not isinstance(reasoning, dict) or not isinstance(leo_pkg, dict) or not leo_pkg.get("enabled"):
        return reasoning
    out = dict(reasoning)
    cites = []
    for o in (leo_pkg.get("evidence_objects") or [])[:8]:
        cites.append(
            {
                "evidence_id": o.get("evidence_id"),
                "evidence_type": o.get("evidence_type"),
                "source_id": o.get("source_id"),
                "title": o.get("title"),
                "confidence": o.get("confidence"),
                "verification_status": o.get("verification_status"),
            }
        )
    out["live_evidence_citations"] = cites
    out["live_evidence_confidence"] = leo_pkg.get("evidence_confidence")
    gate = leo_pkg.get("quality_gate") or {}
    if gate.get("blocked"):
        out["recommendation_policy"] = gate.get("message") or out.get("recommendation_policy")
        out["recommendation_blocked_by_leo"] = True
    return out


def production_dashboard() -> dict[str, Any]:
    cfg = configured_sources()
    snap = get_leo_store().snapshot()
    healthy = [sid for sid, m in cfg.items() if m.get("healthy") and m.get("configured")]
    unused = [
        sid
        for sid, m in cfg.items()
        if m.get("configured") and snap.get("by_source_used", {}).get(sid, 0) == 0
    ]
    most_useful = sorted(
        (snap.get("by_source_used") or {}).items(), key=lambda kv: -kv[1]
    )[:8]
    return {
        "programme": "LEO",
        "leo_version": LEO_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "enabled": is_leo_enabled(),
        "configured_apis": [
            {"source_id": sid, **{k: v for k, v in meta.items() if k != "env"}}
            for sid, meta in cfg.items()
        ],
        "healthy_apis": healthy,
        "unused_apis": unused,
        "metrics": snap,
        "calls_today": snap.get("calls_today"),
        "calls_per_query": snap.get("calls_per_query"),
        "average_latency_ms": snap.get("average_latency_ms"),
        "evidence_contribution": {
            "objects_created": snap.get("evidence_objects_created"),
            "external_contributions": snap.get("external_contributions"),
            "reasoning_contribution_pct": snap.get("reasoning_contribution_pct"),
        },
        "most_useful_apis": [{"source_id": k, "used": v} for k, v in most_useful],
        "api_failures": snap.get("by_source_failures") or {},
        "dossiers": list_dossiers(limit=20),
        "answer_policy": "live_evidence_before_reasoning",
    }


def run_quality_gates(
    tickers: list[str] | None = None,
    *,
    eve: Any | None = None,
) -> dict[str, Any]:
    samples = tickers or [
        "HDFCBANK",
        "INFY",
        "RELIANCE",
        "ULTRACEMCO",
        "POWERGRID",
        "SUNPHARMA",
        "TATASTEEL",
    ]
    packages = []
    for t in samples:
        q = f"Should I buy {t}?"
        packages.append(package_for_query(q, ticker=t, engine="quality_gates", eve=eve, record=True))
    report = quality_gates_report(packages)
    # Success metrics for LEO completion
    ext_ok = all((p.get("usage") or {}).get("external_api_contributed") for p in packages)
    objects_ok = all(len(p.get("evidence_objects") or []) > 0 for p in packages)
    eve_ok = all((p.get("eve") or {}).get("touched") is not False for p in packages)
    return {
        "leo_version": LEO_VERSION,
        "tickers": samples,
        "report": report,
        "success_metrics": {
            "external_api_contributes_when_relevant": ext_ok,
            "evidence_objects_created": objects_ok,
            "eve_path_available": eve_ok,
            "no_reco_on_academy_sif_only": all(
                (p.get("quality_gate") or {}).get("blocked")
                or (p.get("usage") or {}).get("external_api_contributed")
                for p in packages
            ),
        },
        "packages": [
            {
                "ticker": p.get("ticker"),
                "sources_used": p.get("sources_used"),
                "external": (p.get("usage") or {}).get("external_api_contributed"),
                "objects": p.get("evidence_count"),
                "missing": p.get("missing_evidence"),
                "blocked": (p.get("quality_gate") or {}).get("blocked"),
                "confidence": p.get("evidence_confidence"),
            }
            for p in packages
        ],
        "pass": objects_ok and ext_ok,
    }


def _hints(
    plan: dict[str, Any],
    ranked: list[dict[str, Any]],
    gate: dict[str, Any],
    usage: dict[str, Any],
) -> list[str]:
    hints: list[str] = []
    hints.append(
        f"LEO evidence plan ({plan.get('intent')}): "
        f"{len(plan.get('present_evidence') or [])} types present, "
        f"{len(plan.get('missing_evidence') or [])} missing."
    )
    if usage.get("external_sources_used"):
        hints.append(
            "External sources used: " + ", ".join(usage.get("external_sources_used")[:8]) + "."
        )
    if usage.get("documents_used"):
        hints.append("Company documents: " + "; ".join(usage.get("documents_used")[:3]) + ".")
    if gate.get("blocked"):
        hints.append(gate.get("message") or "Recommendation blocked — insufficient live evidence.")
    elif ranked:
        top = ranked[0]
        hints.append(
            f"Top evidence: {top.get('evidence_type')} from {top.get('source_id')} "
            f"(confidence {top.get('confidence')})."
        )
    return hints[:8]
