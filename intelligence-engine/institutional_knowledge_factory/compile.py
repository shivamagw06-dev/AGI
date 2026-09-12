"""Compile Mode — merge fragmented intelligence into Knowledge Objects."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from institutional_knowledge_factory.decision_memory import version_decision_memory
from institutional_knowledge_factory.dna_update import update_company_dna
from institutional_knowledge_factory.kpi import calculate_knowledge_kpis
from institutional_knowledge_factory.maturity import calculate_maturity
from institutional_knowledge_factory.notifications import notify_research_workflows
from institutional_knowledge_factory.persist import load_iko, save_iko
from institutional_knowledge_factory.pipeline import process_evidence
from institutional_knowledge_factory.quality import compute_knowledge_quality
from institutional_knowledge_factory.review import institutional_review
from institutional_knowledge_factory.schema import COMPILE_PIPELINE_STEPS, IKF_VERSION, PROGRAMME
from institutional_knowledge_factory.thesis import evaluate_thesis
from institutional_knowledge_runtime.store import load_or_create_company, put


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _val(cell: Any) -> Any:
    if isinstance(cell, dict):
        return cell.get("value")
    return cell


def gather_sources(entity_id: str) -> dict[str, Any]:
    """Collect all registered intelligence sources for a company."""
    t = entity_id.upper()
    sources: dict[str, Any] = {
        "entity_id": t,
        "ikt": None,
        "kf_object": None,
        "kf_pack": None,
        "company_seed": None,
        "sources_used": [],
        "coverage": {},
    }

    try:
        from institutional_knowledge_tables.store import company_record

        sources["ikt"] = company_record(t)
        if sources["ikt"].get("populated_tables"):
            sources["sources_used"].append("ikt")
            sources["coverage"]["ikt"] = len(sources["ikt"]["populated_tables"])
    except Exception:
        pass

    try:
        from knowledge_factory.store.repository import get_object, get_pack

        sources["kf_object"] = get_object("company", t)
        if sources["kf_object"]:
            sources["sources_used"].append("knowledge_factory_object")
        sources["kf_pack"] = get_pack(t)
        if sources["kf_pack"]:
            sources["sources_used"].append("knowledge_factory_pack")
    except Exception:
        pass

    try:
        from knowledge_factory.company_intelligence.fixtures.seeds import get_seed

        sources["company_seed"] = get_seed(t)
        if sources["company_seed"]:
            sources["sources_used"].append("company_seed")
    except Exception:
        pass

    return sources


def sources_to_evidence_items(sources: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert fragmented sources into normalized evidence items for compilation."""
    t = sources["entity_id"]
    items: list[dict[str, Any]] = []
    company_name = t

    # IKT → identity + financials
    ikt = sources.get("ikt") or {}
    tables = ikt.get("tables") or {}
    if tables:
        master = (tables.get("company_master") or {}).get("row") or {}
        biz = (tables.get("business_model") or {}).get("row") or {}
        company_name = _val(master.get("company_name")) or company_name
        desc = _val(biz.get("business_description")) or _val(biz.get("description"))
        extracts: list[dict[str, Any]] = []
        if desc:
            extracts.append({
                "template_id": "CLAIM_IDENTITY_BUSINESS",
                "statement": f"{company_name} generates revenue primarily through {desc}.",
                "confidence": 75,
                "evidence_id": f"EV_IKT_BIZ_{t}",
                "state": "PARTIAL",
            })
        fin = tables.get("financial_statements") or {}
        rows = fin.get("rows") or []
        if rows:
            latest = rows[-1]
            margin = _val(latest.get("ebitda_margin")) or _val(latest.get("net_margin"))
            if margin is not None:
                extracts.append({
                    "template_id": "CLAIM_FINANCIAL_CASH_GENERATION",
                    "statement": f"{company_name} reported EBITDA/net margin of {margin} in latest financials.",
                    "confidence": 80,
                    "evidence_id": f"EV_IKT_FIN_{t}",
                    "state": "PARTIAL",
                })
        if extracts:
            items.append({
                "source_id": f"IKT_{t}",
                "source_type": "financial_statement",
                "entity_id": t,
                "trust_score": 88,
                "freshness": 75,
                "coverage": list(ikt.get("populated_tables") or []),
                "extracts": extracts,
                "metrics": {},
            })

    # KF object → business/competitive claims
    kf = sources.get("kf_object") or {}
    if kf:
        extracts = []
        bm = kf.get("business_model") or {}
        if isinstance(bm, dict) and bm.get("business_description"):
            extracts.append({
                "template_id": "CLAIM_IDENTITY_BUSINESS",
                "statement": str(bm["business_description"]),
                "confidence": 78,
                "evidence_id": f"EV_KF_BM_{t}",
                "state": "PARTIAL",
            })
        cq = kf.get("competitive_quality") or kf.get("competitive_position") or {}
        if isinstance(cq, dict) and cq.get("moat_summary"):
            extracts.append({
                "template_id": "CLAIM_BUSINESS_SWITCHING_COSTS",
                "statement": str(cq["moat_summary"]),
                "confidence": 72,
                "evidence_id": f"EV_KF_MOAT_{t}",
                "state": "PARTIAL",
            })
        if extracts:
            items.append({
                "source_id": f"KF_OBJ_{t}",
                "source_type": "investor_presentation",
                "entity_id": t,
                "trust_score": 80,
                "freshness": 70,
                "extracts": extracts,
            })

    # Deep company seed → high-trust claims
    seed = sources.get("company_seed") or {}
    if seed:
        extracts = []
        identity = seed.get("identity") or {}
        bm = seed.get("business_model") or {}
        if identity.get("company_name"):
            company_name = identity["company_name"]
        if bm.get("business_description"):
            extracts.append({
                "template_id": "CLAIM_IDENTITY_BUSINESS",
                "statement": str(bm["business_description"]),
                "confidence": 85,
                "evidence_id": f"EV_SEED_BM_{t}",
                "state": "SUPPORTED",
            })
        segments = seed.get("segments") or {}
        if segments.get("margins"):
            extracts.append({
                "template_id": "CLAIM_MONITORING_MARGIN",
                "statement": f"{company_name} — {segments['margins']}",
                "confidence": 82,
                "evidence_id": f"EV_SEED_MARGIN_{t}",
                "state": "SUPPORTED",
                "monitoring": {
                    "trigger": "operating_margin < 20%",
                    "status": "healthy",
                    "metrics": ["operating_margin"],
                },
            })
        mgmt = seed.get("management") or seed.get("management_quality") or {}
        if mgmt.get("capital_allocation") or mgmt.get("track_record"):
            stmt = mgmt.get("capital_allocation") or mgmt.get("track_record")
            extracts.append({
                "template_id": "CLAIM_MGMT_CAPITAL_ALLOCATION",
                "statement": str(stmt),
                "confidence": 80,
                "evidence_id": f"EV_SEED_MGMT_{t}",
                "state": "PARTIAL",
            })
        if extracts:
            items.append({
                "source_id": f"SEED_{t}",
                "source_type": "annual_report",
                "entity_id": t,
                "trust_score": 92,
                "freshness": 85,
                "extracts": extracts,
            })

    # Evidence pack → link refs (no duplicate storage)
    pack = sources.get("kf_pack") or {}
    if pack:
        pack_items = pack.get("items") or pack.get("evidence") or []
        if pack_items and items:
            items[-1].setdefault("pack_refs", [p.get("evidence_id") for p in pack_items if isinstance(p, dict)][:5])

    return items


