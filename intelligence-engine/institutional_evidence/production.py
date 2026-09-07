"""IEP-01 / v1.1.1 production façades — Institutional Knowledge OS."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .flags import iep_flags, is_iep_enabled
from .schema import (
    CANONICAL_DOMAIN_MODELS,
    DESIGN_PRINCIPLES,
    GUIDING_PRINCIPLE,
    IEP_PRODUCT,
    IEP_SPEC,
    IEP_VERSION,
    IEP_WORKSTREAM_ID,
    KNOWLEDGE_OS_PIPELINE,
    ANTI_PIPELINE,
    MISSION_STATEMENT,
    PHASE1_ACCEPTANCE_CRITERIA,
    PHASE1_TOP20,
    PHASE1_UNIVERSE,
    RESEARCH_READY_THRESHOLD,
    AGI_PLATFORM_VERSION,
)


def get_iep_status() -> Dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": IEP_WORKSTREAM_ID,
        "product": IEP_PRODUCT,
        "version": IEP_VERSION,
        "platform_version": AGI_PLATFORM_VERSION,
        "spec": IEP_SPEC,
        "enabled": is_iep_enabled(),
        "flags": iep_flags(),
        "mission": MISSION_STATEMENT,
        "guiding_principle": GUIDING_PRINCIPLE,
        "design_principles": list(DESIGN_PRINCIPLES),
        "phase1_universe_size": len(PHASE1_UNIVERSE),
        "research_ready_threshold": RESEARCH_READY_THRESHOLD,
        "canonical_domain_models": list(CANONICAL_DOMAIN_MODELS),
        "pipeline": list(KNOWLEDGE_OS_PIPELINE),
        "anti_pipeline": list(ANTI_PIPELINE),
        "role": "institutional_knowledge_os",
    }


def get_research_pack(ticker: str, **kwargs: Any) -> Dict[str, Any]:
    from .research_pack.builder import build_institutional_research_pack

    return build_institutional_research_pack(ticker, **kwargs)


def get_research_readiness(ticker: str) -> Dict[str, Any]:
    pack = get_research_pack(ticker)
    return {
        "ok": True,
        "ticker": str(ticker).upper(),
        "readiness": pack.get("research_readiness"),
        "claim_safe": pack.get("claim_safe"),
        "research_ready": pack.get("research_ready"),
    }


def validate_research_pack(ticker: str = "", pack: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    from .validator.pack_validator import validate_research_pack_dict, ci_gate_failures

    p = pack if isinstance(pack, dict) else get_research_pack(ticker)
    v = validate_research_pack_dict(p)
    return {**v, "ci_gates": ci_gate_failures(p), "ticker": p.get("ticker")}


def orchestrate_research(ticker: str, **kwargs: Any) -> Dict[str, Any]:
    from .orchestrator.workflow import orchestrate_company_research

    return orchestrate_company_research(ticker, **kwargs)


def get_evidence_registry(ticker: str) -> Dict[str, Any]:
    from .registry.store import get_registry_for_ticker

    return get_registry_for_ticker(ticker)


def get_canonical_statements(ticker: str) -> Dict[str, Any]:
    from .canonical.statements import build_canonical_statements

    return build_canonical_statements(ticker)


def get_company_memory_bridge(ticker: str) -> Dict[str, Any]:
    from .canonical.statements import build_canonical_statements
    from .registry.store import get_registry_for_ticker
    from .company_memory_bridge.bridge import build_company_memory_view

    can = build_canonical_statements(ticker)
    reg = get_registry_for_ticker(ticker)
    return build_company_memory_view(ticker, canonical=can, registry=reg)


def get_phase1_coverage() -> Dict[str, Any]:
    from .phase1_acceptance import evaluate_institutional_coverage
    from .entity.resolve import entity_id_for_ticker

    rows = []
    ready_n = 0
    statements_n = 0
    complete_ev_n = 0
    coverage_complete_n = 0
    for c in PHASE1_TOP20:
        t = c["ticker"]
        try:
            pack = get_research_pack(t, auto_acquire=True)
            ready = bool(pack.get("research_ready"))
            pub = bool((pack.get("financials") or {}).get("published"))
            ev_n = ((pack.get("evidence") or {}).get("registry") or {}).get("evidence_count") or 0
            cov = evaluate_institutional_coverage(t, pack=pack)
            if ready:
                ready_n += 1
            if pub:
                statements_n += 1
            if ev_n >= 2:
                complete_ev_n += 1
            if cov.get("institutional_coverage_complete"):
                coverage_complete_n += 1
            rows.append(
                {
                    "ticker": t,
                    "entity_id": entity_id_for_ticker(t),
                    "company": c["company"],
                    "sector": c["sector"],
                    "research_ready": ready,
                    "claim_safe": pack.get("claim_safe"),
                    "readiness_score": (pack.get("research_readiness") or {}).get("score"),
                    "statements_published": pub,
                    "period_count": (pack.get("financials") or {}).get("period_count") or 0,
                    "evidence_count": ev_n,
                    "institutional_coverage_complete": cov.get("institutional_coverage_complete"),
                    "coverage_pass_pct": cov.get("pass_pct"),
                    "coverage_failed": cov.get("failed"),
                    "status": (pack.get("research_readiness") or {}).get("status"),
                }
            )
        except Exception as exc:
            rows.append({"ticker": t, "company": c["company"], "error": str(exc), "research_ready": False})
    n = max(1, len(PHASE1_TOP20))
    return {
        "ok": True,
        "phase": 1,
        "universe": "top_20_india_cross_sector",
        "acceptance_criteria": list(PHASE1_ACCEPTANCE_CRITERIA),
        "companies": rows,
        "summary": {
            "total": len(PHASE1_TOP20),
            "with_canonical_statements": statements_n,
            "with_complete_evidence": complete_ev_n,
            "research_ready_pct": round(100.0 * ready_n / n, 2),
            "research_ready_count": ready_n,
            "institutional_coverage_complete_count": coverage_complete_n,
        },
        "scale_rule": "Do NOT scale to Nifty 500 until Top-20 reaches Institutional Coverage Complete",
    }


def get_success_metrics() -> Dict[str, Any]:
    from .observability.metrics import research_quality_metrics

    cov = get_phase1_coverage()
    summary = cov.get("summary") or {}
    block_rate = 100.0 - float(summary.get("research_ready_pct") or 0)
    quality = research_quality_metrics(sample_limit=3)
    return {
        "ok": True,
        "metrics": {
            "companies_with_canonical_statements": summary.get("with_canonical_statements"),
            "companies_with_complete_evidence": summary.get("with_complete_evidence"),
            "research_ready_pct": summary.get("research_ready_pct"),
            "recommendation_block_rate_proxy_pct": round(block_rate, 2),
            "phase1_total": summary.get("total"),
            "institutional_coverage_complete_count": summary.get(
                "institutional_coverage_complete_count"
            ),
            **(quality.get("metrics") or {}),
        },
        "tracked": quality.get("tracked"),
        "coverage": cov,
        "quality_observability": quality,
    }


def get_evidence_center_board() -> Dict[str, Any]:
    status = get_iep_status()
    return {
        "ok": True,
        "board": "Evidence Center",
        "workstream_id": IEP_WORKSTREAM_ID,
        "status": status,
        "mission": MISSION_STATEMENT,
        "design_principles": list(DESIGN_PRINCIPLES),
        "pipeline": list(KNOWLEDGE_OS_PIPELINE),
        "phase1_acceptance_criteria": list(PHASE1_ACCEPTANCE_CRITERIA),
    }


def soft_slice_mission_control() -> Dict[str, Any]:
    """Mission Control Evidence Center soft slice — cheap; never scans Top-20 live."""
    try:
        kh = soft_slice_knowledge_health()
        return {
            "status": "ok" if is_iep_enabled() else "disabled",
            "workstream_id": IEP_WORKSTREAM_ID,
            "product": IEP_PRODUCT,
            "version": IEP_VERSION,
            "platform_version": AGI_PLATFORM_VERSION,
            "companies_with_canonical_statements": None,
            "companies_with_complete_evidence": None,
            "research_ready_pct": None,
            "research_ready_count": None,
            "phase1_total": len(PHASE1_TOP20),
            "recommendation_block_rate_proxy_pct": None,
            "threshold": RESEARCH_READY_THRESHOLD,
            "guiding_principle": GUIDING_PRINCIPLE,
            "mission": MISSION_STATEMENT,
            "board": "Evidence Center",
            "knowledge_os": True,
            "knowledge_health": kh,
            "latest_knowledge_version": kh.get("latest_knowledge_version"),
            "note": "Call /api/intelligence/iep/knowledge-health or /iep/phase1 for live coverage",
            "flags": iep_flags(),
        }
    except Exception as exc:
        return {
            "status": "error",
            "workstream_id": IEP_WORKSTREAM_ID,
            "error": str(exc)[:240],
        }


def health() -> Dict[str, Any]:
    return get_iep_status()


# --- v1.1.2 KIL façades ---


def get_kil_status() -> Dict[str, Any]:
    from .integration.layer import kil_status

    return kil_status()


def run_kil_integration(
    cgl_run: Optional[Dict[str, Any]] = None,
    *,
    companies: Optional[list] = None,
) -> Dict[str, Any]:
    from .integration.layer import integrate_cgl_run

    return integrate_cgl_run(cgl_run, companies=companies)


def integrate_company_knowledge(ticker: str, **kwargs: Any) -> Dict[str, Any]:
    from .integration.layer import integrate_company

    return integrate_company(ticker, **kwargs)


def get_knowledge_health() -> Dict[str, Any]:
    from .integration.health.dashboard import knowledge_health_board

    return knowledge_health_board(demo_only=True)


def get_knowledge_confidence(ticker: str) -> Dict[str, Any]:
    from .integration.confidence.score import compute_knowledge_confidence
    from .integration.layer import get_integrated_company

    integ = get_integrated_company(ticker)
    if integ and integ.get("knowledge_confidence"):
        return integ["knowledge_confidence"]
    return compute_knowledge_confidence(ticker)


def get_coverage_state(ticker: str) -> Dict[str, Any]:
    from .integration.layer import integrate_company, get_integrated_company

    integ = get_integrated_company(ticker) or integrate_company(ticker, trigger_repair=False)
    return integ.get("coverage_state") or {}


def get_knowledge_snapshots() -> Dict[str, Any]:
    from .integration.versioning.snapshots import list_snapshots

    return list_snapshots()


def get_kil_events() -> Dict[str, Any]:
    from .integration.events.bus import list_events

    return list_events()


def orchestrate_ask(ticker: str, **kwargs: Any) -> Dict[str, Any]:
    from .integration.orchestrate_ask import orchestrate_ask_research

    return orchestrate_ask_research(ticker, **kwargs)


def get_expansion_status() -> Dict[str, Any]:
    from .integration.expansion import expansion_status, maybe_enqueue_next_500
    from .phase1_acceptance import evaluate_institutional_coverage

    complete = 0
    for c in PHASE1_TOP20:
        try:
            if evaluate_institutional_coverage(c["ticker"]).get("institutional_coverage_complete"):
                complete += 1
        except Exception:
            pass
    status = expansion_status(top20_complete_count=complete, top20_total=len(PHASE1_TOP20))
    return {**status, "enqueue_preview": maybe_enqueue_next_500.__doc__}


def enqueue_nifty_500_expansion(*, force: bool = False) -> Dict[str, Any]:
    from .integration.expansion import maybe_enqueue_next_500

    return maybe_enqueue_next_500(force=force)


def soft_slice_knowledge_health() -> Dict[str, Any]:
    """Cheap Mission Control Knowledge Health slice."""
    try:
        from .integration.layer import health as kil_health, kil_status
        from .integration.versioning.snapshots import get_latest_snapshot
        from .integration.schema import KIL_PHASE1_DEMO, KIL_VERSION, KIL_WORKSTREAM_ID

        kil = kil_health() if callable(kil_health) else kil_status()
        snap = get_latest_snapshot() or kil.get("latest_snapshot")
        cgl_cov = None
        try:
            from continuous_gather_learn.production import dashboard as cgl_dash

            d = cgl_dash()
            cgl_cov = {
                "hard_coverage_pct": d.get("hard_coverage_pct"),
                "covered_companies": d.get("covered_companies"),
                "total_companies": d.get("total_companies"),
                "collector_success": d.get("collector_success_rate"),
                "effective_gather": d.get("effective_gather"),
                "gather_sidecar": d.get("gather_sidecar"),
            }
        except Exception:
            pass
        return {
            "status": "ok" if kil.get("ok") else "error",
            "board": "Knowledge Health",
            "workstream_id": KIL_WORKSTREAM_ID,
            "version": KIL_VERSION,
            "kil": kil,
            "companies_integrated": kil.get("companies_integrated"),
            "latest_knowledge_version": (snap or {}).get("knowledge_version")
            if isinstance(snap, dict)
            else None,
            "phase1_demo": list(KIL_PHASE1_DEMO),
            "cgl": cgl_cov,
            "note": (
                "KIL state is persisted from the gather sidecar. "
                "GET /api/intelligence/iep/knowledge-health uses cached integration rows."
            ),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:240]}


# --- v1.1.1 façades ---


def resolve_company_entity(query: str) -> Dict[str, Any]:
    from .entity.resolve import resolve_entity

    return resolve_entity(query)


def get_company_timeline(ticker: str) -> Dict[str, Any]:
    from .timeline.company_timeline import build_company_timeline

    return build_company_timeline(ticker)


def get_evidence_graph(ticker: str) -> Dict[str, Any]:
    from .evidence_graph.graph import build_evidence_graph

    return build_evidence_graph(ticker)


def get_decision_eligibility(ticker: str) -> Dict[str, Any]:
    from .decision_eligibility.engine import evaluate_decision_eligibility

    return evaluate_decision_eligibility(ticker)


def get_evidence_quality(ticker: str) -> Dict[str, Any]:
    from .quality.engine import evaluate_evidence_quality

    pack = get_research_pack(ticker)
    return evaluate_evidence_quality(
        canonical_financials=pack.get("financials") or {},
        registry_items=((pack.get("evidence") or {}).get("registry") or {}).get("items") or [],
        documents=((pack.get("evidence") or {}).get("acquisition") or {}).get("documents"),
    )


def get_canonical_domains(ticker: str) -> Dict[str, Any]:
    from .entity.resolve import resolve_entity
    from .canonical.domains import empty_domain_bundle
    from .canonical.statements import build_canonical_statements

    resolved = resolve_entity(ticker)
    if not resolved.get("resolved"):
        return resolved
    bundle = empty_domain_bundle(
        resolved["entity_id"], resolved["ticker"], name=str(resolved.get("company") or "")
    )
    bundle["models"]["CanonicalFinancialStatements"] = build_canonical_statements(
        resolved["ticker"], company=resolved.get("company")
    )
    bundle["CanonicalCompany"] = bundle["models"]["CanonicalCompany"]
    return bundle


def get_phase1_acceptance(ticker: str) -> Dict[str, Any]:
    from .phase1_acceptance import evaluate_institutional_coverage

    return evaluate_institutional_coverage(ticker)


def run_continuous_learning(ticker: str, **kwargs: Any) -> Dict[str, Any]:
    from .learning.continuous import on_evidence_event

    return on_evidence_event(ticker, **kwargs)


def get_research_lifecycle(ticker: str) -> Dict[str, Any]:
    from .lifecycle.research_object import get_research_lifecycle as _gl

    return _gl(ticker)


def get_observability_metrics() -> Dict[str, Any]:
    from .observability.metrics import research_quality_metrics

    return research_quality_metrics(sample_limit=5)


def institutional_company(company_ref: str) -> Dict[str, Any]:
    """Aggregate institutional company surface for Ask AGI + APIs."""
    from .entity.resolve import resolve_entity

    resolved = resolve_entity(company_ref)
    if not resolved.get("resolved"):
        return resolved
    t = resolved["ticker"]
    eid = resolved["entity_id"]
    return {
        "ok": True,
        "entity_id": eid,
        "ticker": t,
        "company": resolved.get("company"),
        "sector": resolved.get("sector"),
        "aliases": resolved.get("aliases"),
        "memory": get_company_memory_bridge(t),
        "financials": get_canonical_statements(t),
        "evidence": get_evidence_registry(t),
        "timeline": get_company_timeline(t),
        "research_ready": get_research_readiness(t),
        "claims": {"note": "Use /claims subresource or extract from research note"},
        "valuation": (get_canonical_domains(t).get("models") or {}).get("CanonicalValuation"),
        "knowledge": get_evidence_graph(t),
        "decision_eligibility": get_decision_eligibility(t),
        "quality": get_evidence_quality(t),
        "coverage": get_phase1_acceptance(t),
        "api": {
            "company": f"/v1/iep/company/{eid}",
            "memory": f"/v1/iep/company/{eid}/memory",
            "financials": f"/v1/iep/company/{eid}/financials",
            "evidence": f"/v1/iep/company/{eid}/evidence",
            "timeline": f"/v1/iep/company/{eid}/timeline",
            "research_ready": f"/v1/iep/company/{eid}/research-ready",
            "claims": f"/v1/iep/company/{eid}/claims",
            "valuation": f"/v1/iep/company/{eid}/valuation",
            "knowledge": f"/v1/iep/company/{eid}/knowledge",
        },
        "rule": "Ask AGI consumes the same institutional APIs",
    }


def _resolve_ref_to_ticker(company_ref: str) -> Dict[str, Any]:
    from .entity.resolve import resolve_entity, entity_id_for_ticker
    from .schema import PHASE1_TOP20, ENTITY_ID_PREFIX

    ref = str(company_ref or "").strip()
    # Accept entity id or ticker / alias
    if ref.upper().startswith("AGI-COMPANY-"):
        for c in PHASE1_TOP20:
            if entity_id_for_ticker(c["ticker"]) == ref.upper():
                return resolve_entity(c["ticker"])
        return {"ok": False, "resolved": False, "reason": "unknown_entity_id", "entity_id": ref}
    if ref.upper().startswith(ENTITY_ID_PREFIX) and ref != ref.upper():
        # already handled above; keep for clarity
        pass
    return resolve_entity(ref)


def company_subresource(company_ref: str, resource: str) -> Dict[str, Any]:
    resolved = _resolve_ref_to_ticker(company_ref)
    if not resolved.get("resolved"):
        return resolved
    t = resolved["ticker"]
    eid = resolved["entity_id"]
    resource = str(resource or "").lower().strip()
    mapping = {
        "": lambda: institutional_company(t),
        "memory": lambda: {**get_company_memory_bridge(t), "entity_id": eid},
        "financials": lambda: {**get_canonical_statements(t), "entity_id": eid},
        "evidence": lambda: {**get_evidence_registry(t), "entity_id": eid},
        "timeline": lambda: get_company_timeline(t),
        "research-ready": lambda: {**get_research_readiness(t), "entity_id": eid},
        "claims": lambda: {
            "ok": True,
            "entity_id": eid,
            "ticker": t,
            "claims": [],
            "note": "Populate via research lifecycle / claim extraction",
        },
        "valuation": lambda: {
            "ok": True,
            "entity_id": eid,
            "ticker": t,
            "valuation": (get_canonical_domains(t).get("models") or {}).get("CanonicalValuation"),
        },
        "knowledge": lambda: get_evidence_graph(t),
        "eligibility": lambda: get_decision_eligibility(t),
        "quality": lambda: get_evidence_quality(t),
        "coverage": lambda: get_phase1_acceptance(t),
        "domains": lambda: get_canonical_domains(t),
        "lifecycle": lambda: get_research_lifecycle(t),
    }
    fn = mapping.get(resource)
    if not fn:
        return {"ok": False, "error": f"unknown_resource:{resource}", "entity_id": eid}
    return fn()


# Gate façades
def check_writer_gate(ticker: str, **kwargs: Any) -> Dict[str, Any]:
    from .gates import gate_research_writer

    return gate_research_writer(ticker, **kwargs)


def check_decision_gate(ticker: str, recommendation: str, **kwargs: Any) -> Dict[str, Any]:
    from .gates import gate_decision_recommendation

    return gate_decision_recommendation(ticker, recommendation, **kwargs)


def check_publish_gate(ticker: str, **kwargs: Any) -> Dict[str, Any]:
    from .gates import gate_publishing

    return gate_publishing(ticker, **kwargs)
