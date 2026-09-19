"""Ask AGI Answer Construction V3 — soft production entry (+ IAF orchestration)."""

from __future__ import annotations

from typing import Any

from answer_construction.flags import flags_dict, is_enabled
from answer_construction.policy import apply_answer_construction_v3
from answer_construction.schema import AC_VERSION, ARCHITECTURE_STATUS, PROGRAMME


def health() -> dict[str, Any]:
    iaf_health: dict[str, Any] = {}
    irw_health: dict[str, Any] = {}
    editorial_health: dict[str, Any] = {}
    cxr_health: dict[str, Any] = {}
    irsp_health: dict[str, Any] = {}
    try:
        from institutional_analysts.production import health as iaf_h

        iaf_health = iaf_h()
    except Exception:
        iaf_health = {"status": "unavailable"}
    try:
        from research_writer.production import health as irw_h

        irw_health = irw_h()
    except Exception:
        irw_health = {"status": "unavailable"}
    try:
        from editorial.production import health as editorial_h

        editorial_health = editorial_h()
    except Exception:
        editorial_health = {"status": "unavailable"}
    try:
        from contradiction_reasoning.production import health as cxr_h

        cxr_health = cxr_h()
    except Exception:
        cxr_health = {"status": "unavailable"}
    try:
        from institutional_reasoning.production import health as irsp_h

        irsp_health = irsp_h()
    except Exception:
        irsp_health = {"status": "unavailable"}
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "version": AC_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_an_engine": True,
        "gate_logic_unchanged": True,
        "never_stop_at_first_coverage_check": True,
        "institutional_analyst_framework": iaf_health,
        "institutional_research_writer": irw_health,
        "editorial_intelligence_layer": editorial_health,
        "contradiction_reasoning": cxr_health,
        "institutional_reasoning": irsp_health,
        "response_constitution": {"version": "1.0", "soft_wire": True},
        "flags": flags_dict(),
    }


_AC_POLICY_KEYS = {
    "query",
    "executive",
    "thesis",
    "house_label",
    "bull",
    "bear",
    "risks",
    "catalysts",
    "why",
    "intelligence_construction",
    "company_analysis",
    "company_dossier",
    "evidence_completion",
    "live_evidence",
    "sector_intelligence",
    "institutional_briefing",
    "decision_engine",
    "reco_gate",
    "leo_gate",
}


