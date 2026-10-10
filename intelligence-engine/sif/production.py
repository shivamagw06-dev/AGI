"""SIF production bridge — soft adapters for locked engines (no redesign)."""

from __future__ import annotations

from typing import Any

from sif.detection import SECTOR_IDS, detect_sector
from sif.evidence import assess_company_evidence
from sif.frameworks import FRAMEWORKS, get_framework, list_frameworks
from sif.retrieval import sector_aware_retrieve
from sif.schema import SIF_VERSION
from sif.usage import get_sif_store


def is_sif_enabled() -> bool:
    try:
        from app.core.config import get_settings

        s = get_settings()
        return bool(getattr(s, "sif", True)) and bool(getattr(s, "academy_production", True))
    except Exception:
        return True


def valuation_guidance(sector_id: str | None) -> dict[str, Any]:
    fw = get_framework(sector_id)
    if not fw:
        return {"enabled": False, "methodology": ["dcf_fcff"], "preferred_multiples": ["P/E"]}
    return {
        "enabled": True,
        "sector_id": fw.sector_id,
        "methodology": list(fw.valuation_methodology),
        "preferred_multiples": list(fw.preferred_multiples),
        "primary_method": (fw.valuation_methodology or ["dcf_fcff"])[0],
        "note": "SIF advises VE which methodology to prioritise; live data supplies inputs",
    }


