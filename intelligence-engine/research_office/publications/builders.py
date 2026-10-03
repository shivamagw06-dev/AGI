"""Build knowledge-only morning publications from soft-read knowledge."""

from __future__ import annotations

from typing import Any

from research_office import store
from research_office.publications.gates import validate_publication
from research_office.publications.registry import register_publication
from research_office.templates import knowledge as kn


def _obs(payload: dict[str, Any], label: str) -> list[str]:
    if payload.get("unavailable"):
        return [f"{label}: unavailable — transparent insufficiency"]
    keys = [k for k in payload.keys() if k not in {"fabricated", "error", "unavailable"}][:12]
    return [f"{label}: observed keys {keys}"] if keys else [f"{label}: empty snapshot"]


def _evidence_present(sources: list[dict[str, Any]], payloads: list[dict[str, Any]]) -> bool:
    """Provenanced KF soft-reads count as evidence attempts.

    Unavailable layers are transparent insufficiency inside the publication body,
    not a silent fabrication. Completely missing sources ⇒ evidence_missing.
    """
    if not sources:
        return False
    if any(s.get("provenance") for s in sources):
        return True
    return any(not (p or {}).get("unavailable") for p in payloads)


def _historical_analogues_section(
    *,
    title: str,
    covered_entities: list[str] | None = None,
) -> dict[str, Any]:
    """Soft-wire IMAI — only when validated historical memories exist."""
    try:
        from institutional_analog_intelligence.production import retrieve

        pack = retrieve(
            question=title,
            playbook=None,
            evidence_graph={
                "entities": list(covered_entities or []),
                "chain_bullets": [],
            },
            as_of=None,
            top_k=4,
        )
        if not pack.get("have_we_seen_this_before"):
            return {
                "historical_analogues": [],
                "previous_comparable_events": [],
                "lessons_from_history": [],
                "imai_version": pack.get("imai_version"),
                "omitted_no_evidence": True,
            }
        return {
            "historical_analogues": list(pack.get("surface_bullets") or [])[:5],
            "previous_comparable_events": [
                f"{m.get('memory_id')}: {m.get('title')}" for m in (pack.get("memories") or [])[:4]
            ],
            "lessons_from_history": list((pack.get("comparison") or {}).get("similarities") or [])[:4],
            "imai_version": pack.get("imai_version"),
            "top_memory_ids": pack.get("top_memory_ids") or [],
            "omitted_no_evidence": False,
            "invented_analogues": False,
        }
    except Exception:
        return {
            "historical_analogues": [],
            "previous_comparable_events": [],
            "lessons_from_history": [],
            "omitted_no_evidence": True,
        }