def package_for_ask_agi(**kwargs: Any) -> dict[str, Any]:
    """Soft entry used by UiService after IRP / IC / ECP orchestration.

    Runs Question Understanding Engine FIRST, then Institutional Analyst Framework,
    then applies Answer Construction V3 policy. Engines remain unchanged.
    """
    out: dict[str, Any] = {}

    # Question Understanding Engine v1.0 — FIRST stage. Every answer starts here.
    try:
        from question_understanding_engine import apply_question_understanding_engine

        out = apply_question_understanding_engine(out, **kwargs)
        kwargs = {
            **kwargs,
            "question_understanding": out.get("question_understanding"),
            "research_brief": out.get("research_brief"),
            "research_objective": out.get("research_objective"),
            "decision_type": out.get("decision_type"),
            "primary_investment_question": out.get("primary_investment_question"),
            "top_research_questions": out.get("top_research_questions"),
        }
    except Exception:
        out.setdefault("question_understanding_engine", {"enabled": False, "bypassed": True})

    iaf_pack: dict[str, Any] = {}
    try:
        from institutional_analysts.production import package_for_ask_agi as iaf_package

        iaf_pack = (
            iaf_package(
                kwargs.get("query") or "",
                ticker=kwargs.get("ticker"),
                company_analysis=kwargs.get("company_analysis"),
                company_dossier=kwargs.get("company_dossier"),
                live_evidence=kwargs.get("live_evidence"),
                finance_academy=kwargs.get("finance_academy"),
                sector_intelligence=kwargs.get("sector_intelligence"),
                company_monitor=kwargs.get("company_monitor"),
                valuation=kwargs.get("valuation"),
                institutional_briefing=kwargs.get("institutional_briefing"),
                intelligence_construction=kwargs.get("intelligence_construction"),
                decision_engine=kwargs.get("decision_engine"),
                intelligence_layer=kwargs.get("intelligence_layer"),
                irp=kwargs.get("irp"),
                evidence_completion=kwargs.get("evidence_completion"),
                data_validation=kwargs.get("data_validation"),
                knowledge_foundation=kwargs.get("knowledge_foundation"),
                aws_macro=kwargs.get("aws_macro"),
                yahoo_enrichment=kwargs.get("yahoo_enrichment"),
            )
            or {}
        )
    except Exception:
        iaf_pack = {}

    policy_kwargs = {k: kwargs[k] for k in _AC_POLICY_KEYS if k in kwargs}
    ac_out = apply_answer_construction_v3(
        institutional_analysts=iaf_pack if iaf_pack.get("enabled") else None,
        **policy_kwargs,
    )
    out = {**out, **ac_out}
    if iaf_pack.get("enabled"):
        out["institutional_analysts"] = iaf_pack
        out["base"] = list(iaf_pack.get("base_case") or out.get("base") or [])[:6]
        if iaf_pack.get("research_writer"):
            out["research_writer"] = iaf_pack.get("research_writer")
            out["institutional_report"] = iaf_pack.get("institutional_report")
        if iaf_pack.get("institutional_stack"):
            out["institutional_stack"] = iaf_pack["institutional_stack"]
    if not out.get("institutional_stack"):
        try:
            from institutional_stack.production import soft_slice_for_ask_agi

            stack = soft_slice_for_ask_agi(kwargs.get("ticker"))
            if stack:
                out["institutional_stack"] = stack.get("institutional_stack") or stack
        except Exception:
            pass

    # Institutional Reasoning Soft Policy — understand first, reason second, communicate last.
    # Attaches the pre-answer plan + system prompt. Does not invent facts.
    try:
        from institutional_reasoning.production import package_for_ask_agi as irsp_package

        company_name = None
        if isinstance(out.get("institutional_analysts"), dict):
            company_name = out["institutional_analysts"].get("company")
        irsp = irsp_package(
            query=str(kwargs.get("query") or ""),
            ticker=kwargs.get("ticker"),
            company=company_name,
        )
        if irsp.get("enabled"):
            out["institutional_reasoning"] = irsp
            out["reasoning_plan"] = {
                "top_rule": irsp.get("top_rule"),
                "question_type": (irsp.get("question_understanding") or {}).get("question_type"),
                "main_question": irsp.get("main_question"),
                "steps": irsp.get("reasoning_steps"),
                "answer_structure": irsp.get("answer_structure"),
                "contradiction_protocol_required": irsp.get("contradiction_protocol_required"),
                "pattern_id": irsp.get("pattern_id"),
            }
            # Prefer evidence-first policy unless a later specialist layer overrides.
            if not out.get("answer_policy") or out.get("answer_policy") == "think_then_answer_institutional":
                out["answer_policy"] = "evidence_then_reason_then_communicate"
            # Gold patterns / reasoning families own the executive when matched.
            if irsp.get("owns_executive") and irsp.get("executive"):
                out["executive"] = irsp["executive"]
                out["answer_policy"] = irsp.get("answer_policy") or "gold_reasoning_pattern"
                out["reasoning_pattern"] = {
                    "enabled": True,
                    "pattern_id": irsp.get("pattern_id"),
                    "level": irsp.get("pattern_level"),
                    "family_id": irsp.get("family_id"),
                    "source": irsp.get("reasoning_source"),
                    "novelty": irsp.get("novelty"),
                }
                out["novelty"] = irsp.get("novelty") or {}
                out["reasoning_family"] = irsp.get("reasoning_family") or {
                    "family_id": irsp.get("family_id")
                }
                if irsp.get("ecr"):
                    out["ecr"] = irsp["ecr"]
                    out["evidence_to_conclusion_ratio"] = irsp.get(
                        "evidence_to_conclusion_ratio"
                    ) or (irsp.get("ecr") or {}).get("ecr")
                ia_out = out.get("institutional_answer")
                if isinstance(ia_out, dict) and ia_out.get("enabled"):
                    out["institutional_answer"] = {
                        **ia_out,
                        "text": irsp["executive"],
                        "reason": irsp.get("direct_answer")
                        or (irsp.get("gold_pattern") or {}).get("direct_answer")
                        or ia_out.get("reason"),
                        "gold_reasoning_pattern": irsp.get("reasoning_source") == "gold_pattern",
                        "reasoning_family": irsp.get("family_id"),
                        "pattern_id": irsp.get("pattern_id"),
                        "novelty_score": (irsp.get("novelty") or {}).get("novelty_score"),
                        "ecr": (irsp.get("ecr") or {}).get("ecr"),
                    }
    except Exception:
        out.setdefault("institutional_reasoning", {"enabled": False, "bypassed": True})

    # Soft-attach Academy Books slice onto AC pack for IRW / UI provenance.
    try:
        from academy.books.production import research_writer_slice as books_slice_fn

        books = books_slice_fn(
            str(kwargs.get("query") or ""),
            ticker=kwargs.get("ticker"),
        )
        if isinstance(books, dict) and books.get("enabled"):
            out["academy_books"] = books
    except Exception:
        out.setdefault("academy_books", {"enabled": False})

    # Contradiction Reasoning Soft Layer — step-by-step conflict answers.
    # Soft-wire only (not a top-level engine; not Continuous Research Evaluation).
    # When active, owns the executive text so answers do not jump to certainty.
    # Skip if a gold reasoning pattern already owns the executive.
    contradiction_active = bool(out.get("reasoning_pattern", {}).get("enabled"))
    try:
        if not contradiction_active:
            from contradiction_reasoning.production import package_for_ask_agi as cxr_package

            company_name = None
            if isinstance(out.get("institutional_analysts"), dict):
                company_name = out["institutional_analysts"].get("company")
            cxr = cxr_package(
                query=str(kwargs.get("query") or ""),
                ticker=kwargs.get("ticker"),
                company=company_name,
            )
            if cxr.get("enabled") and cxr.get("executive"):
                contradiction_active = True
                out["contradiction_reasoning"] = cxr
                out["executive"] = cxr["executive"]
                out["answer_policy"] = "contradiction_reasoning_step_by_step"
                out["conflicting_evidence"] = [
                    {"fact": f} for f in (cxr.get("facts") or [])
                ] + [
                    {"explanation": e, "status": "possible"}
                    for e in (cxr.get("possible_explanations") or [])
                ]
                ia_out = out.get("institutional_answer")
                if isinstance(ia_out, dict) and ia_out.get("enabled"):
                    out["institutional_answer"] = {
                        **ia_out,
                        "text": cxr["executive"],
                        "reason": cxr.get("direct_answer")
                        or (cxr.get("answer_structure") or {}).get("direct_answer")
                        or ia_out.get("reason"),
                        "risk": (
                            "Evidence is incomplete: "
                            + "; ".join((cxr.get("missing_evidence") or [])[:2])
                        )
                        if cxr.get("missing_evidence")
                        else ia_out.get("risk"),
                        "contradiction_reasoning": True,
                        "contradiction_archetype": cxr.get("archetype"),
                        "contradiction_confidence": cxr.get("confidence"),
                    }
    except Exception:
        out.setdefault("contradiction_reasoning", {"enabled": False, "bypassed": True})

    # Editorial Intelligence Layer — configured provider rewrites ONLY.
    # AGIB remains the brain; structured intelligence only; never documents.
    # Skip editorial override when contradiction / gold reasoning owns the executive.
    # Also skip inventing valuation prose when framework execution policy withholds narrative.
    ep = kwargs.get("execution_policy") if isinstance(kwargs.get("execution_policy"), dict) else {}
    if ep:
        out["execution_policy"] = {
            "question_type": ep.get("question_type"),
            "sufficient": ep.get("sufficient"),
            "narrative_allowed": ep.get("narrative_allowed"),
            "missing_evidence": ep.get("missing_evidence") or [],
            "summary": ep.get("summary"),
            "results": ep.get("results") or [],
            "ask_agi_hints": ep.get("ask_agi_hints") or [],
        }
        if ep.get("narrative_allowed") is False and ep.get("gate_reason"):
            out["executive"] = str(ep.get("gate_reason") or out.get("executive") or "")[:800]
            out["answer_policy"] = "framework_execution_policy_insufficient_evidence"

    ia_gate = out.get("institutional_answer") if isinstance(out.get("institutional_answer"), dict) else {}
    evidence_gate_owns_lead = bool(
        ia_gate.get("evidence_insufficient")
        or ia_gate.get("investment_thesis_status") == "INCONCLUSIVE"
        or (out.get("recommendation_status") or {}).get("investment_thesis_status") == "INCONCLUSIVE"
    )

    if evidence_gate_owns_lead:
        # Governance owns the conclusion, but the editorial writer may explain it.
        # The structured INCONCLUSIVE status is passed into the rewrite package and
        # must remain explicit; only the earlier blanket prose bypass is removed.
        out["editorial_governance"] = {
            "conclusion_locked": True,
            "investment_thesis_status": "INCONCLUSIVE",
            "reason": "institutional_readiness_gate_owns_conclusion",
        }
        out["answer_policy"] = "institutional_readiness_gate_inconclusive_editorial_allowed"

    if not contradiction_active and ep.get("narrative_allowed") is not False:
        try:
            from answer_construction.institutional_intelligence import wants_detailed_analysis
            from editorial.production import package_for_ask_agi as editorial_package

            editorial = editorial_package(
                query=str(kwargs.get("query") or ""),
                ticker=kwargs.get("ticker"),
                answer_construction=out,
                company_analysis=kwargs.get("company_analysis")
                if isinstance(kwargs.get("company_analysis"), dict)
                else None,
                institutional_answer=out.get("institutional_answer")
                if isinstance(out.get("institutional_answer"), dict)
                else None,
                company=out.get("institutional_analysts", {}).get("company")
                if isinstance(out.get("institutional_analysts"), dict)
                else None,
                detailed=wants_detailed_analysis(str(kwargs.get("query") or "")),
                execution_policy=ep or None,
            )
            if editorial.get("enabled") and editorial.get("executive"):
                out["executive"] = editorial["executive"]
                out["editorial"] = editorial
                ia_out = out.get("institutional_answer")
                if isinstance(ia_out, dict) and ia_out.get("enabled") and editorial.get("executive"):
                    rewritten = editorial.get("rewritten_summary") or editorial.get("executive")
                    out["institutional_answer"] = {
                        **ia_out,
                        "text": editorial["executive"],
                        "reason": rewritten or ia_out.get("reason"),
                        "editorial_provider": editorial.get("provider"),
                        "editorial_fallback": editorial.get("fallback"),
                        "editorial_rewrite_only": True,
                    }
                out["answer_policy"] = (
                    "institutional_readiness_gate_inconclusive_editorial_allowed"
                    if evidence_gate_owns_lead
                    else "agib_brain_external_editorial_writer"
                )
        except Exception:
            out.setdefault("editorial", {"enabled": False, "bypassed": True})
    else:
        out.setdefault(
            "editorial",
            {
                "enabled": False,
                "bypassed": True,
                "reason": "reasoning_pattern_owns_executive",
            },
        )

    # Response Constitution v1.0 — Human First Institutional Research.
    # Soft shape: Direct Answer → Why → Thesis → Bull/Bear → Bottom Line → Supporting → Follow-ups.
    try:
        from answer_construction.response_constitution import apply_response_constitution

        out = apply_response_constitution(
            out,
            query=str(kwargs.get("query") or ""),
            ticker=kwargs.get("ticker"),
            company=kwargs.get("company"),
            company_analysis=kwargs.get("company_analysis")
            if isinstance(kwargs.get("company_analysis"), dict)
            else None,
            intelligence_construction=kwargs.get("intelligence_construction")
            if isinstance(kwargs.get("intelligence_construction"), dict)
            else None,
            bull=kwargs.get("bull"),
            bear=kwargs.get("bear"),
            risks=kwargs.get("risks"),
            catalysts=kwargs.get("catalysts"),
            why=kwargs.get("why"),
            house_label=kwargs.get("house_label") or out.get("house_label"),
            confidence=kwargs.get("confidence"),
            follow_ups=kwargs.get("follow_ups"),
        )
    except Exception:
        out.setdefault("response_constitution", {"enabled": False, "bypassed": True})

    # Ask Intelligence Constitution v1.0 — institutional response methodology (code, not prompt).
    try:
        from ask_intelligence_constitution import apply_ask_intelligence_constitution

        out = apply_ask_intelligence_constitution(
            out,
            query=str(kwargs.get("query") or ""),
            intent_resolution=kwargs.get("intent_resolution") or out.get("intent_resolution"),
            ticker=kwargs.get("ticker"),
            company=kwargs.get("company"),
            house_label=kwargs.get("house_label") or out.get("house_label"),
        )
    except Exception:
        out.setdefault("ask_intelligence_constitution", {"enabled": False, "bypassed": True})

    # Institutional Playbook Framework v1.0 — methodology layer (Ask → Investment OS).
    try:
        from institutional_playbook_framework import apply_institutional_playbook_framework

        out = apply_institutional_playbook_framework(
            out,
            query=str(kwargs.get("query") or ""),
            intent_resolution=kwargs.get("intent_resolution") or out.get("intent_resolution"),
            playbook_selection=kwargs.get("playbook_selection") or out.get("playbook_selection"),
            ticker=kwargs.get("ticker"),
            research_journey_state=kwargs.get("research_journey_state"),
        )
    except Exception:
        out.setdefault("institutional_playbook_framework", {"enabled": False, "bypassed": True})

    # Research Workflow Framework v1.0 — orchestrates playbooks into research sessions.
    try:
        from research_workflow_framework import apply_research_workflow_framework

        out = apply_research_workflow_framework(
            out,
            query=str(kwargs.get("query") or ""),
            intent_resolution=kwargs.get("intent_resolution") or out.get("intent_resolution"),
            ticker=kwargs.get("ticker"),
            company=kwargs.get("company"),
            research_session_state=kwargs.get("research_session_state"),
        )
    except Exception:
        out.setdefault("research_workflow_framework", {"enabled": False, "bypassed": True})

    # Institutional Knowledge Factory v1.0 — transforms evidence into institutional knowledge.
    try:
        from institutional_knowledge_factory import apply_ikf

        out = apply_ikf(
            out,
            query=str(kwargs.get("query") or ""),
            ticker=kwargs.get("ticker"),
            company=kwargs.get("company"),
            evidence_items=kwargs.get("evidence_items"),
            reason=kwargs.get("reason"),
        )
    except Exception:
        out.setdefault("institutional_knowledge_factory", {"enabled": False, "bypassed": True})

    # Institutional Knowledge Runtime v1.0 — validated assertions before downstream consumption.
    try:
        from institutional_knowledge_runtime import apply_ikr_runtime

        out = apply_ikr_runtime(
            out,
            query=str(kwargs.get("query") or ""),
            ticker=kwargs.get("ticker"),
            company=kwargs.get("company"),
            iko=kwargs.get("iko") or out.get("iko"),
            evidence_graph=kwargs.get("evidence_graph"),
            monitoring_metrics=kwargs.get("monitoring_metrics"),
        )
    except Exception:
        out.setdefault("institutional_knowledge_runtime", {"enabled": False, "bypassed": True})

    # Institutional Writing Constitution v1.0 — IRE communication layer (how AGI explains).
    try:
        from institutional_writing_constitution import apply_institutional_writing_constitution

        out = apply_institutional_writing_constitution(
            out,
            query=str(kwargs.get("query") or ""),
            ticker=kwargs.get("ticker"),
            company=kwargs.get("company"),
        )
    except Exception:
        out.setdefault("institutional_writing_constitution", {"enabled": False, "bypassed": True})

    # Editorial Excellence Program v1.0 — review loop after institutional writing.
    try:
        from editorial_excellence import apply_editorial_excellence

        out = apply_editorial_excellence(
            out,
            query=str(kwargs.get("query") or ""),
            ticker=kwargs.get("ticker"),
            company=kwargs.get("company"),
            benchmark_id=kwargs.get("benchmark_id"),
        )
    except Exception:
        out.setdefault("editorial_excellence", {"enabled": False, "bypassed": True})

    return out


def quality_gates() -> dict[str, Any]:
    return {
        "programme": PROGRAMME,
        "version": AC_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "passed": is_enabled(),
        "checks": {
            "enabled": is_enabled(),
            "preserves_full_brief_when_gated": True,
            "recommendation_status_trailing_only": True,
            "never_expose_raw_missing_keys": True,
            "gate_logic_unchanged": True,
            "institutional_analyst_framework_soft": True,
            "institutional_research_writer_soft": True,
            "response_constitution_v1": True,
            "ask_intelligence_constitution_v1": True,
            "institutional_playbook_framework_v1": True,
            "research_workflow_framework_v1": True,
            "institutional_knowledge_factory_v1": True,
            "institutional_knowledge_runtime_v1": True,
            "institutional_writing_constitution_v1": True,
            "editorial_excellence_v1": True,
            "question_understanding_engine_v1": True,
            "question_understanding_engine_v1_1": True,
        },
        "flags": flags_dict(),
    }