def resolve_source_conflicts(evidence_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """When sources disagree on same template, prefer higher trust × freshness."""
    by_template: dict[str, dict[str, Any]] = {}
    for item in evidence_items:
        trust = int(item.get("trust_score") or 70)
        fresh = int(item.get("freshness") or 70)
        score = trust * 0.6 + fresh * 0.4
        for extract in item.get("extracts") or []:
            tid = extract.get("template_id")
            if not tid:
                continue
            prev = by_template.get(tid)
            if prev is None or score > prev["_score"]:
                by_template[tid] = {**extract, "_score": score, "_source_id": item.get("source_id")}

    if not by_template:
        return evidence_items

    merged_extracts = [{k: v for k, v in ex.items() if not k.startswith("_")} for ex in by_template.values()]
    return [{
        "source_id": f"COMPILED_{evidence_items[0]['entity_id']}",
        "source_type": "corporate_filing",
        "entity_id": evidence_items[0]["entity_id"],
        "trust_score": max(int(i.get("trust_score") or 70) for i in evidence_items),
        "freshness": max(int(i.get("freshness") or 70) for i in evidence_items),
        "extracts": merged_extracts,
        "compiled_from": [i.get("source_id") for i in evidence_items],
    }]


def compile_company(
    entity_id: str,
    *,
    company: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Compile Mode — merge IKT + KF + evidence + seeds into one Knowledge Object."""
    t = entity_id.upper()
    steps_completed: list[str] = []

    if not force:
        existing = load_iko(t)
        if existing and existing.get("compiled_at"):
            return {
                "enabled": True,
                "mode": "compile",
                "version": IKF_VERSION,
                "entity_id": t,
                "skipped": True,
                "reason": "already_compiled",
                "iko": existing,
            }

    steps_completed.append("collect")
    sources = gather_sources(t)
    steps_completed.append("normalize")

    evidence_items = sources_to_evidence_items(sources)
    steps_completed.append("merge")

    if evidence_items:
        evidence_items = resolve_source_conflicts(evidence_items)
        steps_completed.extend(["resolve_duplicates", "resolve_contradictions"])

        result = process_evidence(
            t,
            evidence_items,
            company=company,
            reason="Compile mode: fragmented intelligence merge",
        )
        iko = result["iko"]
        changes = result.get("changes") or []
    else:
        iko = load_or_create_company(t, company=company)
        changes = []
        steps_completed.extend(["resolve_duplicates", "resolve_contradictions"])

    steps_completed.extend(["identify_assertions", "score_assertions", "link_evidence", "generate_company_dna"])

    thesis = evaluate_thesis(iko, changes)
    quality = compute_knowledge_quality(iko)
    maturity = calculate_maturity(iko)
    review = institutional_review(iko, changes, quality)
    notifications = notify_research_workflows(t, changes=changes, thesis=thesis, review=review, quality=quality)

    iko = version_decision_memory(t, iko, changes, thesis)
    iko["compiled_at"] = _now_iso()
    iko["compilation"] = {
        "mode": "compile",
        "version": IKF_VERSION,
        "sources_used": sources.get("sources_used") or [],
        "source_count": len(sources.get("sources_used") or []),
        "timestamp": iko["compiled_at"],
        "assertions_updated": len(changes),
    }
    save_iko(iko)
    put("company", t, iko)

    steps_completed.extend(["generate_monitoring", "generate_thesis", "update_knowledge_object"])

    return {
        "enabled": True,
        "mode": "compile",
        "version": IKF_VERSION,
        "programme": PROGRAMME,
        "entity_id": t,
        "pipeline_steps": list(COMPILE_PIPELINE_STEPS),
        "steps_completed": steps_completed,
        "sources_used": sources.get("sources_used") or [],
        "sources": {k: v is not None for k, v in sources.items() if k not in ("coverage",)},
        "claims_updated": len(changes),
        "changes": changes,
        "iko": iko,
        "thesis": thesis,
        "quality": quality,
        "maturity": maturity,
        "review": review,
        "notifications": notifications,
        "deterministic": True,
        "llm": False,
    }


def compile_universe(
    tickers: list[str],
    *,
    universe: str = "CUSTOM",
) -> dict[str, Any]:
    """Compile a list of tickers and return universe KPIs."""
    results: list[dict[str, Any]] = []
    ikos: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for ticker in tickers:
        try:
            r = compile_company(ticker, force=True)
            results.append({"ticker": ticker.upper(), "ok": True, "grade": (r.get("maturity") or {}).get("institutional_grade")})
            if r.get("iko"):
                ikos.append(r["iko"])
        except Exception as exc:
            errors.append({"ticker": ticker.upper(), "error": str(exc)[:120]})

    kpis = calculate_knowledge_kpis(ikos, universe=universe)
    kpis["target"] = len(tickers)
    kpis["errors"] = len(errors)

    return {
        "universe": universe,
        "compiled_results": results,
        "errors": errors,
        "kpis": kpis,
        "status": "ok" if len(ikos) == len(tickers) else "partial",
    }
