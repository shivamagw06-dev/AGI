"""IRP V1 pipeline — think before Ask AGI answers.

Uses existing KIP + RSP APIs only. No platform redesign.
"""

from __future__ import annotations

from typing import Any

from app.aws.adapters import dump, soft
from app.irp.contradictions import detect_contradictions
from app.irp.domain import classify_domain
from app.irp.entities import resolve_entities
from app.irp.intent import detect_intent
from app.irp.learning import IrpLearningStore
from app.irp.models import IrpPackage, RankedEvidenceItem
from app.irp.plan import build_research_plan
from app.irp.rank import filter_and_rank_evidence
from app.irp.reason import (
    build_company_intelligence,
    build_institutional_briefing,
    build_institutional_reasoning,
    build_sector_intelligence,
)
from app.irp.validate import validate_package
from app.kip.models import ClientSearchRequest
from app.ui.questions import follow_up_questions


class IrpPipeline:
    def __init__(
        self,
        *,
        kip: Any | None = None,
        rsp: Any | None = None,
        learning: IrpLearningStore | None = None,
    ) -> None:
        self.kip = kip
        self.rsp = rsp
        self.learning = learning or IrpLearningStore()

    def run(self, question: str, *, ticker: str | None = None) -> IrpPackage:
        q = (question or "").strip()

        # 1 Intent
        intent = detect_intent(q)
        # 2 Entities
        entities = resolve_entities(q, ticker=ticker)
        # 3 Domain
        domain = classify_domain(intent, entities)
        # 4 Plan
        plan = build_research_plan(q, intent=intent, domain=domain, entities=entities)

        # Learning cues (soft)
        cues = self.learning.cues_for(q)

        # 5a LEO — live evidence before Academy / SIF (additive; no redesign)
        leo_pkg: dict[str, Any] = {}
        try:
            from leo.production import package_for_query as leo_package

            leo_pkg = leo_package(
                q,
                ticker=ticker or entities.primary_ticker,
                engine="irp",
            ) or {}
        except Exception:
            leo_pkg = {}

        # 5b FAPI + SIF — sector framework then Finance Academy (consume LEO evidence)
        academy_pkg: dict[str, Any] = {}
        sif_pkg: dict[str, Any] = {}
        leo_supplied = (leo_pkg.get("sif_evidence_supplied") or {}) if isinstance(leo_pkg, dict) else {}
        try:
            from academy.fapi.production import package_for_query

            academy_pkg = package_for_query(q, engine="irp", ticker=ticker or entities.primary_ticker)
            sif_pkg = academy_pkg.get("sector_intelligence") or {}
        except Exception:
            academy_pkg = {}
            sif_pkg = {}
        if not sif_pkg or leo_supplied:
            try:
                from sif.production import analyse_query as sif_analyse

                sif_pkg = (
                    sif_analyse(
                        q,
                        ticker=ticker or entities.primary_ticker,
                        engine="irp",
                        evidence_supplied=leo_supplied or None,
                        kip=self.kip,
                    )
                    or sif_pkg
                    or {}
                )
            except Exception:
                if not sif_pkg:
                    sif_pkg = {}

        # 5 Knowledge retrieval via existing KIP client_search / rag (no redesign)
        client = {}
        house = None
        evidence_dicts: list[dict[str, Any]] = []
        primary = entities.primary_ticker if domain == "company" else None
        if self.kip and q:
            req = ClientSearchRequest(question=q, ticker=primary)
            client_obj = soft(self.kip.client_search, req)
            client = dump(client_obj) or {}
            house = client.get("house_view")
            evidence = client.get("evidence") or {}
            evidence_dicts.extend(_as_dict_list(evidence.get("supporting_evidence")))
            evidence_dicts.extend(_as_dict_list(evidence.get("conflicting_opinions")))
            # Extra focused RAG pass for sector universes
            if entities.sector_label:
                rag = soft(
                    self.kip.rag,
                    f"{entities.sector_label} outlook earnings demand",
                    ticker=None,
                    limit=10,
                )
                rag_d = dump(rag) or {}
                evidence_dicts.extend(_as_dict_list(rag_d.get("supporting_evidence")))
                evidence_dicts.extend(_as_dict_list(rag_d.get("conflicting_opinions")))

        # Prefer prior high-quality evidence ids when present in cues
        if cues.get("prefer_evidence"):
            for e in evidence_dicts:
                if not isinstance(e, dict):
                    continue
                eid = str(e.get("document_id") or e.get("id") or e.get("title") or "")
                if eid and any(eid in str(p) for p in cues["prefer_evidence"]):
                    e["confidence"] = max(float(e.get("confidence") or 0.5), 0.75)

        # Inject LEO verified evidence into the IRP evidence pool (before rank/reason)
        if isinstance(leo_pkg, dict) and leo_pkg.get("evidence_objects"):
            for o in (leo_pkg.get("evidence_objects") or [])[:24]:
                if not isinstance(o, dict):
                    continue
                evidence_dicts.append(
                    {
                        "id": o.get("evidence_id"),
                        "document_id": o.get("evidence_id"),
                        "title": o.get("title") or o.get("fact_key"),
                        "snippet": o.get("value_text"),
                        "source": o.get("source_id"),
                        "evidence_type": o.get("evidence_type"),
                        "confidence": o.get("confidence"),
                        "verification_status": o.get("verification_status"),
                        "leo": True,
                    }
                )

        # 6 Rank + reject unrelated
        ranked, rejected = filter_and_rank_evidence(evidence_dicts, entities=entities, plan=plan)

        # 8 Research Committee (RSP) — after retrieval/ranking
        rsp_pkg: dict[str, Any] = {}
        if self.rsp:
            rsp_ticker = primary
            # Sector subjects: do not invent fake tickers like SERVICES
            if not rsp_ticker and entities.tickers:
                rsp_ticker = entities.tickers[0]
            raw = soft(
                self.rsp.reason_for_writer,
                q or f"{entities.sector_label or rsp_ticker or 'markets'} institutional view",
                ticker=rsp_ticker,
            )
            rsp_pkg = dump(raw) if raw is not None and not isinstance(raw, dict) else (raw or {})
            if not isinstance(rsp_pkg, dict):
                rsp_pkg = {}

        # 7 Contradictions (merge ranked + RSP)
        contradictions = detect_contradictions(
            ranked,
            rsp_contradictions=(rsp_pkg.get("contradictions") if isinstance(rsp_pkg, dict) else None),
        )

        # 8 Institutional reasoning
        reasoning = build_institutional_reasoning(
            q,
            intent=intent,
            domain=domain,
            entities=entities,
            ranked=ranked,
            contradictions=contradictions,
            house_view=house if isinstance(house, dict) else None,
            rsp=rsp_pkg,
        )

        # 8b Enrich reasoning with LEO citations, then SIF, then Finance Academy
        try:
            from academy.fapi.production import enrich_reasoning as fapi_enrich
            from leo.production import enrich_reasoning as leo_enrich
            from sif.production import enrich_reasoning as sif_enrich

            enriched = reasoning.model_dump()
            if isinstance(leo_pkg, dict) and leo_pkg.get("enabled"):
                enriched = leo_enrich(enriched, leo_pkg)
                for hint in (leo_pkg.get("answer_hints") or [])[:2]:
                    why = list(enriched.get("why") or [])
                    if hint and hint not in why:
                        why.insert(0, hint)
                        enriched["why"] = why[:10]
            if sif_pkg.get("sector_id"):
                enriched = sif_enrich(enriched, sif_pkg)
            if academy_pkg.get("is_finance") and academy_pkg.get("concept_ids"):
                enriched = fapi_enrich(enriched, academy_pkg)
            for field in (
                "why",
                "what_is_happening",
                "key_drivers",
                "valuation_perspective",
                "supports",
                "stance",
                "outlook",
                "uncertainties",
            ):
                if field in enriched and enriched[field] is not None:
                    setattr(reasoning, field, enriched[field])
        except Exception:
            pass

        # 13 Self-check; rebuild once if needed
        validation = validate_package(
            q,
            entities=entities,
            ranked=ranked,
            rejected=rejected,
            reasoning=reasoning,
        )
        if not validation.passed:
            # Rebuild: drop weak evidence and re-reason
            ranked = [r for r in ranked if r.relevance_score >= 0.35] or ranked[:4]
            reasoning = build_institutional_reasoning(
                q,
                intent=intent,
                domain=domain,
                entities=entities,
                ranked=ranked,
                contradictions=contradictions,
                house_view=house if isinstance(house, dict) else None,
                rsp=rsp_pkg,
            )
            try:
                from academy.fapi.production import enrich_reasoning as fapi_enrich
                from sif.production import enrich_reasoning as sif_enrich

                enriched = reasoning.model_dump()
                if sif_pkg.get("sector_id"):
                    enriched = sif_enrich(enriched, sif_pkg)
                if academy_pkg.get("is_finance") and academy_pkg.get("concept_ids"):
                    enriched = fapi_enrich(enriched, academy_pkg)
                for field in (
                    "why",
                    "what_is_happening",
                    "key_drivers",
                    "valuation_perspective",
                    "supports",
                    "stance",
                    "outlook",
                    "uncertainties",
                ):
                    if field in enriched and enriched[field] is not None:
                        setattr(reasoning, field, enriched[field])
            except Exception:
                pass
            validation = validate_package(
                q,
                entities=entities,
                ranked=ranked,
                rejected=rejected,
                reasoning=reasoning,
            )
            validation.rebuilt = True

        # Follow-ups
        followups = follow_up_questions(
            question=q,
            intent=intent,
            related_companies=entities.tickers[:6],
            related_themes=entities.themes[:6],
            house_label=reasoning.stance,
            risks=reasoning.risks,
            catalysts=reasoning.catalysts,
            knowledge_graph=None,
            recent_research_titles=[r.title for r in ranked[:4] if r.title],
        )

        briefing = build_institutional_briefing(reasoning, question=q)
        if isinstance(briefing, dict):
            if academy_pkg.get("concept_ids"):
                briefing = {
                    **briefing,
                    "finance_academy": {
                        "concept_ids": academy_pkg.get("concept_ids"),
                        "causal_models": [c.get("model_id") for c in (academy_pkg.get("causal_models") or [])],
                        "mental_models": [m.get("model_id") for m in (academy_pkg.get("mental_models") or [])],
                        "answer_hints": academy_pkg.get("answer_hints") or [],
                    },
                }
            if sif_pkg.get("sector_id"):
                briefing = {
                    **briefing,
                    "sector_intelligence": {
                        "sector_id": sif_pkg.get("sector_id"),
                        "framework_version": sif_pkg.get("framework_version"),
                        "kpis_retrieved": sif_pkg.get("kpis_retrieved"),
                        "valuation_framework": sif_pkg.get("valuation_framework"),
                        "recommendation_gate": sif_pkg.get("recommendation_gate"),
                        "trace": sif_pkg.get("trace"),
                    },
                }
            if isinstance(leo_pkg, dict) and leo_pkg.get("enabled"):
                briefing = {
                    **briefing,
                    "live_evidence": {
                        "leo_version": leo_pkg.get("leo_version"),
                        "sources_used": leo_pkg.get("sources_used"),
                        "evidence_count": leo_pkg.get("evidence_count"),
                        "evidence_confidence": leo_pkg.get("evidence_confidence"),
                        "missing_evidence": leo_pkg.get("missing_evidence"),
                        "quality_gate": leo_pkg.get("quality_gate"),
                        "api_calls": len(leo_pkg.get("api_calls") or []),
                    },
                }
        sector_intel = build_sector_intelligence(entities, reasoning)
        company_intel = build_company_intelligence(entities, reasoning)
        sector_pkg = dump(sector_intel) if not isinstance(sector_intel, dict) else dict(sector_intel)
        if not isinstance(sector_pkg, dict):
            sector_pkg = {}
        if isinstance(sif_pkg, dict) and sif_pkg:
            sector_pkg = {**sector_pkg, "sif": sif_pkg}

        package = IrpPackage(
            question=q,
            intent=intent,
            domain=domain,
            entities=entities,
            research_plan=plan,
            ranked_evidence=ranked,
            rejected_evidence=rejected[:20],
            contradictions=contradictions,
            reasoning=reasoning,
            validation=validation,
            client_search=client if isinstance(client, dict) else {},
            house_view=house if isinstance(house, dict) else None,
            rsp=rsp_pkg,
            follow_ups=followups[:8],
            institutional_briefing=briefing,
            sector_intelligence=sector_pkg,
            company_intelligence=company_intel,
            finance_academy=academy_pkg if isinstance(academy_pkg, dict) else {},
            live_evidence=leo_pkg if isinstance(leo_pkg, dict) else {},
        )

        # 14 Learning loop
        self.learning.record(package)
        return package


def _as_dict_list(items: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for x in items or []:
        if isinstance(x, dict):
            out.append(x)
        else:
            d = dump(x)
            if isinstance(d, dict):
                out.append(d)
    return out