def analyse_query(
    query: str,
    *,
    ticker: str | None = None,
    engine: str = "ask_agi",
    evidence_supplied: dict[str, Any] | None = None,
    kip: Any | None = None,
    eve: Any | None = None,
    aws: Any | None = None,
    ve_pack: dict[str, Any] | None = None,
    iie_pack: dict[str, Any] | None = None,
    record: bool = True,
) -> dict[str, Any]:
    """Full SIF analysis package for a production query."""
    if not is_sif_enabled():
        return {"enabled": False, "sif_version": SIF_VERSION, "bypassed": True}

    detection = detect_sector(query, ticker)
    sector_id = detection.get("sector_id")
    resolved_ticker = detection.get("ticker") or (ticker.upper() if ticker else None)
    framework = get_framework(sector_id)
    retrieved = sector_aware_retrieve(query, framework, limit=16)
    evidence = assess_company_evidence(
        resolved_ticker,
        kip=kip,
        eve=eve,
        aws=aws,
        ve_pack=ve_pack,
        iie_pack=iie_pack,
        supplied=evidence_supplied,
    )

    # Compose sector-first answer hints
    hints: list[str] = []
    if framework:
        hints.append(
            f"Sector framework: {framework.name} ({framework.sector_id} / {framework.version}). "
            f"Prioritise KPIs: {', '.join(framework.priority_metrics[:8])}."
        )
        hints.append(
            "Decision: "
            + (framework.decision_framework[0] if framework.decision_framework else "Apply sector checklist before generic finance.")
        )
        hints.append(
            "Valuation: prefer "
            + ", ".join(framework.valuation_methodology[:3])
            + f" / multiples {', '.join(framework.preferred_multiples[:3])}."
        )
        for mistake in (framework.common_mistakes or [])[:1]:
            hints.append(f"Avoid: {mistake}")
    for t in (retrieved.get("teachings") or [])[:3]:
        bit = t.get("what_it_is") or ""
        hints.append(f"{t.get('concept_id')}: {bit}"[:360])

    allow_reco = bool(evidence.get("sufficient")) and bool(framework)
    recommendation_gate = {
        "allow_buy_hold_sell": allow_reco,
        "blocked": not allow_reco,
        "reason": None
        if allow_reco
        else (
            "sector_framework_missing"
            if not framework
            else evidence.get("recommendation_policy")
        ),
        "message": None
        if allow_reco
        else (
            "Sector framework missing — cannot issue institutional recommendation."
            if not framework
            else evidence.get("message")
        ),
    }

    # Mental / decision frameworks from sector + academy
    mental = list((framework.industry_mental_models if framework else [])[:8])
    academy_mental = []
    try:
        from academy.catalog import all_mental_models

        prio = set((framework.academy_concept_priority if framework else [])[:12])
        for mm in all_mental_models():
            if prio & set(mm.related_concepts or []):
                academy_mental.append(mm.model_id)
    except Exception:
        pass

    package = {
        "enabled": True,
        "sif_version": SIF_VERSION,
        "engine": engine,
        "query": query,
        "detection": detection,
        "sector_id": sector_id,
        "sector_name": framework.name if framework else None,
        "ticker": resolved_ticker,
        "framework": framework.to_dict() if framework else None,
        "framework_version": framework.version if framework else None,
        "kpis_retrieved": retrieved.get("kpi_ids") or [],
        "priority_metrics": list(framework.priority_metrics) if framework else [],
        "academy_concepts_used": retrieved.get("concept_ids") or [],
        "generic_suppressed": retrieved.get("generic_suppressed") or [],
        "sector_outranks_generic": bool(retrieved.get("sector_outranks_generic")),
        "ranked": retrieved.get("ranked") or [],
        "valuation_framework": valuation_guidance(sector_id),
        "iie_focus": list(framework.iie_focus) if framework else [],
        "industry_mental_models": mental,
        "academy_mental_models": academy_mental[:8],
        "decision_framework": list(framework.decision_framework) if framework else [],
        "company_evidence": evidence,
        "recommendation_gate": recommendation_gate,
        "answer_hints": hints[:10],
        "answer_policy": (
            "sector_framework_then_academy_then_evidence"
            if allow_reco
            else "insufficient_evidence_no_recommendation"
        ),
        "confidence": _confidence(framework, evidence, retrieved),
        "missing_evidence": evidence.get("missing") or [],
        "trace": {
            "sector": sector_id,
            "framework_used": framework.sector_id if framework else None,
            "framework_version": framework.version if framework else None,
            "kpis_retrieved": retrieved.get("kpi_ids") or [],
            "company_evidence_used": [k for k, ok in (evidence.get("present") or {}).items() if ok],
            "academy_concepts_used": retrieved.get("concept_ids") or [],
            "mental_models_used": mental + academy_mental[:4],
            "valuation_framework_used": (valuation_guidance(sector_id).get("methodology") or [])[:4],
            "confidence": None,
            "missing_evidence": evidence.get("missing") or [],
        },
    }
    package["trace"]["confidence"] = package["confidence"]

    if record:
        get_sif_store().record(
            {
                "query": (query or "")[:240],
                "engine": engine,
                "sector_id": sector_id,
                "ticker": resolved_ticker,
                "kpis": package["kpis_retrieved"][:12],
                "academy_concepts": package["academy_concepts_used"][:12],
                "recommendation_blocked": recommendation_gate["blocked"],
                "confidence": package["confidence"],
                "trace": package["trace"],
            }
        )
    return package


def attach_for_engine(engine: str, query: str, *, ticker: str | None = None, **kwargs: Any) -> dict[str, Any]:
    pkg = analyse_query(query, ticker=ticker, engine=engine, **kwargs)
    return {"sector_intelligence": pkg, "attached": bool(pkg.get("enabled") and pkg.get("sector_id"))}


def enrich_reasoning(reasoning: dict[str, Any], sif_pkg: dict[str, Any]) -> dict[str, Any]:
    """Inject sector framework into IRP-style reasoning dict."""
    if not sif_pkg.get("enabled") or not sif_pkg.get("sector_id"):
        return reasoning
    out = dict(reasoning or {})
    hints = sif_pkg.get("answer_hints") or []
    if hints:
        why = str(out.get("why") or "")
        out["why"] = (hints[0] + (" " + why if why else "")).strip()[:1400]
        drivers = list(out.get("key_drivers") or [])
        for kpi in (sif_pkg.get("priority_metrics") or [])[:8]:
            label = kpi.replace("_", " ")
            if label not in drivers:
                drivers.insert(0, label)
        out["key_drivers"] = drivers[:12]
        vp = str(out.get("valuation_perspective") or "")
        vg = sif_pkg.get("valuation_framework") or {}
        prefix = f"SIF valuation: {', '.join(vg.get('methodology') or [])}."
        out["valuation_perspective"] = (prefix + " " + vp).strip()[:900]
        supports = list(out.get("supports") or [])
        for h in hints[:3]:
            if h not in supports:
                supports.insert(0, h)
        out["supports"] = supports[:8]
    # Block fabricated conviction when evidence insufficient
    gate = sif_pkg.get("recommendation_gate") or {}
    if gate.get("blocked"):
        out["stance"] = "Insufficient Evidence"
        out["outlook"] = gate.get("message") or "Insufficient company evidence for institutional recommendation."
        out["uncertainties"] = list(out.get("uncertainties") or []) + list(sif_pkg.get("missing_evidence") or [])[:8]
    out["sector_intelligence_provenance"] = sif_pkg.get("trace") or {}
    return out


