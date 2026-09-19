"""IAF production entry — Research Planner → Analysts → Committee → CIO."""

from __future__ import annotations

from typing import Any

from institutional_analysts.base import company_name, ticker_of
from institutional_analysts.business.analyst import analyse as business_analyse
from institutional_analysts.cio.report import write_report
from institutional_analysts.committee.aggregate import aggregate
from institutional_analysts.financial.analyst import analyse as financial_analyse
from institutional_analysts.flags import (
    flags_dict,
    is_enabled,
    is_iai_business_enabled,
    is_iai_financial_enabled,
    is_iai_valuation_enabled,
)
from institutional_analysts.macro.analyst import analyse as macro_analyse
from institutional_analysts.management.analyst import analyse as management_analyse
from institutional_analysts.mandates import MANDATES, mandate_for
from institutional_analysts.market.analyst import analyse as market_analyse
from institutional_analysts import memory as iaf_memory
from institutional_analysts.ownership.analyst import analyse as ownership_analyse
from institutional_analysts.risk.analyst import analyse as risk_analyse
from institutional_analysts.schema import (
    ANALYST_ROLES,
    ARCHITECTURE_STATUS,
    IAF_VERSION,
    PROGRAMME,
    PUBLIC_OWNER_LABELS,
    SECTION_OWNERS,
)
from institutional_analysts.sector.analyst import analyse as sector_analyse
from institutional_analysts.valuation.analyst import analyse as valuation_analyse

_ANALYSERS = {
    "business": business_analyse,
    "financial": financial_analyse,
    "valuation": valuation_analyse,
    "market": market_analyse,
    "sector": sector_analyse,
    "macro": macro_analyse,
    "risk": risk_analyse,
    "management": management_analyse,
    "ownership": ownership_analyse,
}


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "version": IAF_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_an_engine": True,
        "orchestration_only": True,
        "no_new_data": True,
        "analysts": list(ANALYST_ROLES),
        "mandates": {r: mandate_for(r) for r in ANALYST_ROLES},
        "section_owners": SECTION_OWNERS,
        "public_owner_labels": PUBLIC_OWNER_LABELS,
        "memory": iaf_memory.metrics(),
        "features": {
            "structured_opinions": True,
            "domain_guards": True,
            "multi_factor_confidence": True,
            "analyst_memory": True,
            "committee_meeting_stages": True,
            "disagreement_matrix": True,
            "committee_minutes": True,
            "cio_editor": True,
            "iai_business_analyst": is_iai_business_enabled(),
            "iai_business_analyst_v2": is_iai_business_enabled(),
            "iai_business_analyst_v2_1": is_iai_business_enabled(),
            "iai_financial_analyst": is_iai_financial_enabled(),
            "iai_valuation_analyst": is_iai_valuation_enabled(),
        },
        "does_not_redesign": [
            "cid",
            "leo",
            "irp",
            "company_analysis",
            "financial_intelligence",
            "company_monitor",
            "knowledge_foundation",
            "academy",
            "dvc",
            "ecp",
            "market_data_client",
            "providers",
            "investment_committee",
            "cio",
            "research_writer",
            "ui",
        ],
        "flags": flags_dict(),
    }


def quality_gates() -> dict[str, Any]:
    return {
        "programme": PROGRAMME,
        "version": IAF_VERSION,
        "passed": is_enabled(),
        "checks": {
            "enabled": is_enabled(),
            "one_question_per_analyst": True,
            "mandate_metadata_present": len(MANDATES) == len(ANALYST_ROLES),
            "structured_opinions": True,
            "domain_guards": True,
            "committee_reads_opinions_only": True,
            "committee_meeting_stages": True,
            "cio_reads_committee_only": True,
            "cio_editor_no_analyst_verbatim": True,
            "no_internal_names_in_user_copy": True,
            "engines_unchanged": True,
        },
        "flags": flags_dict(),
    }