def build_all_morning_publications(*, scheduler_run_id: str | None = None) -> list[dict[str, Any]]:
    versions = kn.knowledge_versions()
    # Soft-wire IERE — retrieve best evidence before publication generation (no pub logic change).
    best_evidence = kn.read_best_evidence(
        question="What institutional evidence supports today's research office publications?"
    )
    sched = kn.read_scheduler_context()
    iks = kn.read_iks_dashboard()
    coverage = kn.read_coverage()
    macro = kn.read_macro()
    gov = kn.read_government()
    industry = kn.read_industry()
    events = kn.read_corporate_events()
    alt = kn.read_alternative_data()
    exp = kn.read_expectations()
    company = kn.read_company_intelligence()

    pubs: list[dict[str, Any]] = []

    pubs.append(
        _publish(
            title="Market Morning Brief",
            publication_type="market_morning_brief",
            sections={
                "market_overview": _obs(iks, "institutional_knowledge_stack"),
                "global_context": _obs(macro, "macro"),
                "todays_agenda": _obs(sched, "scheduler"),
                "major_overnight_developments": _obs(events, "corporate_events"),
                "key_events": _obs(gov, "government"),
                "ranked_evidence": _obs(best_evidence, "evidence_retrieval"),
            },
            payloads=[iks, macro, sched, events, gov, best_evidence],
            source_names=[
                ("iks", iks),
                ("macro", macro),
                ("scheduler", sched),
                ("corporate_events", events),
                ("government", gov),
                ("evidence_retrieval", best_evidence),
            ],
            coverage={"morning": coverage, "fabricated": False},
            versions=versions,
            scheduler_run_id=scheduler_run_id,
        )
    )

    pubs.append(
        _publish(
            title="Macro Intelligence Brief",
            publication_type="macro_intelligence_brief",
            sections={
                "macro_dashboard": _obs(macro, "macro_object"),
                "rates": ["Rates: see macro snapshot — no fabricated series"],
                "inflation": ["Inflation: see macro snapshot — UNKNOWN if absent"],
                "gdp": ["GDP: see macro snapshot — UNKNOWN if absent"],
                "liquidity": ["Liquidity: UNKNOWN unless present in macro object"],
                "credit": ["Credit: cross-ref alternative data bank credit if present"],
                "fx": ["FX: UNKNOWN unless present in macro object"],
                "alternative_data_changes": _obs(alt, "alternative_data"),
                "macro_observations": _obs(macro, "macro"),
            },
            payloads=[macro, alt],
            source_names=[("macro", macro), ("alternative_data", alt)],
            coverage={"fabricated": False},
            versions=versions,
            scheduler_run_id=scheduler_run_id,
        )
    )

    pubs.append(
        _publish(
            title="Government Intelligence Brief",
            publication_type="government_intelligence_brief",
            sections={
                "rbi": ["RBI: from government intelligence dashboard"],
                "budget": ["Budget: from government intelligence dashboard"],
                "sebi": ["SEBI: from government intelligence dashboard"],
                "gst": ["GST: from government intelligence dashboard"],
                "pli": ["PLI: from government intelligence dashboard"],
                "trade": ["Trade: from government intelligence dashboard"],
                "policy_changes": _obs(gov, "government"),
                "transmission_summary": [
                    "Transmission: descriptive only — no portfolio implications"
                ],
            },
            payloads=[gov],
            source_names=[("government", gov)],
            coverage={"fabricated": False},
            versions=versions,
            scheduler_run_id=scheduler_run_id,
        )
    )

    pubs.append(
        _publish(
            title="Sector Intelligence Report",
            publication_type="sector_intelligence_report",
            sections={
                "current_state": _obs(company, "company_intelligence"),
                "valuation": ["Valuation context: evidence-backed fields only; else UNKNOWN"],
                "historical_context": ["Historical: via KF/HD when available"],
                "alternative_data": _obs(alt, "alternative_data"),
                "macro_sensitivity": _obs(macro, "macro"),
                "government_impacts": _obs(gov, "government"),
                "key_observations": _obs(iks, "iks"),
            },
            payloads=[company, alt, macro, gov, iks],
            source_names=[
                ("company_intelligence", company),
                ("alternative_data", alt),
                ("macro", macro),
                ("government", gov),
            ],
            coverage={"fabricated": False},
            versions=versions,
            scheduler_run_id=scheduler_run_id,
        )
    )

    pubs.append(
        _publish(
            title="Industry Intelligence Report",
            publication_type="industry_intelligence_report",
            sections={
                "business_model_observations": _obs(industry, "industry"),
                "value_chain_developments": ["Value chain: from industry intelligence"],
                "cost_changes": ["Cost changes: UNKNOWN unless evidenced"],
                "supply_chain_changes": ["Supply chain: UNKNOWN unless evidenced"],
                "industry_cycles": ["Industry cycles: descriptive observations only"],
            },
            payloads=[industry],
            source_names=[("industry", industry)],
            coverage={"fabricated": False},
            versions=versions,
            scheduler_run_id=scheduler_run_id,
        )
    )

    pubs.append(
        _publish(
            title="Corporate Events Report",
            publication_type="corporate_events_report",
            sections={
                "results": ["Results: from corporate events intelligence"],
                "guidance": ["Guidance: from events / expectations layers"],
                "ceo_changes": ["CEO changes: timeline when present"],
                "buybacks": ["Buybacks: timeline when present"],
                "acquisitions": ["Acquisitions: timeline when present"],
                "contracts": ["Contracts: timeline when present"],
                "litigation": ["Litigation: timeline when present"],
                "regulatory_actions": ["Regulatory actions: timeline when present"],
                "timeline_updates": _obs(events, "corporate_events"),
            },
            payloads=[events],
            source_names=[("corporate_events", events)],
            coverage={"fabricated": False},
            versions=versions,
            scheduler_run_id=scheduler_run_id,
        )
    )

    pubs.append(
        _publish(
            title="Alternative Data Report",
            publication_type="alternative_data_report",
            sections={
                "upi": ["UPI: trend change only if dataset present"],
                "electricity": ["Electricity: trend change only if dataset present"],
                "rail_freight": ["Rail Freight: trend change only if dataset present"],
                "port_cargo": ["Port Cargo: trend change only if dataset present"],
                "gst": ["GST: trend change only if dataset present"],
                "vehicle_registrations": ["Vehicle Registrations: trend only if present"],
                "bank_credit": ["Bank Credit: trend only if present"],
                "rainfall": ["Rainfall: trend only if present"],
                "air_traffic": ["Air Traffic: trend only if present"],
                "trend_changes": _obs(alt, "alternative_data"),
            },
            payloads=[alt],
            source_names=[("alternative_data", alt)],
            coverage={"fabricated": False},
            versions=versions,
            scheduler_run_id=scheduler_run_id,
        )
    )

    pubs.append(
        _publish(
            title="Market Expectations Report",
            publication_type="market_expectations_report",
            sections={
                "guidance_changes": _obs(exp, "expectations"),
                "expectation_revisions": ["Revisions: from expectations intelligence"],
                "new_surprises": ["Surprises: from expectations intelligence"],
                "narrative_evolution": ["Narratives: descriptive only"],
                "expectation_gaps": ["Gaps: reality vs expectations — knowledge only"],
            },
            payloads=[exp],
            source_names=[("expectations", exp)],
            coverage={"fabricated": False},
            versions=versions,
            scheduler_run_id=scheduler_run_id,
        )
    )

    return pubs


