"""S05 — Selective Knowledge Factory retrieval (primary retrieval engine)."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from ask_pipeline.schema import KNOWLEDGE_SELECTION
from ask_pipeline.store import utc_now


def _prov(collector: str, *, derived_from: str | None = None) -> dict[str, Any]:
    now = utc_now()
    return {
        "source": "knowledge_factory",
        "retrieved_at": now,
        "validated_at": now,
        "collector": collector,
        "confidence": None,
        "derived_from": derived_from,
        "version": "ask-kf-retrieve-v1",
        "fabricated": False,
    }


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        return {"unavailable": True, "error": str(exc)[:160], "fabricated": False}


def retrieve_knowledge(
    *,
    intent: str,
    entities: list[dict[str, Any]],
    soft_tags: list[dict[str, Any]] | None = None,
    question: str | None = None,
    as_of: str | None = None,
    concept_mode: bool = False,
    institutional_knowledge: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.time()
    selection = dict(KNOWLEDGE_SELECTION.get(intent) or KNOWLEDGE_SELECTION["Unknown"])

    # IKL — institutional memory before KF/IERE raw-document style retrieval
    ikl_pack: dict[str, Any] = institutional_knowledge or {}
    try:
        from institutional_knowledge_layer.production import ask_consult as ikl_ask_consult

        company_ids_early = [
            str(e["id"]).upper()
            for e in (entities or [])
            if e.get("type") == "company" and e.get("id")
        ]
        if institutional_knowledge is None:
            ikl_pack = ikl_ask_consult(
                question or "",
                ticker=company_ids_early[0] if company_ids_early else None,
                companies=company_ids_early or None,
            ) or {}
    except Exception:
        ikl_pack = {}

    # Phase 6.0 — Universal Knowledge Orchestration. The desk path gathers the
    # same provider set as the KUL short-circuit; routing never decides coverage.
    uko_pack: dict[str, Any] = {}
    try:
        from universal_knowledge.production import for_ask_pipeline

        company_ids_uko = [
            str(e["id"]).upper()
            for e in (entities or [])
            if e.get("type") == "company" and e.get("id")
        ]
        uko_pack = for_ask_pipeline(
            question or "",
            ticker=company_ids_uko[0] if company_ids_uko else None,
        ) or {}
    except Exception as exc:
        uko_pack = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "providers_used": []}

    # Track A Concept Mode — never force company objects / Infosys defaults
    if concept_mode:
        selection = {k: v for k, v in selection.items() if k != "company"}
        selection.setdefault("macro", "optional")
        selection.setdefault("industry", "optional")
        selection.setdefault("government", "optional")
    # Soft tags may add optional object types
    for tag in soft_tags or []:
        t = tag.get("type")
        if t == "industry":
            selection.setdefault("industry", "optional")
        elif t == "government_policy":
            selection.setdefault("government", "optional")
        elif t == "macro_variable":
            selection.setdefault("macro", "optional")
        elif t == "alternative_dataset":
            selection.setdefault("alternative_data", "optional")
        elif t == "universe":
            selection.setdefault("universe", "optional")
        elif t == "portfolio":
            selection.setdefault("decision_memory", "optional")

    company_ids = []
    if not concept_mode:
        company_ids = [
            str(e["id"]).upper() for e in entities if e.get("type") == "company" and e.get("id")
        ]
    bag: dict[str, Any] = {"objects": {}, "skipped_objects": [], "errors": []}

    for obj, mode in selection.items():
        if mode not in ("required", "optional"):
            bag["skipped_objects"].append({"object": obj, "reason": "not_selected"})
            continue
        bag["objects"][obj] = _retrieve_object(obj, company_ids)

    # Explicitly mark non-selected
    for obj in (
        "universe",
        "company",
        "corporate_events",
        "government",
        "industry",
        "relationships",
        "alternative_data",
        "expectations",
        "historical",
        "decision_memory",
        "replay",
        "macro",
    ):
        if obj not in selection:
            bag["skipped_objects"].append({"object": obj, "reason": "intent_not_applicable"})

    # Soft-wire IERE — ranked Evidence Packs (never PDFs / never raw APIs).
    iere = _retrieve_iere(
        question=question,
        company_ids=company_ids,
        as_of=as_of,
        concept_mode=concept_mode,
    )
    primary = "evidence_retrieval" if iere and not iere.get("unavailable") else "knowledge_factory"
    if isinstance(ikl_pack, dict) and ikl_pack.get("enabled") and ikl_pack.get("layers_hit"):
        primary = f"ikl+{primary}"

    # Soft-wire multi-source adapters (Private Markets / Valuation CMS / Nifty research).
    multi_source = _retrieve_multi_source(
        question=question,
        company_ids=company_ids,
        entities=entities,
    )
    if multi_source and not multi_source.get("unavailable") and multi_source.get("evidence_count"):
        # Keep KF/IERE primary; annotate that multi-source contributed.
        if primary == "knowledge_factory":
            primary = "knowledge_factory+multi_source"
        else:
            primary = f"{primary}+multi_source"
    if isinstance(uko_pack, dict) and uko_pack.get("providers_used"):
        primary = f"uko+{primary}"

    return {
        "stage": "knowledge_retrieval",
        "status": "executed",
        "intent": intent,
        "selection": selection,
        "company_ids": company_ids,
        "concept_mode": concept_mode,
        "as_of": as_of,
        "bag": bag,
        "iere": iere,
        "multi_source": multi_source,
        "institutional_knowledge": ikl_pack if isinstance(ikl_pack, dict) else {},
        "universal_knowledge": uko_pack if isinstance(uko_pack, dict) else {},
        "primary_engine": primary,
        "retrieval_order_policy": "uko→company_memory→industry→macro→graph→kpis→timeline→raw→live",
        "duration_ms": int((time.time() - started) * 1000),
        "provenance": _prov("ask_pipeline.knowledge.retrieve_knowledge"),
        "fabricated": False,
    }


def _retrieve_multi_source(
    *,
    question: str | None,
    company_ids: list[str],
    entities: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    try:
        from multi_source import retrieve_multi_source

        ticker = company_ids[0] if company_ids else None
        out = retrieve_multi_source(
            question or "",
            ticker=ticker,
            entities=entities,
            timeout_sec=2.5,
        )
        return out if isinstance(out, dict) else {"unavailable": True, "fabricated": False}
    except Exception as exc:
        return {"unavailable": True, "error": str(exc)[:160], "fabricated": False}


def _retrieve_iere(
    *,
    question: str | None,
    company_ids: list[str],
    as_of: str | None = None,
    concept_mode: bool = False,
) -> dict[str, Any]:
    try:
        from evidence_retrieval.production import replay as iere_replay
        from evidence_retrieval.production import search as iere_search

        q = (question or "").strip()
        if not q:
            if concept_mode or not company_ids:
                q = "What institutional evidence supports this conceptual question?"
            else:
                q = f"What institutional evidence is available for {company_ids[0]}?"
        ticker = None if concept_mode else (company_ids[0] if company_ids else None)
        # Point-in-time replay only when as_of is an explicit historical bound
        today = datetime.now(timezone.utc).date().isoformat()
        use_replay = bool(as_of) and str(as_of)[:10] < today
        if use_replay:
            out = iere_replay(question=q, as_of=as_of, ticker=ticker)
        else:
            out = iere_search(q, ticker=ticker, as_of=as_of)
        return {
            "retrieval_id": out.get("retrieval_id"),
            "ask_envelope": out.get("ask_envelope"),
            # Full ranked list for Track B Answer Assembly (structured only)
            "ranked_evidence": list(out.get("ranked") or []),
            "pack_ids": out.get("pack_ids") or [],
            "ranked_count": out.get("ranked_count"),
            "quality_gates": out.get("quality_gates"),
            "latency_ms": out.get("latency_ms"),
            "as_of": as_of,
            "concept_mode": concept_mode,
            "replay": out.get("replay"),
            "unavailable": False,
            "fabricated": False,
            "reasoning_changed": False,
        }
    except Exception as exc:
        return {"unavailable": True, "error": str(exc)[:160], "fabricated": False}


def _retrieve_object(obj: str, company_ids: list[str]) -> dict[str, Any]:
    if obj == "company":
        rows = {}
        for cid in company_ids or []:
            rows[cid] = _company(cid)
        if not company_ids:
            return {
                "status": "empty",
                "reason": "no_company_entity",
                "provenance": _prov("company"),
            }
        return {"status": "ok", "by_entity": rows, "provenance": _prov("company")}

    if obj == "corporate_events":
        rows = {}
        for cid in company_ids:
            rows[cid] = _safe(_events, cid)
        return {"status": "ok", "by_entity": rows, "provenance": _prov("corporate_events")}

    if obj == "industry":
        rows = {}
        for cid in company_ids:
            rows[cid] = _safe(_industry, cid)
        return {"status": "ok", "by_entity": rows, "provenance": _prov("industry")}

    if obj == "relationships":
        rows = {}
        for cid in company_ids:
            rows[cid] = _safe(_relationships, cid)
        return {"status": "ok", "by_entity": rows, "provenance": _prov("relationships")}

    if obj == "alternative_data":
        rows = {}
        for cid in company_ids:
            rows[cid] = _safe(_alt, cid)
        return {"status": "ok", "by_entity": rows, "provenance": _prov("alternative_data")}

    if obj == "expectations":
        rows = {}
        for cid in company_ids:
            rows[cid] = _safe(_expectations, cid)
        return {"status": "ok", "by_entity": rows, "provenance": _prov("expectations")}

    if obj == "government":
        return {"status": "ok", "payload": _safe(_government), "provenance": _prov("government")}

    if obj == "macro":
        return {"status": "ok", "payload": _safe(_macro), "provenance": _prov("macro")}

    if obj == "universe":
        return {"status": "ok", "payload": _safe(_universe), "provenance": _prov("universe")}

    if obj == "historical":
        rows = {}
        for cid in company_ids:
            rows[cid] = _safe(_historical, cid)
        return {"status": "ok", "by_entity": rows, "provenance": _prov("historical")}

    if obj == "decision_memory":
        return {"status": "ok", "payload": _safe(_decision_memory), "provenance": _prov("decision_memory")}

    if obj == "replay":
        return {"status": "ok", "payload": _safe(_replay_index), "provenance": _prov("replay")}

    return {"status": "skipped", "reason": "unknown_object", "provenance": _prov(obj)}


def _company(cid: str) -> dict[str, Any]:
    out: dict[str, Any] = {"entity": cid}
    try:
        from knowledge_factory.production import company_object, evidence_feed

        out["object"] = company_object(cid)
        out["evidence_feed"] = evidence_feed(cid)
    except Exception as exc:
        out["error"] = str(exc)[:160]
    try:
        from knowledge_factory.company_intelligence import store as ici_store

        out["company_intelligence"] = ici_store.get(cid)
    except Exception:
        out["company_intelligence"] = None
    out["provenance"] = _prov("company", derived_from=cid)
    out["found"] = bool(out.get("object") or out.get("evidence_feed") or out.get("company_intelligence"))
    return out


def _events(cid: str) -> dict[str, Any]:
    from knowledge_factory.corporate_events import store as icei_store

    return {"timeline": icei_store.get_timeline(cid), "provenance": _prov("corporate_events")}


def _industry(cid: str) -> dict[str, Any]:
    from knowledge_factory.industry_intelligence.production import company_industry

    return {"industry": company_industry(cid), "provenance": _prov("industry")}


def _relationships(cid: str) -> dict[str, Any]:
    from knowledge_factory.economic_relationship_intelligence.production import company as rel_co

    return {"relationships": rel_co(cid), "provenance": _prov("relationships")}


def _alt(cid: str) -> dict[str, Any]:
    from knowledge_factory.alternative_data_intelligence.production import company as alt_co

    return {"alternative_data": alt_co(cid), "provenance": _prov("alternative_data")}


def _expectations(cid: str) -> dict[str, Any]:
    from knowledge_factory.market_expectations_intelligence.production import company as exp_co
    from knowledge_factory.market_expectations_intelligence.production import gap

    return {
        "expectations": exp_co(cid),
        "expectation_gap": gap(cid),
        "provenance": _prov("expectations"),
    }


def _government() -> dict[str, Any]:
    from knowledge_factory.government_intelligence.dashboard import government_dashboard

    return government_dashboard(ensure=False)


def _macro() -> dict[str, Any]:
    from knowledge_factory.store import repository as store

    return store.get_object("macro", "GLOBAL")


def _universe() -> dict[str, Any]:
    from universe_intelligence.dashboard import universe_health

    return universe_health(universe_id="NIFTY_500", ensure=False)


def _historical(cid: str) -> dict[str, Any]:
    from knowledge_factory.historical_depth import store as hd_store

    return {
        "object": hd_store.get_object("company", cid),
        "pack": hd_store.get_pack(cid),
        "provenance": _prov("historical"),
    }


def _decision_memory() -> dict[str, Any]:
    try:
        from institutional_reasoning.iro.memory import snapshot

        return snapshot()
    except Exception as exc:
        return {"unavailable": True, "error": str(exc)[:120]}


def _replay_index() -> dict[str, Any]:
    try:
        from decision_quality import store as idq_store

        ids = idq_store.list_decisions()
        return {"decision_ids": ids[:50], "n": len(ids)}
    except Exception as exc:
        return {"unavailable": True, "error": str(exc)[:120]}