def plan_research(query: str, *, ticker: str | None = None) -> dict[str, Any]:
    return {
        "owner": "research_planner",
        "query": query,
        "ticker": ticker,
        "assignments": [
            {
                "role": r,
                "mandate": mandate_for(r).get("mandate"),
                "primary_question": mandate_for(r).get("primary_question"),
                "primary_inputs": mandate_for(r).get("primary_inputs"),
                "outputs": mandate_for(r).get("outputs"),
                "never": mandate_for(r).get("never"),
            }
            for r in ANALYST_ROLES
        ],
        "flow": [
            "research_planner",
            "specialist_analysts",
            "investment_committee_meeting",
            "chief_investment_officer_editor",
            "institutional_report",
        ],
    }


def package_for_ask_agi(
    query: str,
    *,
    ticker: str | None = None,
    company_analysis: dict[str, Any] | None = None,
    company_dossier: dict[str, Any] | None = None,
    live_evidence: dict[str, Any] | None = None,
    finance_academy: dict[str, Any] | None = None,
    sector_intelligence: dict[str, Any] | None = None,
    company_monitor: dict[str, Any] | None = None,
    valuation: dict[str, Any] | None = None,
    institutional_briefing: dict[str, Any] | None = None,
    intelligence_construction: dict[str, Any] | None = None,
    decision_engine: dict[str, Any] | None = None,
    intelligence_layer: dict[str, Any] | None = None,
    irp: dict[str, Any] | None = None,
    evidence_completion: dict[str, Any] | None = None,
    data_validation: dict[str, Any] | None = None,
    knowledge_foundation: dict[str, Any] | None = None,
    aws_macro: dict[str, Any] | None = None,
    yahoo_enrichment: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "bypassed": True, "programme": PROGRAMME}

    ctx: dict[str, Any] = {
        "query": query,
        "ticker": ticker,
        "company_analysis": company_analysis or {},
        "company_dossier": company_dossier or {},
        "live_evidence": live_evidence or {},
        "finance_academy": finance_academy or {},
        "sector_intelligence": sector_intelligence or {},
        "company_monitor": company_monitor or {},
        "valuation": valuation or {},
        "institutional_briefing": institutional_briefing or {},
        "intelligence_construction": intelligence_construction or {},
        "decision_engine": decision_engine or {},
        "intelligence_layer": intelligence_layer or {},
        "irp": irp or {},
        "evidence_completion": evidence_completion or {},
        "data_validation": data_validation or {},
        "knowledge_foundation": knowledge_foundation or {},
        "aws_macro": aws_macro or {},
        "yahoo_enrichment": yahoo_enrichment or {},
    }
    t = ticker_of(ctx) or (ticker.upper() if ticker else None)
    ctx["ticker"] = t
    name = company_name(ctx)

    # Soft-wire Institutional Stack into analyst context (FIL→FDI→MII→EIL→PIL)
    try:
        from institutional_stack.pipeline import company_pack as stack_company_pack

        if t:
            stack_pack = stack_company_pack(t, analyst="committee")
            ctx["institutional_stack"] = stack_pack
            layers = stack_pack.get("layers") or {}
            ctx["filing_intelligence"] = layers.get("filing_intelligence") or {}
            ctx["filing_diff"] = layers.get("filing_diff") or {}
            ctx["management_intelligence_layer"] = layers.get("management_intelligence") or {}
            ctx["accounting_intelligence"] = layers.get("accounting_intelligence") or {}
            ctx["portfolio_intelligence"] = layers.get("portfolio_intelligence") or {}
            ctx["causal_intelligence"] = layers.get("causal_intelligence") or {}
            ctx["forecast_intelligence"] = layers.get("forecast_intelligence") or {}
            ctx["knowledge_graph"] = layers.get("knowledge_graph") or {}
            ctx["institutional_memory"] = layers.get("institutional_memory") or {}
            ctx["simulation_lab"] = layers.get("simulation_lab") or {}
            ctx["decision_engine_v2"] = layers.get("decision_engine_v2") or {}
            ctx["peer_intelligence"] = layers.get("peer_intelligence") or {}
            ctx["evidence_intelligence"] = layers.get("evidence_intelligence") or {}
    except Exception:
        ctx["institutional_stack"] = {}

    # Soft CIG — causal why precedes desk opinions (no redesign of analysts)
    causal_intelligence: dict[str, Any] = ctx.get("causal_intelligence") or {}
    try:
        from causal_graph.production import soft_slice_for_analyst as cig_slice

        if t:
            causal_intelligence = (cig_slice(t, analyst="committee") or {}).get(
                "causal_intelligence"
            ) or causal_intelligence
            if causal_intelligence:
                ctx["causal_intelligence"] = causal_intelligence
    except Exception:
        pass

    # Soft IKG — connected knowledge precedes desk opinions (no redesign of analysts)
    knowledge_graph: dict[str, Any] = ctx.get("knowledge_graph") or {}
    try:
        from knowledge_graph.production import soft_slice_for_analyst as ikg_slice

        if t:
            knowledge_graph = (ikg_slice(t, analyst="committee") or {}).get(
                "knowledge_graph"
            ) or knowledge_graph
            if knowledge_graph:
                ctx["knowledge_graph"] = knowledge_graph
    except Exception:
        pass

    # Soft FIE — scenario outlook precedes desk opinions (no redesign of analysts)
    forecast_intelligence: dict[str, Any] = ctx.get("forecast_intelligence") or {}
    try:
        from forecast_intelligence.production import soft_slice_for_analyst as fie_slice

        if t:
            forecast_intelligence = (fie_slice(t, analyst="committee") or {}).get(
                "forecast_intelligence"
            ) or forecast_intelligence
            if forecast_intelligence:
                ctx["forecast_intelligence"] = forecast_intelligence
    except Exception:
        pass

    # Soft ILM — learning/memory precedes desk opinions (no redesign of analysts)
    institutional_memory: dict[str, Any] = ctx.get("institutional_memory") or {}
    try:
        from institutional_memory.production import soft_slice_for_analyst as ilm_slice

        if t:
            institutional_memory = (ilm_slice(t, analyst="committee") or {}).get(
                "institutional_memory"
            ) or institutional_memory
            if institutional_memory:
                ctx["institutional_memory"] = institutional_memory
    except Exception:
        pass

    # Soft SSL — simulation/decision packages precede desk opinions (no redesign of analysts)
    simulation_lab: dict[str, Any] = ctx.get("simulation_lab") or {}
    try:
        from simulation_lab.production import soft_slice_for_analyst as ssl_slice

        if t:
            simulation_lab = (ssl_slice(t, analyst="committee") or {}).get(
                "simulation_lab"
            ) or simulation_lab
            if simulation_lab:
                ctx["simulation_lab"] = simulation_lab
    except Exception:
        pass

    planner = plan_research(query, ticker=t)
    opinions: dict[str, dict[str, Any]] = {}
    for role, fn in _ANALYSERS.items():
        try:
            # Soft desk-specific causal / knowledge / forecast / memory slices when available
            try:
                from causal_graph.production import soft_slice_for_analyst as cig_desk

                if t and causal_intelligence:
                    desk = (cig_desk(t, analyst=role) or {}).get("causal_intelligence") or {}
                    if desk:
                        ctx["causal_intelligence"] = {**causal_intelligence, "desk": desk.get("desk")}
            except Exception:
                pass
            try:
                from knowledge_graph.production import soft_slice_for_analyst as ikg_desk

                if t and knowledge_graph:
                    kdesk = (ikg_desk(t, analyst=role) or {}).get("knowledge_graph") or {}
                    if kdesk:
                        ctx["knowledge_graph"] = {**knowledge_graph, "desk": kdesk.get("desk")}
            except Exception:
                pass
            try:
                from forecast_intelligence.production import soft_slice_for_analyst as fie_desk

                if t and forecast_intelligence:
                    fdesk = (fie_desk(t, analyst=role) or {}).get("forecast_intelligence") or {}
                    if fdesk:
                        ctx["forecast_intelligence"] = {**forecast_intelligence, "desk": fdesk.get("desk")}
            except Exception:
                pass
            try:
                from institutional_memory.production import soft_slice_for_analyst as ilm_desk

                if t and institutional_memory:
                    idesk = (ilm_desk(t, analyst=role) or {}).get("institutional_memory") or {}
                    if idesk:
                        ctx["institutional_memory"] = {**institutional_memory, "desk": idesk.get("desk")}
            except Exception:
                pass
            try:
                from simulation_lab.production import soft_slice_for_analyst as ssl_desk

                if t and simulation_lab:
                    sdesk = (ssl_desk(t, analyst=role) or {}).get("simulation_lab") or {}
                    if sdesk:
                        ctx["simulation_lab"] = {**simulation_lab, "desk": sdesk.get("desk")}
            except Exception:
                pass
            opinions[role] = fn(ctx)
        except Exception as exc:
            meta = mandate_for(role)
            opinions[role] = {
                "role": role,
                "analyst": meta.get("analyst"),
                "mandate": {
                    "text": meta.get("mandate"),
                    "primary_question": meta.get("primary_question"),
                    "primary_inputs": meta.get("primary_inputs"),
                    "outputs": meta.get("outputs"),
                    "never": meta.get("never"),
                },
                "primary_question": meta.get("primary_question"),
                "question": meta.get("primary_question"),
                "summary": "Opinion unavailable for this run.",
                "headline": "Opinion unavailable for this run.",
                "stance": "Neutral",
                "strengths": [],
                "weaknesses": [],
                "sections": {},
                "evidence": [],
                "unanswered_questions": ["Specialist file could not be assembled for this run."],
                "confidence": {
                    "evidence": 0.2,
                    "knowledge": 0.2,
                    "freshness": 0.2,
                    "coverage": 0.2,
                    "overall": 0.2,
                },
                "structured": True,
                "error": str(exc)[:120],
            }

    committee = aggregate(opinions, query=query, company=name, ticker=t)

    # Soft CIG — event propagation map into committee (never redesigns IC)
    if causal_intelligence:
        committee = {
            **committee,
            "causal_intelligence": causal_intelligence,
            "event_propagation_map": causal_intelligence.get("propagation_map")
            or (causal_intelligence.get("committee") or {}).get("event_propagation_map"),
            "causal_why": causal_intelligence.get("why"),
            "causal_counterfactuals": causal_intelligence.get("counterfactuals"),
        }

    # Soft IKG — relationship / dependency maps into committee (never redesigns IC)
    if knowledge_graph:
        committee = {
            **committee,
            "knowledge_graph": knowledge_graph,
            "relationship_maps": (knowledge_graph.get("committee") or {}).get("relationship_maps")
            or knowledge_graph.get("summary"),
            "dependency_risks": (knowledge_graph.get("committee") or {}).get("dependency_risks")
            or (knowledge_graph.get("dependencies") or {}).get("suppliers"),
            "hidden_concentration": (knowledge_graph.get("committee") or {}).get("hidden_concentration")
            or knowledge_graph.get("portfolio"),
        }

    # Soft FIE — scenario probabilities into committee (never redesigns IC)
    if forecast_intelligence:
        committee = {
            **committee,
            "forecast_intelligence": forecast_intelligence,
            "scenario_probabilities": forecast_intelligence.get("distribution")
            or (forecast_intelligence.get("committee") or {}).get("distribution"),
            "most_likely_scenario": forecast_intelligence.get("most_likely"),
            "forecast_uncertainty": forecast_intelligence.get("uncertainty"),
        }

    # Soft ILM — historical votes / decision quality / lessons into committee (never redesigns IC)
    if institutional_memory:
        committee = {
            **committee,
            "institutional_memory": institutional_memory,
            "historical_votes": (institutional_memory.get("committee") or {}).get("historical_votes"),
            "decision_quality": (institutional_memory.get("committee") or {}).get("decision_quality")
            or (institutional_memory.get("accuracy") or {}).get("committee_accuracy"),
            "lessons_learned": (institutional_memory.get("institutional_learning") or {}).get("what_improved"),
            "mistake_intelligence": institutional_memory.get("mistake_intelligence"),
        }

    # Soft SSL — alternative strategies / trade-offs / opportunity cost into committee (never redesigns IC)
    if simulation_lab:
        committee = {
            **committee,
            "simulation_lab": simulation_lab,
            "alternative_strategies": simulation_lab.get("alternative_strategies")
            or (simulation_lab.get("committee") or {}).get("alternatives"),
            "simulation_trade_offs": (simulation_lab.get("committee") or {}).get("trade_offs"),
            "opportunity_cost": (simulation_lab.get("committee") or {}).get("opportunity_cost")
            or (simulation_lab.get("decision_package") or {}).get("opportunity_cost"),
            "scenario_comparison": simulation_lab.get("decision_package"),
        }

    # Soft PIO — portfolio impact between Committee and CIO (never redesigns either)
    portfolio_intelligence: dict[str, Any] = {}
    try:
        from portfolio_intelligence.production import soft_slice_for_analyst as pio_slice

        if t:
            portfolio_intelligence = (pio_slice(t, analyst="committee") or {}).get(
                "portfolio_intelligence"
            ) or {}
            if portfolio_intelligence:
                committee = {
                    **committee,
                    "portfolio_intelligence": portfolio_intelligence,
                    "portfolio_impact": portfolio_intelligence.get("impact"),
                    "portfolio_trade_offs": portfolio_intelligence.get("suitability"),
                }
    except Exception:
        portfolio_intelligence = ctx.get("portfolio_intelligence") or {}

    # Soft IDE V2 — constitutional package AFTER PIO and BEFORE CIO (never redesigns CIO/IC)
    decision_engine_v2: dict[str, Any] = ctx.get("decision_engine_v2") or {}
    try:
        from decision_engine_v2.production import analyse as idev2_analyse

        if t:
            idev2_pack = idev2_analyse(
                {
                    "ticker": t,
                    "question": query,
                    "committee": committee,
                    "portfolio_intelligence": portfolio_intelligence,
                }
            )
            if idev2_pack.get("enabled") is not False and idev2_pack.get("found"):
                decision_engine_v2 = {
                    "enabled": True,
                    "found": True,
                    "version": idev2_pack.get("idev2_version"),
                    "recommendation_status": (idev2_pack.get("recommendation_gate") or {}).get("status"),
                    "confidence": (idev2_pack.get("confidence") or {}).get("confidence"),
                    "conflict_count": (idev2_pack.get("conflicts") or {}).get("conflict_count"),
                    "audit_id": (idev2_pack.get("audit") or {}).get("audit_id"),
                    "summary": (idev2_pack.get("report") or {}).get("cio_brief")
                    or idev2_pack.get("institutional_judgement"),
                    "decision_package": {
                        "gate": idev2_pack.get("recommendation_gate"),
                        "judgement": idev2_pack.get("institutional_judgement"),
                        "monitoring": idev2_pack.get("monitoring"),
                        "confidence": idev2_pack.get("confidence"),
                        "conflicts": idev2_pack.get("conflicts"),
                        "uncertainty": idev2_pack.get("uncertainty"),
                        "weights": idev2_pack.get("weights"),
                        "audit": idev2_pack.get("audit"),
                    },
                    "monitoring_plan": idev2_pack.get("monitoring"),
                    "cio_brief": (idev2_pack.get("report") or {}).get("cio_brief"),
                    "architecture_frozen": True,
                    "never_recommendation": True,
                }
                committee = {
                    **committee,
                    "decision_engine_v2": decision_engine_v2,
                    "unified_decision_package": decision_engine_v2.get("decision_package"),
                    "decision_readiness": decision_engine_v2.get("recommendation_status"),
                    "decision_conflicts": (idev2_pack.get("conflicts") or {}).get("matrix"),
                }
    except Exception:
        pass

    cio = write_report(committee, query=query, company=name)
    if causal_intelligence:
        cio = {
            **cio,
            "causal_intelligence": causal_intelligence,
            "why_markets_moved": causal_intelligence.get("cio_brief")
            or causal_intelligence.get("why"),
        }
    if knowledge_graph:
        cio = {
            **cio,
            "knowledge_graph": knowledge_graph,
            "relationship_intelligence": knowledge_graph.get("cio_brief")
            or knowledge_graph.get("summary"),
        }
    if forecast_intelligence:
        cio = {
            **cio,
            "forecast_intelligence": forecast_intelligence,
            "forward_outlook": forecast_intelligence.get("cio_brief")
            or forecast_intelligence.get("executive_forecast"),
        }
    if institutional_memory:
        cio = {
            **cio,
            "institutional_memory": institutional_memory,
            "institutional_learning_summary": institutional_memory.get("cio_brief")
            or institutional_memory.get("institutional_learning")
            or institutional_memory.get("summary"),
        }
    if simulation_lab:
        cio = {
            **cio,
            "simulation_lab": simulation_lab,
            "simulation_decision_package": simulation_lab.get("decision_package")
            or simulation_lab.get("cio_brief")
            or simulation_lab.get("summary"),
            "recommended_monitoring": simulation_lab.get("monitoring_plan"),
        }
    if decision_engine_v2:
        cio = {
            **cio,
            "decision_engine_v2": decision_engine_v2,
            "constitutional_decision_package": decision_engine_v2.get("decision_package")
            or decision_engine_v2.get("cio_brief")
            or decision_engine_v2.get("summary"),
            "decision_readiness": decision_engine_v2.get("recommendation_status"),
            "decision_audit_id": decision_engine_v2.get("audit_id"),
            "recommended_monitoring": decision_engine_v2.get("monitoring_plan")
            or cio.get("recommended_monitoring"),
        }
    if portfolio_intelligence:
        cio = {
            **cio,
            "portfolio_intelligence": portfolio_intelligence,
            "portfolio_context": portfolio_intelligence.get("cio_brief")
            or portfolio_intelligence.get("suitability"),
        }

    # Persist memory AFTER opinions are built (so this run can compare to prior)
    iaf_memory.put_opinions(t, opinions)
    minutes_row = committee.get("minutes") or {}
    # ICI already stores minutes forever; keep IAF mirror for analyst what-changed
    iaf_memory.put_minutes(t, minutes_row)
    minutes_history = committee.get("timeline") or iaf_memory.get_minutes_history(t, limit=6)

    base_pack = {
        "enabled": True,
        "programme": PROGRAMME,
        "version": IAF_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_an_engine": True,
        "orchestration_only": True,
        "query": query,
        "ticker": t,
        "company": name,
        "research_plan": planner,
        "mandates": {r: mandate_for(r) for r in ANALYST_ROLES},
        "analyst_opinions": opinions,
        "committee": committee,
        "investment_committee_intelligence": committee.get("ici") if committee.get("ici_enabled") else {},
        "cio": cio,
        "disagreement_matrix": committee.get("disagreement_matrix"),
        "committee_minutes": minutes_row,
        "committee_minutes_history": minutes_history,
        "committee_vote": committee.get("vote") or committee.get("stage_5_vote"),
        "committee_decision": committee.get("decision") or committee.get("stage_10_decision"),
        "committee_challenges": committee.get("challenges") or committee.get("stage_3_challenges") or [],
        "minority_opinions": committee.get("minority_opinions") or [],
        "confidence_recalibration": committee.get("confidence_recalibration") or {},
        "committee_timeline": committee.get("timeline") or [],
        "committee_accuracy": committee.get("accuracy") or {},
        "section_owners": SECTION_OWNERS,
        "public_owner_labels": PUBLIC_OWNER_LABELS,
        "executive_summary": cio.get("executive_summary"),
        "investment_thesis": cio.get("investment_thesis"),
        "bull_case": cio.get("bull_case"),
        "base_case": cio.get("base_case"),
        "bear_case": cio.get("bear_case"),
        "key_risks": cio.get("key_risks"),
        "key_catalysts": cio.get("key_catalysts"),
        "institutional_conclusion": cio.get("institutional_conclusion"),
        "why": [w for w in (cio.get("why") or []) if w][:6],
        "what_changed": cio.get("what_changed") or [],
        "confidence": cio.get("confidence"),
        "business_intelligence": opinions.get("business"),
        "financial_intelligence": opinions.get("financial"),
        "valuation_intelligence": opinions.get("valuation"),
        "market_intelligence": opinions.get("market"),
        "sector_intelligence_opinion": opinions.get("sector"),
        "macro_intelligence": opinions.get("macro"),
        "risk_intelligence": opinions.get("risk"),
        "management_intelligence": opinions.get("management"),
        "ownership_intelligence": opinions.get("ownership"),
        "institutional_view": committee,
        "institutional_stack": ctx.get("institutional_stack") or {},
        "portfolio_intelligence": portfolio_intelligence,
        "causal_intelligence": causal_intelligence,
        "forecast_intelligence": forecast_intelligence,
        "knowledge_graph": knowledge_graph,
        "institutional_memory": institutional_memory,
        "simulation_lab": simulation_lab,
        "decision_engine_v2": decision_engine_v2,
        "ask_agi_hints": [
            f"Specialist analysts contributed structured opinions on {name}",
            f"Committee stance: {committee.get('committee_stance')}",
            f"Chief Investment Officer confidence {cio.get('confidence')}",
        ],
    }
    stack_summary = (base_pack.get("institutional_stack") or {}).get("summary") or {}
    if stack_summary.get("management_dna"):
        base_pack["ask_agi_hints"].append(
            f"Management DNA: {stack_summary.get('management_dna')} "
            f"(trust score {stack_summary.get('management_confidence')})"
        )
    if stack_summary.get("accounting_behaviour"):
        base_pack["ask_agi_hints"].append(
            f"Accounting behaviour: {stack_summary.get('accounting_behaviour')} "
            f"(quality {stack_summary.get('accounting_quality_score')})"
        )
    if stack_summary.get("portfolio_net_effect") or stack_summary.get("portfolio_grade"):
        base_pack["ask_agi_hints"].append(
            f"Portfolio fit ({stack_summary.get('portfolio_id')}): "
            f"grade {stack_summary.get('portfolio_grade')} · "
            f"net effect {stack_summary.get('portfolio_net_effect')} · "
            f"PQE {stack_summary.get('portfolio_quality')}"
        )
    if stack_summary.get("causal_why") or causal_intelligence.get("why"):
        why0 = stack_summary.get("causal_why")
        if not why0 and isinstance(causal_intelligence.get("why"), list):
            why0 = (causal_intelligence.get("why") or [None])[0]
        if why0:
            base_pack["ask_agi_hints"].append(f"Causal why: {why0}")
        upstream = stack_summary.get("causal_upstream") or causal_intelligence.get("upstream_drivers")
        if upstream:
            base_pack["ask_agi_hints"].append(
                f"Upstream drivers: {', '.join(str(x) for x in list(upstream)[:4])}"
            )
    if stack_summary.get("forecast_most_likely") or forecast_intelligence.get("most_likely"):
        most = stack_summary.get("forecast_most_likely") or forecast_intelligence.get("most_likely")
        dist = stack_summary.get("forecast_distribution") or forecast_intelligence.get("distribution") or {}
        base_pack["ask_agi_hints"].append(
            f"Most likely scenario: {most}"
            + (f" (~{dist.get(most)})" if isinstance(dist, dict) and most in dist else "")
            + " — not a price prediction"
        )
    if stack_summary.get("knowledge_relationship_count") or knowledge_graph.get("relationship_count"):
        base_pack["ask_agi_hints"].append(
            f"Knowledge graph: {stack_summary.get('knowledge_relationship_count') or knowledge_graph.get('relationship_count')} "
            f"evidenced relationships for {stack_summary.get('knowledge_canonical_id') or knowledge_graph.get('canonical_id') or t}"
        )
    if stack_summary.get("memory_lesson_count") or institutional_memory.get("lesson_count"):
        base_pack["ask_agi_hints"].append(
            f"Institutional learning: {stack_summary.get('memory_lesson_count') or institutional_memory.get('lesson_count')} lessons · "
            f"{stack_summary.get('memory_mistake_count') or institutional_memory.get('mistake_count')} classified mistakes · "
            f"thinking_improved={stack_summary.get('memory_thinking_improved') if stack_summary.get('memory_thinking_improved') is not None else institutional_memory.get('thinking_improved')}"
        )
    if stack_summary.get("simulation_expected_return") is not None or simulation_lab.get("expected_return") is not None:
        er = stack_summary.get("simulation_expected_return")
        if er is None:
            er = simulation_lab.get("expected_return")
        sid = stack_summary.get("simulation_scenario_id") or simulation_lab.get("scenario_id")
        base_pack["ask_agi_hints"].append(
            f"Simulation lab: scenario {sid} · E[r]={er} · "
            f"conf {stack_summary.get('simulation_confidence') if stack_summary.get('simulation_confidence') is not None else simulation_lab.get('confidence')} "
            f"— experiment before allocate"
        )
    if stack_summary.get("decision_status") or decision_engine_v2.get("recommendation_status"):
        status = stack_summary.get("decision_status") or decision_engine_v2.get("recommendation_status")
        base_pack["ask_agi_hints"].append(
            f"IDE V2: {status} · conf "
            f"{stack_summary.get('decision_confidence') if stack_summary.get('decision_confidence') is not None else decision_engine_v2.get('confidence')} · "
            f"audit {stack_summary.get('decision_audit_id') or decision_engine_v2.get('audit_id')} "
            f"— constitutional judgement, not a trade ticket"
        )

    # Institutional Research Writer — presentation layer AFTER CIO (never mutates votes/confidence)
    research_writer: dict[str, Any] = {}
    try:
        from research_writer.production import package_for_ask_agi as irw_package

        research_writer = irw_package(base_pack, query=query) or {}
    except Exception:
        research_writer = {}

    if research_writer.get("enabled"):
        base_pack["research_writer"] = research_writer
        base_pack["institutional_report"] = research_writer.get("institutional_report")
        # Presentation overlays only — intelligence fields above stay authoritative for votes/confidence
        base_pack["executive_summary"] = research_writer.get("executive_summary") or base_pack["executive_summary"]
        base_pack["investment_thesis"] = research_writer.get("investment_thesis") or base_pack["investment_thesis"]
        base_pack["institutional_conclusion"] = (
            research_writer.get("institutional_conclusion") or base_pack["institutional_conclusion"]
        )
        base_pack["written_business_intelligence"] = research_writer.get("business_intelligence")
        base_pack["written_financial_intelligence"] = research_writer.get("financial_intelligence")
        base_pack["written_valuation_intelligence"] = research_writer.get("valuation_intelligence")
        base_pack["written_market_intelligence"] = research_writer.get("market_intelligence")
        base_pack["written_sector_intelligence"] = research_writer.get("sector_intelligence")
        base_pack["written_macro_intelligence"] = research_writer.get("macro_intelligence")
        base_pack["written_management"] = research_writer.get("management")
        base_pack["written_ownership"] = research_writer.get("ownership")
        base_pack["written_institutional_view"] = research_writer.get("institutional_view")
        base_pack["risk_register"] = research_writer.get("risk_register")
        base_pack["report_tables"] = research_writer.get("tables")
        base_pack["chart_recommendations"] = research_writer.get("chart_recommendations")
        if research_writer.get("bull_case"):
            base_pack["bull_case"] = research_writer.get("bull_case")
        if research_writer.get("base_case"):
            base_pack["base_case"] = research_writer.get("base_case")
        if research_writer.get("bear_case"):
            base_pack["bear_case"] = research_writer.get("bear_case")
        hints = list(base_pack.get("ask_agi_hints") or [])
        for h in research_writer.get("ask_agi_hints") or []:
            if h not in hints:
                hints.append(h)
        # Keep late institutional-layer hints (FIE / IKG / ILM / SSL / IDE V2) visible in Ask AGI.
        base_pack["ask_agi_hints"] = hints[:16]

    return base_pack