def build_company_note(
    ticker: str,
    *,
    scheduler_run_id: str | None = None,
    trigger_reason: str = "new_evidence",
) -> dict[str, Any]:
    versions = kn.knowledge_versions()
    t = str(ticker or "").upper()
    # Soft-wire IERE ranked evidence for company notes (publication body unchanged).
    best_evidence = kn.read_best_evidence(t)
    bundle = kn.read_company_bundle(t)
    feed = kn.read_evidence_feed(t)
    gov = kn.read_government()
    macro = kn.read_macro()
    alt = kn.read_alternative_data()
    exp = kn.read_expectations()
    industry = kn.read_industry()

    insufficient = []
    for name, payload in (
        ("company_bundle", bundle),
        ("evidence_feed", feed),
        ("macro", macro),
        ("government", gov),
        ("alternative_data", alt),
        ("expectations", exp),
        ("industry", industry),
    ):
        if payload.get("unavailable") or payload.get("insufficient"):
            insufficient.append(name)

    return _publish(
        title=f"Company Research Note — {t}",
        publication_type="company_research_note",
        sections={
            "company": t,
            "summary": [f"Evidence-triggered note ({trigger_reason}) — no recommendation"],
            "evidence": _obs(feed, "evidence_feed"),
            "ranked_evidence": _obs(best_evidence, "evidence_retrieval"),
            "historical_context": ["Historical: from bundle/HD when present"],
            "sector_context": _obs(industry, "industry"),
            "macro_context": _obs(macro, "macro"),
            "government_context": _obs(gov, "government"),
            "alternative_data_context": _obs(alt, "alternative_data"),
            "expectation_context": _obs(exp, "expectations"),
            "transparent_insufficiency": insufficient or ["none_declared"],
            "bundle_keys": list(bundle.keys())[:20],
        },
        payloads=[bundle, feed, best_evidence, macro, gov, alt, exp, industry],
        source_names=[
            ("company_bundle", bundle),
            ("evidence_feed", feed),
            ("evidence_retrieval", best_evidence),
            ("macro", macro),
            ("government", gov),
            ("alternative_data", alt),
            ("expectations", exp),
            ("industry", industry),
        ],
        coverage={"ticker": t, "fabricated": False},
        versions=versions,
        scheduler_run_id=scheduler_run_id,
        covered_entities=[t],
        evidence_pack_versions={"evidence_feed": (feed or {}).get("version") or versions["evidence_version"]},
    )