def quality_gates(*, warm: bool = True) -> dict[str, Any]:
    if warm:
        for q, t in (
            ("Should I buy HDFC Bank?", "HDFCBANK"),
            ("Should I buy Infosys?", "INFY"),
            ("UltraTech Cement outlook", "ULTRACEMCO"),
        ):
            analyse_query(q, ticker=t, engine="ask_agi", record=True)

    # Structural gates
    coverage = {sid: (sid in FRAMEWORKS) for sid in SECTOR_IDS}
    missing_fw = [sid for sid, ok in coverage.items() if not ok]

    hdfc = analyse_query("Should I buy HDFC Bank?", ticker="HDFCBANK", engine="validation", record=False)
    kpis = set(hdfc.get("kpis_retrieved") or [])
    banking_required = {"nim", "casa", "credit_cost", "gnpa", "nnpa", "cet1", "roe", "pb"}
    banking_hit = banking_required & kpis
    generics = set(hdfc.get("generic_suppressed") or [])
    academy = hdfc.get("academy_concepts_used") or []
    generic_leaked = [c for c in academy[:8] if c in {"risk_and_diversification", "liquidity", "monetary_system"}]

    checks = {
        "all_phase1_sectors_have_frameworks": not missing_fw,
        "hdfc_maps_to_banks": hdfc.get("sector_id") == "banks",
        "hdfc_kpis_include_banking_core": len(banking_hit) >= 6,
        "hdfc_suppresses_generic_concepts": "risk_and_diversification" in generics or not generic_leaked,
        "sector_outranks_generic": bool(hdfc.get("sector_outranks_generic")),
        "evidence_gate_blocks_without_docs": bool((hdfc.get("recommendation_gate") or {}).get("blocked")),
        "ve_methodology_for_banks_is_pb_or_excess_return": any(
            m in ((hdfc.get("valuation_framework") or {}).get("methodology") or [])
            for m in ("pb", "justified_pb", "residual_income", "excess_return")
        ),
    }
    passed = all(checks.values())
    return {
        "passed": passed,
        "checks": checks,
        "missing_frameworks": missing_fw,
        "hdfc_kpis": sorted(kpis),
        "hdfc_banking_hits": sorted(banking_hit),
        "reject_completion": not passed,
        "message": "SIF quality gates passed" if passed else "SIF incomplete — sector frameworks or HDFC prioritisation failed",
    }


def production_dashboard() -> dict[str, Any]:
    gates = quality_gates(warm=False)
    return {
        "programme": "SIF",
        "version": SIF_VERSION,
        "enabled": is_sif_enabled(),
        "sector_count": len(FRAMEWORKS),
        "sectors": sorted(FRAMEWORKS.keys()),
        "usage": get_sif_store().snapshot(),
        "frameworks": [{"sector_id": f["sector_id"], "name": f["name"], "priority_metrics": f["priority_metrics"][:6]} for f in list_frameworks()],
        "quality_gates": gates,
    }


def _confidence(framework, evidence: dict[str, Any], retrieved: dict[str, Any]) -> float:
    score = 0.35
    if framework:
        score += 0.25
    if evidence.get("sufficient"):
        score += 0.30
    elif evidence.get("core_ok"):
        score += 0.10
    if retrieved.get("kpi_ids"):
        score += 0.10
    return round(min(0.95, score), 3)
