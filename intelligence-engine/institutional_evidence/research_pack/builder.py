"""InstitutionalResearchPack — single canonical pack; no engine reads providers directly."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..schema import FORBIDDEN_INVENTED_FIELDS, PHASE1_TOP20


def _meta(ticker: str) -> Dict[str, str]:
    for c in PHASE1_TOP20:
        if c["ticker"] == ticker.upper():
            return dict(c)
    return {"ticker": ticker.upper(), "company": ticker.upper(), "sector": "unknown"}


def build_institutional_research_pack(
    ticker: str,
    *,
    auto_acquire: bool = True,
) -> Dict[str, Any]:
    from ..acquisition.collector import acquire_company_documents
    from ..registry.store import register_documents, get_registry_for_ticker
    from ..canonical.statements import build_canonical_statements
    from ..company_memory_bridge.bridge import build_company_memory_view
    from ..readiness.index import compute_research_readiness
    from ..validator.pack_validator import validate_research_pack_dict

    t = str(ticker or "").upper().strip()
    meta = _meta(t)
    missing: List[str] = []
    errors: List[str] = []

    if auto_acquire:
        acq = acquire_company_documents(t, company=meta.get("company"), trigger_ingest=False)
        reg = register_documents(acq)
    else:
        reg = get_registry_for_ticker(t)
        acq = {"documents": [], "document_count": 0}

    canonical = build_canonical_statements(t, company=meta.get("company"))
    memory = build_company_memory_view(t, canonical=canonical, registry=reg)

    # Soft-consume downstream intelligence (consumers of evidence — not substitutes)
    valuation: Dict[str, Any] = {}
    risks: Dict[str, Any] = {}
    forecast: Dict[str, Any] = {}
    knowledge_graph: Dict[str, Any] = {}
    decision: Dict[str, Any] = {}

    try:
        from valuation_engine.production import get_valuation  # type: ignore

        v = get_valuation(t)
        if isinstance(v, dict):
            valuation = v
    except Exception as exc:
        errors.append(f"valuation:{exc}")

    try:
        from institutional_knowledge_graph.production import get_company_graph  # type: ignore

        kg = get_company_graph(t)
        if isinstance(kg, dict):
            knowledge_graph = kg
    except Exception:
        pass

    try:
        from decision_engine.production import get_decision  # type: ignore

        d = get_decision(t)
        if isinstance(d, dict):
            decision = d
    except Exception:
        try:
            from institutional_decision_engine.production import get_decision  # type: ignore

            d = get_decision(t)
            if isinstance(d, dict):
                decision = d
        except Exception:
            pass

    if not canonical.get("published") or canonical.get("zero_periods"):
        missing.append("canonical_financial_statements")
    if (reg.get("evidence_count") or 0) < 1:
        missing.append("evidence_registry")
    if (memory.get("slot_coverage") or 0) < 0.2:
        missing.append("company_memory")

    evidence = {
        "registry": {
            "evidence_count": reg.get("evidence_count"),
            "primary_count": reg.get("primary_count"),
            "items": reg.get("items") or [],
        },
        "acquisition": {
            "document_count": acq.get("document_count"),
            "sources_hit": acq.get("sources_hit"),
        },
        "primary_citation_ids": [
            i.get("evidence_id")
            for i in (reg.get("items") or [])
            if i.get("research_ready")
        ][:50],
    }

    pack: Dict[str, Any] = {
        "schema": "InstitutionalResearchPack.v1",
        "company": meta.get("company"),
        "ticker": t,
        "sector": meta.get("sector"),
        "financials": canonical,
        "valuation": valuation,
        "risks": risks,
        "forecast": forecast,
        "knowledge_graph": knowledge_graph,
        "decision": decision,
        "evidence": evidence,
        "company_memory": memory,
        "research_readiness": None,  # filled below
        "claim_safe": False,
        "missing_components": missing,
        "forbidden_invented_fields": list(FORBIDDEN_INVENTED_FIELDS),
        "built_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "errors": errors,
        "rule": "No engine reads providers directly — consume this pack only",
    }

    readiness = compute_research_readiness(pack)
    pack["research_readiness"] = readiness
    validation = validate_research_pack_dict(pack)
    pack["validation"] = validation
    pack["claim_safe"] = bool(validation.get("claim_safe"))
    pack["research_ready"] = bool(readiness.get("research_ready"))
    pack["blocked"] = not (pack["claim_safe"] and pack["research_ready"])
    pack["ok"] = True
    return pack