def _publish(
    *,
    title: str,
    publication_type: str,
    sections: dict[str, Any],
    payloads: list[dict[str, Any]],
    source_names: list[tuple[str, dict[str, Any]]],
    coverage: dict[str, Any],
    versions: dict[str, str],
    scheduler_run_id: str | None,
    covered_entities: list[str] | None = None,
    evidence_pack_versions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sources = [kn.source_ref(n, p) for n, p in source_names]
    # Soft-wire IMAI historical analogues — only when evidence/memories exist
    analog_sec = _historical_analogues_section(
        title=title,
        covered_entities=covered_entities,
    )
    if not analog_sec.get("omitted_no_evidence"):
        sections = {
            **sections,
            "historical_analogues": analog_sec.get("historical_analogues") or [],
            "previous_comparable_events": analog_sec.get("previous_comparable_events") or [],
            "lessons_from_history": analog_sec.get("lessons_from_history") or [],
        }
    body = {
        "as_of": store.utc_now(),
        "snapshot": {
            "publication_type": publication_type,
            "scheduler_run_id": scheduler_run_id,
            "knowledge_version": versions["knowledge_version"],
            "evidence_version": versions["evidence_version"],
            "imai_version": analog_sec.get("imai_version"),
            "imai_top_memory_ids": analog_sec.get("top_memory_ids") or [],
        },
        "sections": sections,
        "recommendation": None,
        "knowledge_only": True,
    }
    evidence_present = _evidence_present(sources, payloads)
    # If all unavailable, still publish with insufficiency but gate fails
    validation = validate_publication(
        body=body,
        sources=sources,
        knowledge_version=versions.get("knowledge_version"),
        evidence_version=versions.get("evidence_version"),
        coverage=coverage,
        evidence_present=evidence_present,
    )
    # AGIB v3.4 Track C — soft-wire IFSE metadata (publication body unchanged)
    fw_meta = _select_publication_frameworks(
        title=title,
        publication_type=publication_type,
        covered_entities=covered_entities or [],
    )
    # AGIB v3.4 Track D — soft-wire ICE template render into body.communication
    ice = _render_publication_communication(
        title=title,
        publication_type=publication_type,
        covered_entities=covered_entities or [],
        fw_meta=fw_meta,
        sections=sections,
    )
    if ice:
        body = {**body, "communication": ice}
    return register_publication(
        title=title,
        publication_type=publication_type,
        body=body,
        knowledge_version=versions["knowledge_version"],
        evidence_version=versions["evidence_version"],
        evidence_pack_versions=evidence_pack_versions or {"soft_dashboard": versions["evidence_version"]},
        covered_entities=covered_entities or [],
        coverage=coverage,
        sources=sources,
        validation=validation,
        scheduler_run_id=scheduler_run_id,
        framework_used=fw_meta.get("framework_used"),
        framework_confidence=fw_meta.get("framework_confidence"),
        framework_version=fw_meta.get("framework_version"),
        framework_explanation=fw_meta.get("framework_explanation"),
    )


def _select_publication_frameworks(
    *,
    title: str,
    publication_type: str,
    covered_entities: list[str],
) -> dict[str, Any]:
    try:
        from framework_selection import IFSE_VERSION, select_frameworks
        from framework_selection import store as ifse_store

        intent_map = {
            "macro_intelligence_brief": "Macro",
            "government_intelligence_brief": "Government",
            "sector_intelligence_report": "Industry",
            "industry_intelligence_report": "Industry",
            "company_research_note": "Analyse",
            "market_morning_brief": "CrossDomain",
            "corporate_events_report": "CorporateEvents",
            "alternative_data_report": "Analyse",
            "market_expectations_report": "Analyse",
        }
        ticker = covered_entities[0] if covered_entities else None
        entities = (
            [{"type": "company", "id": ticker, "confidence": 0.99}] if ticker else []
        )
        intent_v2 = intent_map.get(publication_type, "Analyse")
        sel = select_frameworks(
            question=title,
            intent_v2=intent_v2,
            entities=entities,
            ticker_hint=ticker,
            concept_mode=not bool(ticker),
        )
        ifse_store.record_selection(sel)
        # AGIB v3.5 — soft-wire IAP after frameworks
        playbook_meta: dict[str, Any] = {}
        try:
            from institutional_playbooks import IAP_VERSION, select_playbook
            from institutional_playbooks import store as iap_store

            pb = select_playbook(
                question=title,
                intent_v2=intent_v2,
                sector=sel.get("sector"),
                framework_ids=list(sel.get("framework_ids") or []),
                framework_selection=sel,
                concept_mode=not bool(ticker),
            )
            iap_store.record_selection(pb)
            playbook_meta = {
                "playbook_id": pb.get("playbook_id"),
                "playbook_name": pb.get("playbook_name"),
                "category": pb.get("category"),
                "checklist": pb.get("checklist"),
                "procedure": pb.get("procedure"),
                "common_mistakes": pb.get("common_mistakes"),
                "output_structure": pb.get("output_structure"),
                "explanation": pb.get("explanation"),
                "confidence": pb.get("confidence"),
                "iap_version": pb.get("iap_version") or IAP_VERSION,
                "guides_reasoning": True,
            }
        except Exception:
            playbook_meta = {}
        return {
            "framework_used": list(sel.get("framework_ids") or []),
            "framework_confidence": sel.get("confidence") or {},
            "framework_version": sel.get("ifse_version") or IFSE_VERSION,
            "framework_explanation": sel.get("explanation"),
            "playbook_selection": playbook_meta,
        }
    except Exception as exc:
        return {
            "framework_used": [],
            "framework_confidence": {"error": str(exc)[:120]},
            "framework_version": None,
            "framework_explanation": None,
            "playbook_selection": {},
        }


def _render_publication_communication(
    *,
    title: str,
    publication_type: str,
    covered_entities: list[str],
    fw_meta: dict[str, Any],
    sections: dict[str, Any],
) -> dict[str, Any] | None:
    """Soft-wire ICE — publication logic unchanged; add communication render."""
    try:
        from institutional_communication.production import communicate
        from institutional_communication.schema import ICE_VERSION

        intent_map = {
            "macro_intelligence_brief": "Macro",
            "government_intelligence_brief": "Government",
            "sector_intelligence_report": "Industry",
            "industry_intelligence_report": "Industry",
            "company_research_note": "Analyse",
            "market_morning_brief": "CrossDomain",
            "corporate_events_report": "CorporateEvents",
            "alternative_data_report": "Analyse",
            "market_expectations_report": "Analyse",
        }
        intent = intent_map.get(publication_type, "Analyse")
        ia = {
            "format": "institutional_answer_v1",
            "question": title,
            "intent_v2": intent,
            "question_type": publication_type,
            "concept_mode": not bool(covered_entities),
            "as_of": None,
            "sections": {
                "executive_summary": {
                    "bullets": list((sections.get("summary") or [])[:4]),
                    "evidence_ids": [],
                },
                "evidence": {
                    "bullets": list((sections.get("evidence") or [])[:8]),
                    "evidence_ids": [],
                },
                "analysis": {
                    "bullets": list((sections.get("summary") or [])[:4]),
                    "evidence_ids": [],
                },
                "risks": {
                    "bullets": list((sections.get("transparent_insufficiency") or ["none"])[:4]),
                    "evidence_ids": [],
                },
                "confidence": {"bullets": [], "evidence_ids": []},
                "sources": {"bullets": [], "evidence_ids": []},
                "framework": {"bullets": [], "evidence_ids": []},
                "conclusion": {"bullets": [], "evidence_ids": []},
            },
            "evidence": {"items": [], "pack_names": [], "iere_ranked_count": 0},
            "frameworks": {
                "framework_ids": fw_meta.get("framework_used") or [],
                "selected": [
                    {"framework_id": fid, "name": fid, "role": "primary"}
                    for fid in (fw_meta.get("framework_used") or [])[:3]
                ],
                "primary": [
                    {"framework_id": fid, "name": fid, "role": "primary"}
                    for fid in (fw_meta.get("framework_used") or [])[:2]
                ],
                "secondary": [],
                "supporting": [],
                "forbidden_rejected": [],
                "explanation": fw_meta.get("framework_explanation") or {},
                "confidence": fw_meta.get("framework_confidence") or {},
            },
            "playbook": fw_meta.get("playbook_selection") or {},
            "institutional_memory": {
                "have_we_seen_this_before": bool(sections.get("historical_analogues")),
                "surface_bullets": list(sections.get("historical_analogues") or [])[:5],
                "top_memory_ids": [],
                "comparison": {
                    "similarities": list(sections.get("lessons_from_history") or [])[:4],
                },
                "guides_memory": True,
                "invented_analogues": False,
            },
            "gaps": {"missing_domains": [], "coverage": 0.5, "tell_reasoning": "Publication soft-wire"},
            "confidence": fw_meta.get("framework_confidence") or {"band": "Moderate", "score": 0.65},
            "citations": {},
            "risk_signals": {
                "missing_domains": [],
                "tell_reasoning": "Publication soft-wire",
                "disagreements": [],
            },
            "replay": {},
            "fabricated": False,
        }
        out = communicate(ia)
        return {
            "ice_version": out.get("ice_version") or ICE_VERSION,
            "template": out.get("template"),
            "executive_summary": out.get("executive_summary"),
            "section_order": out.get("section_order"),
            "framework_visible": out.get("framework_visible"),
            "playbook_visible": out.get("playbook_visible"),
            "playbook_id": out.get("playbook_id"),
            "validation": out.get("validation"),
            "llm_used": False,
            "fabricated": False,
        }
    except Exception:
        return None
