"""Complete Ask Pipeline runner — soft-wire integration only."""

from __future__ import annotations

import time
from typing import Any

from ask_pipeline.context import build_ask_context
from ask_pipeline.dag import execute_research_dag
from ask_pipeline.entities import resolve_ask_entities
from ask_pipeline.evidence import assemble_evidence
from ask_pipeline.gates import evaluate_gates
from ask_pipeline.intent import detect_intent
from ask_pipeline.answer_assembly import (
    AAE_VERSION,
    assemble_answer_plan,
    bind_reasoning_to_answer,
)
from ask_pipeline.intent_resolution import resolve_intent
from framework_selection import IFSE_VERSION, select_frameworks
from framework_selection import store as ifse_store
from institutional_playbooks import IAP_VERSION, select_playbook
from institutional_playbooks import store as iap_store
from institutional_evidence_graph import IEG_VERSION, build_evidence_graph
from institutional_evidence_graph import store as ieg_store
from institutional_analog_intelligence import IMAI_VERSION
from institutional_analog_intelligence.production import retrieve as retrieve_institutional_memory
from institutional_communication import ICE_VERSION, communicate_from_ask
from ask_pipeline.knowledge import retrieve_knowledge
from ask_pipeline.planner import run_planner
from ask_pipeline.external_research import run_external_research
from ask_pipeline.policy import execution_policy
from ask_pipeline.recording import record_decision_quality, register_outcome
from ask_pipeline.schema import FREEZE_LOCKS, PIPELINE_VERSION, PROGRAMME
from ask_pipeline import store
from ask_pipeline.telemetry import build_telemetry
from ask_pipeline.llm_synthesis import synthesize_financial_answer
from observability.tracing import span as trace_span
from observability.tracing import traced as trace_run


@trace_run("agi.ask_pipeline", run_type="chain", tags=["agi", "ask_pipeline"])
def run_complete_ask(
    question: str,
    *,
    ticker_hint: str | None = None,
    session_id: str | None = None,
    conversation_id: str | None = None,
    entity_resolution_pack: dict[str, Any] | None = None,
    extra_packs: dict[str, Any] | None = None,
    academy: dict[str, Any] | None = None,
    requested_depth: str | None = None,
    requested_horizon: str | None = None,
    requested_asset: str | None = None,
    requested_portfolio: str | None = None,
    jurisdiction: str | None = None,
    institutional_knowledge: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Traverse the full institutional Ask pipeline for one question."""
    t0 = time.time()
    stages: dict[str, Any] = {}

    # S01 Context
    context = build_ask_context(
        question,
        session_id=session_id,
        conversation_id=conversation_id,
        ticker_hint=ticker_hint,
        requested_depth=requested_depth,
        requested_horizon=requested_horizon,
        requested_asset=requested_asset,
        requested_portfolio=requested_portfolio,
        jurisdiction=jurisdiction,
    )
    stages["context"] = {"status": "executed", "pipeline_id": context["pipeline_id"]}

    # ------------------------------------------------------------------
    # AGIB v3.4 Track A — Intent Resolution Layer (BEFORE IERE)
    # Language → Intent → Entities → Temporal → Question Type → Requirements
    # ------------------------------------------------------------------
    with trace_span(
        "intent_resolution",
        inputs={"question": question, "ticker_hint": ticker_hint},
        tags=["ask", "intent"],
    ) as _sp:
        irl = resolve_intent(question, ticker_hint=ticker_hint or context.get("ticker_hint"))
        _sp.end(
            outputs={
                "intent": irl.get("intent"),
                "confidence": irl.get("intent_confidence"),
                "question_type": irl.get("question_type"),
                "as_of": irl.get("as_of"),
                "concept_mode": irl.get("concept_mode"),
                "secondary_intent": irl.get("secondary_intent"),
                "rejected_intents": irl.get("rejected_intents"),
            }
        )
    stages["intent_resolution"] = {"status": "executed", **irl}
    context["intent_resolution"] = {
        "intent": irl.get("intent"),
        "question_type": irl.get("question_type"),
        "concept_mode": irl.get("concept_mode"),
        "as_of": irl.get("as_of"),
        "legacy_intent": irl.get("legacy_intent"),
    }
    context["as_of"] = irl.get("as_of")
    context["concept_mode"] = bool(irl.get("concept_mode"))

    # S02 Intent — prefer IRL; keep legacy detector as soft telemetry only
    legacy_intent = detect_intent(question)
    intent_rec = {
        "intent": irl.get("legacy_intent") or legacy_intent.get("intent") or "Unknown",
        "intent_v2": irl.get("intent"),
        "confidence": irl.get("intent_confidence"),
        "reasons": irl.get("intent_reasons") or [],
        "question_type_hint": irl.get("question_type"),
        "investment_recommendation": bool(irl.get("investment_recommendation")),
        "legacy_detector": legacy_intent,
        "source": "intent_resolution_layer",
    }
    context["intent"] = intent_rec["intent"]
    context["intent_v2"] = irl.get("intent")
    stages["intent"] = {"status": "executed", **intent_rec}

    # S03 Entities — Concept Mode clears pollution; else soft-merge IRL + legacy
    if irl.get("concept_mode"):
        entities_rec = {
            "primary": None,
            "entities": [],
            "soft_tags": irl.get("soft_tags") or [],
            "concept_mode": True,
            "count": 0,
            "entity_pollution_blocked": irl.get("entity_pollution_blocked"),
            "ignored_ticker_hint": irl.get("ignored_ticker_hint"),
            "source": "intent_resolution_layer",
        }
    else:
        entities_rec = resolve_ask_entities(
            question,
            ticker_hint=ticker_hint or context.get("ticker_hint"),
            entity_resolution_pack=entity_resolution_pack,
        )
        # Prefer IRL primary when present
        if irl.get("primary"):
            entities_rec["primary"] = irl["primary"]
            # Ensure IRL entities are present
            for e in irl.get("entities") or []:
                if not any(x.get("id") == e.get("id") for x in (entities_rec.get("entities") or [])):
                    entities_rec.setdefault("entities", []).append(e)
        entities_rec["concept_mode"] = False
        entities_rec["source"] = "intent_resolution_layer+legacy"
    context["entities"] = entities_rec.get("entities") or []
    stages["entities"] = {"status": "executed", **entities_rec}

    # S04 Query classification — IRL OVERRIDES classify_question (Track A exit gate)
    question_type = irl.get("question_type") or "education"
    legacy_cls: dict[str, Any] = {}
    try:
        from institutional_reasoning.evidence_contracts import classify_question

        legacy_cls = classify_question(question)
    except Exception as exc:
        legacy_cls = {"error": str(exc)[:120]}
    stages["query_classification"] = {
        "status": "executed",
        "question_type": question_type,
        "source": "intent_resolution_layer",
        "overrides_classify_question": True,
        "legacy_classify_question": legacy_cls,
        "intent_v2": irl.get("intent"),
    }

    primary = entities_rec.get("primary") or {}
    has_entity = bool(primary.get("entity_id")) and not irl.get("concept_mode")
    policy = execution_policy(
        intent=str(irl.get("intent") or intent_rec["intent"]),
        investment_recommendation=bool(intent_rec.get("investment_recommendation")),
        has_entity=has_entity,
        question_type=question_type,
        concept_mode=bool(irl.get("concept_mode")),
        as_of=irl.get("as_of"),
    )
    stages["policy"] = {"status": "executed", **policy}

    # S05 Knowledge (+ IERE) — inherits as_of + concept_mode
    with trace_span(
        "knowledge_retrieval",
        run_type="retriever",
        inputs={"intent": intent_rec["intent"], "as_of": irl.get("as_of")},
        tags=["ask", "knowledge"],
    ) as _sp:
        knowledge = retrieve_knowledge(
            intent=intent_rec["intent"],
            entities=context["entities"],
            soft_tags=entities_rec.get("soft_tags"),
            question=question,
            as_of=irl.get("as_of"),
            concept_mode=bool(irl.get("concept_mode")),
            institutional_knowledge=institutional_knowledge,
        )
        _sp.end(
            outputs={
                "ranked_evidence": len(((knowledge.get("iere") or {}).get("ranked_evidence") or [])),
                "as_of": knowledge.get("as_of"),
            }
        )
    stages["knowledge"] = knowledge

    # S06 Evidence — prefers IERE Evidence Packs when available; reasoning unchanged
    with trace_span(
        "evidence_assembly",
        run_type="retriever",
        inputs={"intent": intent_rec["intent"]},
        tags=["ask", "evidence"],
    ) as _sp:
        evidence = assemble_evidence(
            knowledge,
            intent=intent_rec["intent"],
            entities=context["entities"],
        )
        _sp.end(outputs={"packs": sorted((evidence.get("governance_packs") or {}).keys())})
    stages["evidence"] = evidence

    # ------------------------------------------------------------------
    # AGIB v3.4 Track B — Answer Assembly (AFTER evidence, BEFORE reasoning)
    # Classify → Order → Gaps → Skeleton → Confidence → Citations
    # Deterministic plan only — no LLM synthesis.
    # ------------------------------------------------------------------
    answer_assembly = assemble_answer_plan(
        question=question,
        intent_v2=str(irl.get("intent") or intent_rec.get("intent_v2") or "Unknown"),
        evidence=evidence,
        knowledge=knowledge,
        intent_resolution=irl,
    )
    stages["answer_assembly"] = {
        "status": "executed",
        "aae_version": answer_assembly.get("aae_version") or AAE_VERSION,
        "intent_v2": answer_assembly.get("intent_v2"),
        "item_count": (answer_assembly.get("metrics") or {}).get("item_count"),
        "gap_count": (answer_assembly.get("metrics") or {}).get("gap_count"),
        "confidence_band": (answer_assembly.get("confidence") or {}).get("band"),
        "coverage": (answer_assembly.get("gaps") or {}).get("coverage"),
        "section_order": (answer_assembly.get("skeleton") or {}).get("section_order"),
        "tell_reasoning": (answer_assembly.get("gaps") or {}).get("tell_reasoning"),
        "llm_used": False,
        "fabricated": False,
    }
    context["answer_plan"] = answer_assembly.get("answer_plan")

    # ------------------------------------------------------------------
    # AGIB v3.4 Track C — Framework Selection (AFTER assembly, BEFORE reasoning)
    # Deterministic multi-framework composition. Reasoning unchanged.
    # ------------------------------------------------------------------
    evidence_types_present: list[str] = []
    for item in ((knowledge.get("iere") or {}).get("ranked_evidence") or []):
        if isinstance(item, dict) and item.get("evidence_type"):
            evidence_types_present.append(str(item["evidence_type"]))
    with trace_span(
        "framework_selection",
        inputs={
            "intent_v2": str(irl.get("intent") or intent_rec.get("intent_v2") or "Unknown"),
            "question_type": question_type,
        },
        tags=["ask", "framework"],
    ) as _sp:
        framework_selection = select_frameworks(
            question=question,
            intent_v2=str(irl.get("intent") or intent_rec.get("intent_v2") or "Unknown"),
            question_type=question_type,
            entities=list(entities_rec.get("entities") or []),
            ticker_hint=None if irl.get("concept_mode") else ticker_hint,
            concept_mode=bool(irl.get("concept_mode")),
            as_of=irl.get("as_of"),
            answer_assembly=answer_assembly,
            evidence_types_present=evidence_types_present,
        )
        _sp.end(
            outputs={
                "framework_ids": framework_selection.get("framework_ids"),
                "sector": framework_selection.get("sector"),
                "confidence": (framework_selection.get("confidence") or {}).get("band"),
            }
        )
    ifse_store.record_selection(framework_selection)
    stages["framework_selection"] = {
        "status": "executed",
        "ifse_version": framework_selection.get("ifse_version") or IFSE_VERSION,
        "sector": framework_selection.get("sector"),
        "framework_ids": framework_selection.get("framework_ids"),
        "multi_framework": framework_selection.get("multi_framework"),
        "confidence_band": (framework_selection.get("confidence") or {}).get("band"),
        "confidence_pct": (framework_selection.get("confidence") or {}).get("pct"),
        "validation_passed": (framework_selection.get("validation") or {}).get("passed"),
        "forbidden_rejected": framework_selection.get("forbidden_rejected"),
        "llm_used": False,
        "fabricated": False,
    }
    context["framework_selection"] = {
        "framework_ids": framework_selection.get("framework_ids"),
        "sector": framework_selection.get("sector"),
        "confidence_pct": (framework_selection.get("confidence") or {}).get("pct"),
    }

    # ------------------------------------------------------------------
    # AGIB v3.5 — Institutional Analytical Playbooks (IAP)
    # AFTER framework selection, BEFORE reasoning. Guides reasoning; does not replace it.
    # ------------------------------------------------------------------
    with trace_span(
        "playbook_selection",
        inputs={"sector": framework_selection.get("sector")},
        tags=["ask", "playbook"],
    ) as _sp:
        playbook_selection = select_playbook(
            question=question,
            intent_v2=str(irl.get("intent") or intent_rec.get("intent_v2") or "Unknown"),
            question_type=question_type,
            entities=list(entities_rec.get("entities") or []),
            sector=framework_selection.get("sector"),
            framework_ids=list(framework_selection.get("framework_ids") or []),
            framework_selection=framework_selection,
            concept_mode=bool(irl.get("concept_mode")),
            as_of=irl.get("as_of"),
            answer_assembly=answer_assembly,
        )
        _sp.end(
            outputs={
                "playbook_id": playbook_selection.get("playbook_id"),
                "category": playbook_selection.get("category"),
            }
        )
    iap_store.record_selection(playbook_selection)
    stages["playbook_selection"] = {
        "status": "executed",
        "iap_version": playbook_selection.get("iap_version") or IAP_VERSION,
        "playbook_id": playbook_selection.get("playbook_id"),
        "category": playbook_selection.get("category"),
        "checklist_steps": ((playbook_selection.get("checklist") or {}).get("n_steps")),
        "procedure_steps": ((playbook_selection.get("procedure") or {}).get("n_steps")),
        "confidence_band": (playbook_selection.get("confidence") or {}).get("band"),
        "confidence_pct": (playbook_selection.get("confidence") or {}).get("pct"),
        "validation_passed": (playbook_selection.get("validation") or {}).get("passed"),
        "guides_reasoning": True,
        "reasoning_changed": False,
        "llm_used": False,
        "fabricated": False,
    }
    context["playbook_selection"] = {
        "playbook_id": playbook_selection.get("playbook_id"),
        "category": playbook_selection.get("category"),
        "confidence_pct": (playbook_selection.get("confidence") or {}).get("pct"),
    }

    # ------------------------------------------------------------------
    # AGIB v3.6 Phase 2 Sprint 2.1 — Institutional Evidence Graph (IEG)
    # AFTER playbook, BEFORE reasoning. Relationships over isolated facts.
    # ------------------------------------------------------------------
    hint = None if irl.get("concept_mode") else (
        (primary.get("entity_id") if primary else None)
        or (ticker_hint if not irl.get("entity_pollution_blocked") else None)
    )
    with trace_span(
        "evidence_graph",
        run_type="retriever",
        inputs={"ticker_hint": hint, "as_of": irl.get("as_of")},
        tags=["ask", "evidence_graph"],
    ) as _sp:
        evidence_graph = build_evidence_graph(
            question=question,
            entities=list(entities_rec.get("entities") or []),
            ticker_hint=hint,
            concept_mode=bool(irl.get("concept_mode")),
            as_of=irl.get("as_of"),
            evidence=evidence,
            knowledge=knowledge,
            playbook_selection=playbook_selection,
            framework_selection=framework_selection,
            intent_v2=str(irl.get("intent") or intent_rec.get("intent_v2") or "Unknown"),
        )
        _sp.end(
            outputs={
                "n_nodes": evidence_graph.get("n_nodes"),
                "n_edges": evidence_graph.get("n_edges"),
                "domain_coverage_pct": evidence_graph.get("domain_coverage_pct"),
            }
        )
    ieg_store.record(evidence_graph)

    # ------------------------------------------------------------------
    # AGI v3.5 Phase 3 Sprint 3.5 — Temporal Integrity Replay Guard (pre-analog)
    # AFTER Evidence Graph, BEFORE IMAI / reasoning. Soft-wire only.
    # ------------------------------------------------------------------
    from temporal_integrity.production import guard as tirc_guard

    with trace_span(
        "temporal_integrity.replay_guard.pre_analog",
        inputs={"as_of": irl.get("as_of")},
        tags=["ask", "tirc", "replay_guard"],
    ) as _sp:
        _tirc_pre = tirc_guard(
            as_of=irl.get("as_of"),
            evidence_graph=evidence_graph,
            stage="pre_analog",
        )
        _sp.end(outputs=_tirc_pre.get("report"))
    evidence_graph = _tirc_pre.get("evidence_graph") or evidence_graph

    stages["evidence_graph"] = {
        "status": "executed",
        "ieg_version": evidence_graph.get("ieg_version") or IEG_VERSION,
        "graph_id": evidence_graph.get("graph_id"),
        "entities": evidence_graph.get("entities"),
        "n_nodes": evidence_graph.get("n_nodes"),
        "n_edges": evidence_graph.get("n_edges"),
        "n_chains": len(evidence_graph.get("chains") or []),
        "domain_coverage_pct": evidence_graph.get("domain_coverage_pct"),
        "validation_passed": (evidence_graph.get("validation") or {}).get("passed"),
        "as_of": evidence_graph.get("as_of"),
        "guides_evidence": True,
        "reasoning_changed": False,
        "llm_used": False,
        "fabricated": False,
        "temporal_integrity": (_tirc_pre.get("report") or {}),
    }
    context["evidence_graph"] = {
        "graph_id": evidence_graph.get("graph_id"),
        "domain_coverage_pct": evidence_graph.get("domain_coverage_pct"),
        "n_nodes": evidence_graph.get("n_nodes"),
    }

    # ------------------------------------------------------------------
    # AGIB v3.6 Phase 2 Sprint 2.2 — Institutional Memory & Analog Intelligence
    # AFTER Evidence Graph, BEFORE reasoning. "Have we seen this before?"
    # Soft-wire only — never fabricates analogues; never replaces reasoning.
    # ------------------------------------------------------------------
    with trace_span(
        "institutional_analog_intelligence",
        run_type="retriever",
        inputs={"as_of": irl.get("as_of"), "top_k": 5},
        tags=["ask", "imai"],
    ) as _sp:
        institutional_memory = retrieve_institutional_memory(
            question=question,
            evidence_graph=evidence_graph,
            playbook=playbook_selection,
            as_of=irl.get("as_of"),
            top_k=5,
        )
        _sp.end(
            outputs={
                "have_we_seen_this_before": institutional_memory.get("have_we_seen_this_before"),
                "top_memory_ids": institutional_memory.get("top_memory_ids"),
                "regimes": institutional_memory.get("regimes"),
            }
        )

    # TIRC Replay Guard — post-analog surface / period integrity
    with trace_span(
        "temporal_integrity.replay_guard.post_analog",
        inputs={"as_of": irl.get("as_of")},
        tags=["ask", "tirc", "replay_guard"],
    ) as _sp:
        _tirc_post = tirc_guard(
            as_of=irl.get("as_of"),
            institutional_memory=institutional_memory,
            stage="post_analog",
        )
        _sp.end(outputs=_tirc_post.get("report"))
    institutional_memory = _tirc_post.get("institutional_memory") or institutional_memory
    stages["temporal_integrity"] = {
        "status": "executed",
        "tirc_version": (_tirc_post.get("tirc_version") or _tirc_pre.get("tirc_version")),
        "pre_analog": _tirc_pre.get("report"),
        "post_analog": _tirc_post.get("report"),
        "reasoning_changed": False,
        "knowledge_factory_changed": False,
        "fabricated": False,
    }

    stages["institutional_memory"] = {
        "status": "executed",
        "imai_version": institutional_memory.get("imai_version") or IMAI_VERSION,
        "have_we_seen_this_before": institutional_memory.get("have_we_seen_this_before"),
        "top_memory_ids": institutional_memory.get("top_memory_ids"),
        "scored_count": institutional_memory.get("scored_count"),
        "regimes": institutional_memory.get("regimes"),
        "quality_status": (institutional_memory.get("quality") or {}).get("status"),
        "as_of": institutional_memory.get("as_of"),
        "guides_memory": True,
        "reasoning_changed": False,
        "llm_used": False,
        "fabricated": False,
        "invented_analogues": False,
        "temporal_integrity": (_tirc_post.get("report") or {}),
    }
    context["institutional_memory"] = {
        "top_memory_ids": institutional_memory.get("top_memory_ids"),
        "have_we_seen_this_before": institutional_memory.get("have_we_seen_this_before"),
        "imai_version": institutional_memory.get("imai_version") or IMAI_VERSION,
    }

    # ------------------------------------------------------------------
    # AGI Phase 4 Sprint 4.1 — Institutional Evidence Weighting (IEW)
    # Soft-wire only: deterministic ranking between Memory and Reasoning.
    # Never uses an LLM; never changes reasoning / framework / ICE / TIRC.
    # ------------------------------------------------------------------
    from institutional_evidence_weighting.production import apply_weighting as iew_apply
    from institutional_evidence_weighting.schema import IEW_VERSION, WEIGHT_VERSION

    _iew_meta = {
        "question_id": (context.get("question_id") or session_id or conversation_id),
        "intent": irl.get("intent") or intent_rec.get("intent_v2") or intent_rec.get("intent"),
        "framework": (framework_selection.get("framework_ids") or [None])[0],
        "playbook": playbook_selection.get("playbook_id"),
        "replay_mode": bool(irl.get("as_of")),
        "weight_version": WEIGHT_VERSION,
        "reasoning_version": "frozen",
    }
    with trace_span(
        "evidence_weighting",
        run_type="chain",
        inputs={
            "as_of": irl.get("as_of"),
            "n_graph_nodes": evidence_graph.get("n_nodes") or len(evidence_graph.get("nodes") or []),
            "have_memory": bool(institutional_memory.get("have_we_seen_this_before")),
            "weight_version": WEIGHT_VERSION,
        },
        tags=["ask", "iew", "evidence_weighting"],
        metadata=_iew_meta,
    ) as _sp:
        _iew = iew_apply(
            as_of=irl.get("as_of"),
            evidence_graph=evidence_graph,
            institutional_memory=institutional_memory,
            evidence=evidence,
            question_id=str(_iew_meta.get("question_id") or "") or None,
            intent=str(_iew_meta.get("intent") or "") or None,
            framework=str(_iew_meta.get("framework") or "") or None,
            playbook=str(_iew_meta.get("playbook") or "") or None,
            replay_mode=bool(_iew_meta.get("replay_mode")),
            metadata=_iew_meta,
        )
        # Per-evidence decision traces (mandatory observability)
        for _row in (_iew.get("pack") or {}).get("weighted_evidence") or []:
            with trace_span(
                "evidence_weighting.score",
                run_type="tool",
                inputs={
                    "evidence_id": _row.get("evidence_id"),
                    "source": _row.get("source"),
                },
                tags=["ask", "iew", "weight_decision"],
                metadata={
                    **_iew_meta,
                    "ranking_position": _row.get("ranking_position"),
                    "exclusion_reason": _row.get("exclusion_reason"),
                    "weight_breakdown": _row.get("weight_breakdown"),
                },
            ) as _esp:
                _esp.end(
                    outputs={
                        "weight_score": _row.get("weight_score"),
                        "raw_breakdown": _row.get("weight_breakdown"),
                        "ranking_position": _row.get("ranking_position"),
                        "exclusion_reason": _row.get("exclusion_reason"),
                        "reason": _row.get("reason"),
                        "eligible": _row.get("eligible"),
                    }
                )
        _sp.end(outputs=_iew.get("report"))
    evidence_graph = _iew.get("evidence_graph") or evidence_graph
    institutional_memory = _iew.get("institutional_memory") or institutional_memory
    evidence_weighting = _iew.get("pack") or {}
    stages["evidence_weighting"] = {
        "status": "executed",
        "iew_version": evidence_weighting.get("iew_version") or IEW_VERSION,
        "weight_version": evidence_weighting.get("weight_version") or WEIGHT_VERSION,
        "n_candidates": evidence_weighting.get("n_candidates"),
        "n_eligible": evidence_weighting.get("n_eligible"),
        "n_excluded": evidence_weighting.get("n_excluded"),
        "n_conflicts": evidence_weighting.get("n_conflicts"),
        "top_evidence_id": (_iew.get("report") or {}).get("top_evidence_id"),
        "average_weight": (_iew.get("report") or {}).get("average_weight"),
        "guides_evidence_priority": True,
        "reasoning_changed": False,
        "llm_used": False,
        "fabricated": False,
        "contradictions_resolved": False,
    }
    context["evidence_weighting"] = {
        "iew_version": evidence_weighting.get("iew_version") or IEW_VERSION,
        "weight_version": evidence_weighting.get("weight_version") or WEIGHT_VERSION,
        "top_evidence_ids": [w.get("evidence_id") for w in (evidence_weighting.get("top_weighted") or [])[:5]],
    }

    # ------------------------------------------------------------------
    # AGI Phase 4 Sprint 4.2 — Institutional Hypothesis Generation (IHG)
    # Soft-wire only: Hypothesis Space after IEW, before Reasoning.
    # Deterministic, no LLM, no fabrication, no forced single winner.
    # ------------------------------------------------------------------
    from institutional_hypothesis_generation.production import (
        apply_hypothesis_generation as ihg_apply,
    )
    from institutional_hypothesis_generation.schema import HYPOTHESIS_VERSION, IHG_VERSION

    _ihg_meta = {
        "question_id": (context.get("question_id") or session_id or conversation_id),
        "intent": irl.get("intent") or intent_rec.get("intent_v2") or intent_rec.get("intent"),
        "framework": (framework_selection.get("framework_ids") or [None])[0],
        "playbook": playbook_selection.get("playbook_id"),
        "weight_version": evidence_weighting.get("weight_version") or WEIGHT_VERSION,
        "hypothesis_version": HYPOTHESIS_VERSION,
        "reasoning_version": "frozen",
        "replay_mode": bool(irl.get("as_of")),
    }
    with trace_span(
        "hypothesis_generation",
        run_type="chain",
        inputs={
            "question": question,
            "n_weighted": evidence_weighting.get("n_eligible"),
            "weight_version": _ihg_meta["weight_version"],
            "hypothesis_version": HYPOTHESIS_VERSION,
        },
        tags=["ask", "ihg", "hypothesis"],
        metadata=_ihg_meta,
    ) as _sp:
        _ihg = ihg_apply(
            question=question,
            evidence_weighting=evidence_weighting,
            framework_ids=list(framework_selection.get("framework_ids") or []),
            intent=str(_ihg_meta.get("intent") or "") or None,
            playbook_id=str(_ihg_meta.get("playbook") or "") or None,
            as_of=irl.get("as_of"),
            weight_version=str(_ihg_meta.get("weight_version") or "") or None,
            metadata=_ihg_meta,
        )
        with trace_span(
            "hypothesis_generation.score",
            run_type="tool",
            inputs={"n_hypotheses": (_ihg.get("pack") or {}).get("n_hypotheses")},
            tags=["ask", "ihg", "hypothesis_score"],
            metadata=_ihg_meta,
        ) as _ssp:
            _ssp.end(
                outputs={
                    "outcome": (_ihg.get("report") or {}).get("outcome"),
                    "winning_hypothesis_ids": (_ihg.get("report") or {}).get("winning_hypothesis_ids"),
                    "plural": (_ihg.get("report") or {}).get("plural"),
                    "forced_single_winner": False,
                }
            )
        for _h in (_ihg.get("pack") or {}).get("hypotheses") or []:
            with trace_span(
                "hypothesis_generation.hypothesis",
                run_type="tool",
                inputs={
                    "hypothesis_id": _h.get("hypothesis_id"),
                    "hypothesis": _h.get("hypothesis"),
                },
                tags=["ask", "ihg", "hypothesis_decision"],
                metadata={
                    **_ihg_meta,
                    "status": _h.get("status"),
                    "share": _h.get("share"),
                    "support_score": _h.get("support_score"),
                    "conflict_score": _h.get("conflict_score"),
                },
            ) as _hsp:
                _hsp.end(
                    outputs={
                        "status": _h.get("status"),
                        "priority": _h.get("priority"),
                        "share": _h.get("share"),
                        "overall_score": _h.get("overall_score"),
                        "confidence": _h.get("confidence"),
                        "reason": _h.get("reason"),
                        "supporting_evidence": _h.get("supporting_evidence"),
                        "contradicting_evidence": _h.get("contradicting_evidence"),
                    }
                )
        _sp.end(outputs=_ihg.get("report"))
    hypothesis_generation = _ihg.get("pack") or {}
    stages["hypothesis_generation"] = {
        "status": "executed",
        "ihg_version": hypothesis_generation.get("ihg_version") or IHG_VERSION,
        "hypothesis_version": hypothesis_generation.get("hypothesis_version") or HYPOTHESIS_VERSION,
        "outcome": hypothesis_generation.get("outcome"),
        "n_hypotheses": hypothesis_generation.get("n_hypotheses"),
        "n_rejected": hypothesis_generation.get("n_rejected"),
        "plural": hypothesis_generation.get("plural"),
        "forced_single_winner": False,
        "insufficient_evidence": hypothesis_generation.get("insufficient_evidence"),
        "winning_hypothesis_ids": hypothesis_generation.get("winning_hypothesis_ids"),
        "guides_hypothesis_space": True,
        "reasoning_changed": False,
        "llm_used": False,
        "fabricated": False,
    }
    context["hypothesis_generation"] = {
        "ihg_version": hypothesis_generation.get("ihg_version") or IHG_VERSION,
        "hypothesis_version": hypothesis_generation.get("hypothesis_version") or HYPOTHESIS_VERSION,
        "outcome": hypothesis_generation.get("outcome"),
        "winning_hypothesis_ids": hypothesis_generation.get("winning_hypothesis_ids"),
        "plural": hypothesis_generation.get("plural"),
    }

    # ------------------------------------------------------------------
    # AGI Phase 4 Sprint 4.3 — Institutional Hypothesis Evaluation (IHE)
    # Soft-wire only: evaluate Hypothesis Space before Reasoning.
    # Deterministic judgment — no LLM, no forced single winner.
    # Frozen IEW / IHG / frameworks / reasoning untouched.
    # ------------------------------------------------------------------
    from institutional_hypothesis_evaluation.production import (
        apply_hypothesis_evaluation as ihe_apply,
    )
    from institutional_hypothesis_evaluation.schema import EVALUATION_VERSION, IHE_VERSION

    _ihe_meta = {
        "question_id": (context.get("question_id") or session_id or conversation_id),
        "intent": irl.get("intent") or intent_rec.get("intent_v2") or intent_rec.get("intent"),
        "framework": (framework_selection.get("framework_ids") or [None])[0],
        "playbook": playbook_selection.get("playbook_id"),
        "weight_version": evidence_weighting.get("weight_version") or WEIGHT_VERSION,
        "hypothesis_version": hypothesis_generation.get("hypothesis_version") or HYPOTHESIS_VERSION,
        "evaluation_version": EVALUATION_VERSION,
        "reasoning_version": "frozen",
        "replay_mode": bool(irl.get("as_of")),
    }
    with trace_span(
        "hypothesis_evaluation",
        run_type="chain",
        inputs={
            "question": question,
            "n_hypotheses": hypothesis_generation.get("n_hypotheses"),
            "evaluation_version": EVALUATION_VERSION,
        },
        tags=["ask", "ihe", "hypothesis_evaluation"],
        metadata=_ihe_meta,
    ) as _sp:
        _ihe = ihe_apply(
            question=question,
            hypothesis_generation=hypothesis_generation,
            evidence_weighting=evidence_weighting,
            institutional_memory=institutional_memory,
            framework_selection=framework_selection,
            framework_ids=list(framework_selection.get("framework_ids") or []),
            playbook_selection=playbook_selection,
            evidence_graph=evidence_graph,
            as_of=irl.get("as_of"),
            metadata=_ihe_meta,
        )
        for _eh in (_ihe.get("pack") or {}).get("evaluated_hypotheses") or []:
            with trace_span(
                "hypothesis_evaluation.hypothesis",
                run_type="tool",
                inputs={
                    "hypothesis_id": _eh.get("hypothesis_id"),
                    "hypothesis": _eh.get("hypothesis"),
                },
                tags=["ask", "ihe", "evaluation_decision"],
                metadata={
                    **_ihe_meta,
                    "support_score": _eh.get("support_score"),
                    "conflict_score": _eh.get("conflict_score"),
                    "coverage_score": _eh.get("coverage_score"),
                    "historical_score": _eh.get("historical_score"),
                    "framework_score": _eh.get("framework_score"),
                    "confidence": _eh.get("confidence"),
                    "preferred": _eh.get("preferred"),
                    "rejected_reason": _eh.get("rejected_reason"),
                    "missing_evidence": _eh.get("missing_evidence"),
                    "evaluation_version": EVALUATION_VERSION,
                },
            ) as _esp:
                _esp.end(
                    outputs={
                        "status": _eh.get("status"),
                        "evaluation_score": _eh.get("evaluation_score"),
                        "evaluation_breakdown": _eh.get("evaluation_breakdown"),
                        "confidence": _eh.get("confidence"),
                        "preferred": _eh.get("preferred"),
                        "rejected_reason": _eh.get("rejected_reason"),
                        "evaluation_reason": _eh.get("evaluation_reason"),
                    }
                )
        _sp.end(outputs=_ihe.get("report"))
    hypothesis_evaluation = _ihe.get("pack") or {}
    stages["hypothesis_evaluation"] = {
        "status": "executed",
        "ihe_version": hypothesis_evaluation.get("ihe_version") or IHE_VERSION,
        "evaluation_version": hypothesis_evaluation.get("evaluation_version") or EVALUATION_VERSION,
        "outcome": hypothesis_evaluation.get("outcome"),
        "n_evaluated": hypothesis_evaluation.get("n_evaluated"),
        "n_preferred": hypothesis_evaluation.get("n_preferred"),
        "n_rejected": hypothesis_evaluation.get("n_rejected"),
        "n_indeterminate": hypothesis_evaluation.get("n_indeterminate"),
        "plural": hypothesis_evaluation.get("plural"),
        "forced_single_winner": False,
        "preferred_hypothesis_id": (_ihe.get("report") or {}).get("preferred_hypothesis_id"),
        "guides_judgment": True,
        "reasoning_changed": False,
        "framework_changed": False,
        "llm_used": False,
        "fabricated": False,
    }
    context["hypothesis_evaluation"] = {
        "ihe_version": hypothesis_evaluation.get("ihe_version") or IHE_VERSION,
        "evaluation_version": hypothesis_evaluation.get("evaluation_version") or EVALUATION_VERSION,
        "outcome": hypothesis_evaluation.get("outcome"),
        "preferred_hypothesis_id": (_ihe.get("report") or {}).get("preferred_hypothesis_id"),
        "plural": hypothesis_evaluation.get("plural"),
    }

    # ------------------------------------------------------------------
    # AGI Phase 4 Sprint 4.4 — Institutional Committee Reasoning (ICR)
    # Soft-wire only: Bull/Base/Bear roles from IHE before Reasoning.
    # Not a voting engine — competing cases, then convergence.
    # Frozen IEW / IHG / IHE / frameworks / reasoning untouched.
    # ------------------------------------------------------------------
    from institutional_committee_reasoning.production import (
        apply_committee_reasoning as icr_apply,
    )
    from institutional_committee_reasoning.schema import COMMITTEE_VERSION, ICR_VERSION

    _icr_meta = {
        "question_id": (context.get("question_id") or session_id or conversation_id),
        "intent": irl.get("intent") or intent_rec.get("intent_v2") or intent_rec.get("intent"),
        "framework": (framework_selection.get("framework_ids") or [None])[0],
        "playbook": playbook_selection.get("playbook_id"),
        "weight_version": evidence_weighting.get("weight_version") or WEIGHT_VERSION,
        "hypothesis_version": hypothesis_generation.get("hypothesis_version") or HYPOTHESIS_VERSION,
        "evaluation_version": hypothesis_evaluation.get("evaluation_version") or EVALUATION_VERSION,
        "committee_version": COMMITTEE_VERSION,
        "reasoning_version": "frozen",
        "replay_mode": bool(irl.get("as_of")),
    }
    with trace_span(
        "committee_deliberation",
        run_type="chain",
        inputs={
            "question": question,
            "ihe_outcome": hypothesis_evaluation.get("outcome"),
            "n_evaluated": hypothesis_evaluation.get("n_evaluated"),
            "committee_version": COMMITTEE_VERSION,
        },
        tags=["ask", "icr", "committee_deliberation"],
        metadata=_icr_meta,
    ) as _csp:
        _icr = icr_apply(
            question=question,
            hypothesis_evaluation=hypothesis_evaluation,
            institutional_memory=institutional_memory,
            framework_selection=framework_selection,
            framework_ids=list(framework_selection.get("framework_ids") or []),
            evidence_weighting=evidence_weighting,
            as_of=irl.get("as_of"),
            metadata=_icr_meta,
        )
        for _role in ("bull", "base", "bear"):
            _case = ((_icr.get("pack") or {}).get("cases") or {}).get(_role)
            if not _case:
                continue
            with trace_span(
                "committee_deliberation.case",
                run_type="tool",
                inputs={
                    "case_type": _role,
                    "hypothesis_id": _case.get("hypothesis_id"),
                    "case_name": _case.get("case_name"),
                },
                tags=["ask", "icr", "committee_case"],
                metadata={
                    **_icr_meta,
                    "case_type": _role,
                    "probability": _case.get("probability"),
                    "probability_pct": _case.get("probability_pct"),
                    "confidence": _case.get("confidence"),
                    "support": _case.get("support_score"),
                    "conflict": _case.get("conflict_score"),
                    "assumptions": _case.get("underlying_assumptions"),
                    "risks": _case.get("key_risks"),
                    "catalysts": _case.get("key_catalysts"),
                    "missing_evidence": _case.get("missing_evidence"),
                    "committee_version": COMMITTEE_VERSION,
                },
            ) as _case_sp:
                _case_sp.end(
                    outputs={
                        "case_type": _role,
                        "probability_pct": _case.get("probability_pct"),
                        "confidence": _case.get("confidence"),
                        "invalidation_conditions": _case.get("invalidation_conditions"),
                        "role_definition": _case.get("role_definition"),
                    }
                )
        _csp.end(outputs=_icr.get("report"))
    committee_reasoning = _icr.get("pack") or {}
    stages["committee_reasoning"] = {
        "status": "executed",
        "icr_version": committee_reasoning.get("icr_version") or ICR_VERSION,
        "committee_version": committee_reasoning.get("committee_version") or COMMITTEE_VERSION,
        "outcome": (committee_reasoning.get("report") or {}).get("outcome"),
        "n_cases": committee_reasoning.get("n_cases"),
        "preferred_case": committee_reasoning.get("preferred_case"),
        "probability_distribution": committee_reasoning.get("probability_distribution"),
        "probability_sum": committee_reasoning.get("probability_sum"),
        "voting_engine": False,
        "guides_committee": True,
        "reasoning_changed": False,
        "framework_changed": False,
        "communication_changed": False,
        "llm_used": False,
        "fabricated": False,
    }
    context["committee_reasoning"] = {
        "icr_version": committee_reasoning.get("icr_version") or ICR_VERSION,
        "committee_version": committee_reasoning.get("committee_version") or COMMITTEE_VERSION,
        "preferred_case": committee_reasoning.get("preferred_case"),
        "n_cases": committee_reasoning.get("n_cases"),
        "outcome": (committee_reasoning.get("report") or {}).get("outcome"),
    }

    # ------------------------------------------------------------------
    # AGI Phase 4 Sprint 4.5 — Institutional Confidence Calibration (ICC)
    # Soft-wire only: emergent confidence from IEW→IHG→IHE→ICR before Reasoning.
    # Never a manual label; never raised by an LLM; fixtures never increase it.
    # Frozen IEW / IHG / IHE / ICR / frameworks / reasoning untouched.
    # ------------------------------------------------------------------
    from institutional_confidence_calibration.production import (
        apply_confidence_calibration as icc_apply,
    )
    from institutional_confidence_calibration.schema import CONFIDENCE_VERSION, ICC_VERSION

    _icc_meta = {
        "question_id": (context.get("question_id") or session_id or conversation_id),
        "intent": irl.get("intent") or intent_rec.get("intent_v2") or intent_rec.get("intent"),
        "framework": (framework_selection.get("framework_ids") or [None])[0],
        "playbook": playbook_selection.get("playbook_id"),
        "weight_version": evidence_weighting.get("weight_version") or WEIGHT_VERSION,
        "hypothesis_version": hypothesis_generation.get("hypothesis_version") or HYPOTHESIS_VERSION,
        "evaluation_version": hypothesis_evaluation.get("evaluation_version") or EVALUATION_VERSION,
        "committee_version": committee_reasoning.get("committee_version") or COMMITTEE_VERSION,
        "confidence_version": CONFIDENCE_VERSION,
        "reasoning_version": "frozen",
        "replay_mode": bool(irl.get("as_of")),
    }
    with trace_span(
        "confidence_calibration",
        run_type="chain",
        inputs={
            "question": question,
            "ihe_outcome": hypothesis_evaluation.get("outcome"),
            "icr_n_cases": committee_reasoning.get("n_cases"),
            "confidence_version": CONFIDENCE_VERSION,
        },
        tags=["ask", "icc", "confidence_calibration"],
        metadata=_icc_meta,
    ) as _conf_sp:
        _icc = icc_apply(
            question=question,
            evidence_weighting=evidence_weighting,
            hypothesis_generation=hypothesis_generation,
            hypothesis_evaluation=hypothesis_evaluation,
            committee_reasoning=committee_reasoning,
            institutional_memory=institutional_memory,
            framework_selection=framework_selection,
            temporal_integrity={
                "temporal_ok": True,
                "as_of": irl.get("as_of"),
            },
            replay_integrity=True,
            as_of=irl.get("as_of"),
            metadata=_icc_meta,
        )
        _icc_report = (_icc.get("pack") or {}).get("report") or {}
        _conf_sp.end(
            outputs={
                "overall_confidence": _icc_report.get("overall_confidence"),
                "confidence_level": _icc_report.get("confidence_level"),
                "confidence_reason": _icc_report.get("confidence_reason"),
                "components": _icc_report.get("components"),
                "penalties": _icc_report.get("penalties"),
                "confidence_version": CONFIDENCE_VERSION,
                "temporal_integrity": _icc_report.get("temporal_integrity"),
                "replay_integrity": _icc_report.get("replay_integrity"),
            }
        )
    confidence_calibration = _icc.get("pack") or {}
    stages["confidence_calibration"] = {
        "status": "executed",
        "icc_version": confidence_calibration.get("icc_version") or ICC_VERSION,
        "confidence_version": confidence_calibration.get("confidence_version") or CONFIDENCE_VERSION,
        "overall_confidence": confidence_calibration.get("overall_confidence"),
        "confidence_level": confidence_calibration.get("confidence_level"),
        "guides_confidence": True,
        "reasoning_changed": False,
        "framework_changed": False,
        "communication_changed": False,
        "llm_used": False,
        "manually_assigned": False,
        "fabricated": False,
    }
    context["confidence_calibration"] = {
        "icc_version": confidence_calibration.get("icc_version") or ICC_VERSION,
        "confidence_version": confidence_calibration.get("confidence_version") or CONFIDENCE_VERSION,
        "overall_confidence": confidence_calibration.get("overall_confidence"),
        "confidence_level": confidence_calibration.get("confidence_level"),
    }

    # ------------------------------------------------------------------
    # AGI v4.0 Investment Office OS (5.1–5.5) — soft-wire, never fail Ask.
    # Offices are best-effort; desk briefing must survive office errors/OOM.
    # ------------------------------------------------------------------
    import os as _os

    investment_thesis: dict[str, Any] = {}
    decision_office: dict[str, Any] = {}
    portfolio_office: dict[str, Any] = {}
    monitoring_office: dict[str, Any] = {}
    learning_office: dict[str, Any] = {}
    _v4_persist = str(_os.environ.get("AGI_V4_OFFICE_PERSIST", "0")).lower() in {
        "1",
        "true",
        "yes",
    }
    _v4_enabled = str(_os.environ.get("AGI_V4_OFFICES_IN_ASK", "1")).lower() not in {
        "0",
        "false",
        "no",
    }
    if _v4_enabled:
        try:
            from institutional_investment_thesis.production import (
                apply_investment_thesis as ite_apply,
            )
            from institutional_investment_thesis.schema import ITE_VERSION
            from institutional_decision_office.production import (
                apply_decision_office as ido_apply,
            )
            from institutional_decision_office.schema import IDO_VERSION
            from institutional_portfolio_office.production import (
                apply_portfolio_office as ipo_apply,
            )
            from institutional_portfolio_office.schema import IPO_VERSION
            from institutional_monitoring_office.production import (
                apply_monitoring_office as imo_apply,
            )
            from institutional_monitoring_office.schema import IMO_VERSION
            from institutional_learning_office.production import (
                apply_learning_office as ilo_apply,
            )
            from institutional_learning_office.schema import ILO_VERSION

            _ite = ite_apply(
                question=question,
                ticker=hint,
                company=hint,
                evidence_weighting=evidence_weighting,
                hypothesis_generation=hypothesis_generation,
                hypothesis_evaluation=hypothesis_evaluation,
                committee_reasoning=committee_reasoning,
                confidence_calibration=confidence_calibration,
                institutional_memory=institutional_memory,
                evidence_graph=evidence_graph,
                framework_selection=framework_selection,
                as_of=irl.get("as_of"),
                metadata={"question_id": context.get("question_id"), "ticker": hint},
                persist=_v4_persist,
            )
            investment_thesis = _ite.get("pack") or {}
            stages["investment_thesis"] = {
                "status": "executed",
                "ite_version": investment_thesis.get("ite_version") or ITE_VERSION,
                "thesis_id": (investment_thesis.get("thesis") or {}).get("thesis_id"),
                "persisted": _v4_persist,
            }
            context["investment_thesis"] = {
                "ite_version": investment_thesis.get("ite_version") or ITE_VERSION,
                "thesis_id": (investment_thesis.get("thesis") or {}).get("thesis_id"),
                "decision_status": (investment_thesis.get("thesis") or {}).get("decision_status"),
                "lifecycle": (investment_thesis.get("thesis") or {}).get("lifecycle"),
            }

            _ido = ido_apply(
                question=question,
                investment_thesis=investment_thesis,
                committee_reasoning=committee_reasoning,
                confidence_calibration=confidence_calibration,
                hypothesis_evaluation=hypothesis_evaluation,
                as_of=irl.get("as_of"),
                metadata={"thesis_id": (investment_thesis.get("thesis") or {}).get("thesis_id")},
                persist=_v4_persist,
            )
            decision_office = _ido.get("pack") or {}
            stages["decision_office"] = {
                "status": "executed",
                "ido_version": decision_office.get("ido_version") or IDO_VERSION,
                "decision_id": (decision_office.get("decision") or {}).get("decision_id"),
                "decision": (decision_office.get("decision") or {}).get("decision"),
                "persisted": _v4_persist,
            }
            context["decision_office"] = {
                "ido_version": decision_office.get("ido_version") or IDO_VERSION,
                "decision_id": (decision_office.get("decision") or {}).get("decision_id"),
                "decision": (decision_office.get("decision") or {}).get("decision"),
                "status": (decision_office.get("decision") or {}).get("status"),
            }

            _ipo = ipo_apply(
                question=question,
                investment_thesis=investment_thesis,
                decision_office=decision_office,
                committee_reasoning=committee_reasoning,
                confidence_calibration=confidence_calibration,
                as_of=irl.get("as_of"),
                metadata={"decision_id": (decision_office.get("decision") or {}).get("decision_id")},
                persist=_v4_persist,
            )
            portfolio_office = _ipo.get("pack") or {}
            stages["portfolio_office"] = {
                "status": "executed",
                "ipo_version": portfolio_office.get("ipo_version") or IPO_VERSION,
                "idea_id": (portfolio_office.get("idea") or {}).get("idea_id"),
                "relative_rank": (portfolio_office.get("idea") or {}).get("relative_rank"),
                "expected_role": (portfolio_office.get("idea") or {}).get("expected_role"),
                "persisted": _v4_persist,
            }
            context["portfolio_office"] = {
                "ipo_version": portfolio_office.get("ipo_version") or IPO_VERSION,
                "idea_id": (portfolio_office.get("idea") or {}).get("idea_id"),
                "relative_rank": (portfolio_office.get("idea") or {}).get("relative_rank"),
                "expected_role": (portfolio_office.get("idea") or {}).get("expected_role"),
            }

            _imo = imo_apply(
                question=question,
                portfolio_office=portfolio_office,
                investment_thesis=investment_thesis,
                decision_office=decision_office,
                confidence_calibration=confidence_calibration,
                hypothesis_evaluation=hypothesis_evaluation,
                committee_reasoning=committee_reasoning,
                as_of=irl.get("as_of"),
                metadata={"idea_id": (portfolio_office.get("idea") or {}).get("idea_id")},
                persist=_v4_persist,
            )
            monitoring_office = _imo.get("pack") or {}
            stages["monitoring_office"] = {
                "status": "executed",
                "imo_version": monitoring_office.get("imo_version") or IMO_VERSION,
                "portfolio_idea": monitoring_office.get("portfolio_idea"),
                "n_events": monitoring_office.get("n_events"),
                "requires_review": monitoring_office.get("requires_review"),
                "persisted": _v4_persist,
            }
            context["monitoring_office"] = {
                "imo_version": monitoring_office.get("imo_version") or IMO_VERSION,
                "portfolio_idea": monitoring_office.get("portfolio_idea"),
                "n_events": monitoring_office.get("n_events"),
                "requires_review": monitoring_office.get("requires_review"),
            }

            _ilo = ilo_apply(
                question=question,
                investment_thesis=investment_thesis,
                decision_office=decision_office,
                portfolio_office=portfolio_office,
                monitoring_office=monitoring_office,
                confidence_calibration=confidence_calibration,
                as_of=irl.get("as_of"),
                metadata={"idea_id": (portfolio_office.get("idea") or {}).get("idea_id")},
                persist=_v4_persist,
            )
            learning_office = _ilo.get("pack") or {}
            stages["learning_office"] = {
                "status": "executed",
                "ilo_version": learning_office.get("ilo_version") or ILO_VERSION,
                "learning_id": (learning_office.get("learning") or {}).get("learning_id"),
                "outcome": (learning_office.get("learning") or {}).get("outcome"),
                "category": (learning_office.get("learning") or {}).get("category"),
                "persisted": _v4_persist,
            }
            context["learning_office"] = {
                "ilo_version": learning_office.get("ilo_version") or ILO_VERSION,
                "learning_id": (learning_office.get("learning") or {}).get("learning_id"),
                "outcome": (learning_office.get("learning") or {}).get("outcome"),
                "category": (learning_office.get("learning") or {}).get("category"),
            }
        except Exception as _v4_exc:
            stages["investment_office_os"] = {
                "status": "soft_failed",
                "error": str(_v4_exc)[:200],
                "reasoning_changed": False,
            }
            context.setdefault("investment_thesis", {})
            context.setdefault("decision_office", {})
            context.setdefault("portfolio_office", {})
            context.setdefault("monitoring_office", {})
            context.setdefault("learning_office", {})
    else:
        stages["investment_office_os"] = {"status": "skipped_by_env", "reasoning_changed": False}

    # S07 Planner — no ticker in Concept Mode
    planner = run_planner(question, ticker_hint=hint, policy=policy)
    stages["planner"] = planner

    external_research = run_external_research(question, planner.get("tool_plan"))
    stages["external_research"] = external_research

    # S08 DAG (observability + dependency enforcement record)
    dag = execute_research_dag(
        policy=policy,
        planner=planner,
        knowledge=knowledge,
        evidence=evidence,
    )
    stages["dag"] = dag

    # Merge packs for reasoning
    packs = dict(extra_packs or {})
    if external_research.get("results"):
        packs["web_evidence"] = {
            "results": external_research.get("results"),
            "trust_status": external_research.get("trust_status"),
            "validation": {
                "ok": True,
                "durable_knowledge": False,
                "requires_citation": True,
                "requires_contradiction_check": True,
            },
            "provenance": {
                "source": "governed_external_search",
                "fabricated": False,
            },
        }
    for k, v in (evidence.get("governance_packs") or {}).items():
        if k not in packs or not packs.get(k):
            packs[k] = v
        else:
            # Prefer KF provenance markers alongside existing soft packs
            if isinstance(packs[k], dict) and isinstance(v, dict):
                packs[k] = {**packs[k], "knowledge_factory_overlay": v}
    # Soft overlay — reasoning may ignore; does not change governance internals
    packs["framework_selection"] = {
        "ifse_version": framework_selection.get("ifse_version"),
        "framework_ids": framework_selection.get("framework_ids"),
        "selected": framework_selection.get("selected"),
        "explanation": framework_selection.get("explanation"),
        "confidence": framework_selection.get("confidence"),
        "sector": framework_selection.get("sector"),
        "validation": framework_selection.get("validation"),
        "fabricated": False,
        "reasoning_changed": False,
    }
    # Soft overlay — checklist/procedure guide reasoning; governance may ignore
    packs["playbook_selection"] = {
        "iap_version": playbook_selection.get("iap_version"),
        "playbook_id": playbook_selection.get("playbook_id"),
        "playbook_name": playbook_selection.get("playbook_name"),
        "category": playbook_selection.get("category"),
        "checklist": playbook_selection.get("checklist"),
        "procedure": playbook_selection.get("procedure"),
        "common_mistakes": playbook_selection.get("common_mistakes"),
        "output_structure": playbook_selection.get("output_structure"),
        "evidence_required": playbook_selection.get("evidence_required"),
        "explanation": playbook_selection.get("explanation"),
        "confidence": playbook_selection.get("confidence"),
        "guides_reasoning": True,
        "reasoning_changed": False,
        "fabricated": False,
    }
    packs["evidence_graph"] = {
        "ieg_version": evidence_graph.get("ieg_version"),
        "graph_id": evidence_graph.get("graph_id"),
        "entities": evidence_graph.get("entities"),
        "n_nodes": evidence_graph.get("n_nodes"),
        "n_edges": evidence_graph.get("n_edges"),
        "chains": evidence_graph.get("chains"),
        "chain_bullets": evidence_graph.get("chain_bullets"),
        "surface_bullets": evidence_graph.get("surface_bullets"),
        "entity_trees": {
            k: {
                "coverage": v.get("coverage"),
                "filled_domains": (v.get("coverage") or {}).get("filled_domains"),
            }
            for k, v in (evidence_graph.get("entity_trees") or {}).items()
        },
        "domain_coverage_pct": evidence_graph.get("domain_coverage_pct"),
        "as_of": evidence_graph.get("as_of"),
        "missing_evidence_required": evidence_graph.get("missing_evidence_required"),
        "guides_evidence": True,
        "reasoning_changed": False,
        "fabricated": False,
    }
    packs["institutional_memory"] = {
        "imai_version": institutional_memory.get("imai_version") or IMAI_VERSION,
        "have_we_seen_this_before": institutional_memory.get("have_we_seen_this_before"),
        "top_memory_ids": institutional_memory.get("top_memory_ids"),
        "memories": institutional_memory.get("memories"),
        "surface_bullets": institutional_memory.get("surface_bullets"),
        "comparison": institutional_memory.get("comparison"),
        "regimes": institutional_memory.get("regimes"),
        "as_of": institutional_memory.get("as_of"),
        "quality": institutional_memory.get("quality"),
        "guides_memory": True,
        "reasoning_changed": False,
        "invented_analogues": False,
        "fabricated": False,
    }
    # Soft overlay — ordered weighted evidence for reasoning input priority
    packs["evidence_weighting"] = {
        "iew_version": evidence_weighting.get("iew_version") or IEW_VERSION,
        "weight_version": evidence_weighting.get("weight_version") or WEIGHT_VERSION,
        "ordered_evidence": evidence_weighting.get("ordered_evidence"),
        "top_weighted": evidence_weighting.get("top_weighted"),
        "conflicts": evidence_weighting.get("conflicts"),
        "n_eligible": evidence_weighting.get("n_eligible"),
        "n_excluded": evidence_weighting.get("n_excluded"),
        "guides_evidence_priority": True,
        "contradictions_resolved": False,
        "reasoning_changed": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
    }
    # Soft overlay — Hypothesis Space before conclusion (no forced single winner)
    packs["hypothesis_generation"] = {
        "ihg_version": hypothesis_generation.get("ihg_version") or IHG_VERSION,
        "hypothesis_version": hypothesis_generation.get("hypothesis_version") or HYPOTHESIS_VERSION,
        "hypotheses": hypothesis_generation.get("hypotheses"),
        "outcome": hypothesis_generation.get("outcome"),
        "winning_hypothesis_ids": hypothesis_generation.get("winning_hypothesis_ids"),
        "plural": hypothesis_generation.get("plural"),
        "forced_single_winner": False,
        "insufficient_evidence": hypothesis_generation.get("insufficient_evidence"),
        "guides_hypothesis_space": True,
        "reasoning_changed": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
    }
    # Soft overlay — evaluated judgment entering reasoning (pros/cons/missing/confidence)
    packs["hypothesis_evaluation"] = {
        "ihe_version": hypothesis_evaluation.get("ihe_version") or IHE_VERSION,
        "evaluation_version": hypothesis_evaluation.get("evaluation_version") or EVALUATION_VERSION,
        "report": hypothesis_evaluation.get("report"),
        "evaluated_hypotheses": hypothesis_evaluation.get("evaluated_hypotheses"),
        "outcome": hypothesis_evaluation.get("outcome"),
        "plural": hypothesis_evaluation.get("plural"),
        "forced_single_winner": False,
        "guides_judgment": True,
        "reasoning_changed": False,
        "framework_changed": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
    }
    # Soft overlay — InstitutionalCommitteeReport for reasoning (not raw hypothesis alone)
    packs["committee_reasoning"] = {
        "icr_version": committee_reasoning.get("icr_version") or ICR_VERSION,
        "committee_version": committee_reasoning.get("committee_version") or COMMITTEE_VERSION,
        "report": committee_reasoning.get("report"),
        "cases": committee_reasoning.get("cases"),
        "preferred_case": committee_reasoning.get("preferred_case"),
        "probability_distribution": committee_reasoning.get("probability_distribution"),
        "n_cases": committee_reasoning.get("n_cases"),
        "voting_engine": False,
        "guides_committee": True,
        "reasoning_changed": False,
        "framework_changed": False,
        "communication_changed": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
    }
    # Soft overlay — InstitutionalConfidenceReport (emergent trustworthiness, not optimism)
    packs["confidence_calibration"] = {
        "icc_version": confidence_calibration.get("icc_version") or ICC_VERSION,
        "confidence_version": confidence_calibration.get("confidence_version") or CONFIDENCE_VERSION,
        "report": confidence_calibration.get("report"),
        "overall_confidence": confidence_calibration.get("overall_confidence"),
        "confidence_level": confidence_calibration.get("confidence_level"),
        "confidence_reason": confidence_calibration.get("confidence_reason"),
        "guides_confidence": True,
        "reasoning_changed": False,
        "framework_changed": False,
        "communication_changed": False,
        "llm_used": False,
        "manually_assigned": False,
        "fabricated": False,
        "deterministic": True,
    }
    # Soft overlay — living Investment Thesis (v4.0); analysis only, no BUY/SELL
    packs["investment_thesis"] = {
        "ite_version": investment_thesis.get("ite_version"),
        "schema_version": investment_thesis.get("schema_version"),
        "thesis": investment_thesis.get("thesis"),
        "thesis_id": (investment_thesis.get("thesis") or {}).get("thesis_id"),
        "persisted": investment_thesis.get("persisted"),
        "buy_sell_emitted": False,
        "guides_thesis": True,
        "reasoning_changed": False,
        "judgment_changed": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
    }
    # Soft overlay — Institutional Decision Office (process decision ≠ trade)
    packs["decision_office"] = {
        "ido_version": decision_office.get("ido_version"),
        "schema_version": decision_office.get("schema_version"),
        "decision": decision_office.get("decision"),
        "decision_id": (decision_office.get("decision") or {}).get("decision_id"),
        "persisted": decision_office.get("persisted"),
        "orders_emitted": False,
        "buy_sell_emitted": False,
        "guides_decision": True,
        "reasoning_changed": False,
        "judgment_changed": False,
        "thesis_changed": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
    }
    # Soft overlay — Institutional Portfolio Office (ideas ≠ positions)
    packs["portfolio_office"] = {
        "ipo_version": portfolio_office.get("ipo_version"),
        "schema_version": portfolio_office.get("schema_version"),
        "idea": portfolio_office.get("idea"),
        "idea_id": (portfolio_office.get("idea") or {}).get("idea_id"),
        "peer_ranking": portfolio_office.get("peer_ranking")
        or (portfolio_office.get("idea") or {}).get("peer_ranking"),
        "persisted": portfolio_office.get("persisted"),
        "positions_emitted": False,
        "orders_emitted": False,
        "guides_portfolio": True,
        "reasoning_changed": False,
        "judgment_changed": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
    }
    # Soft overlay — Institutional Monitoring Office (events recommend review)
    packs["monitoring_office"] = {
        "imo_version": monitoring_office.get("imo_version"),
        "schema_version": monitoring_office.get("schema_version"),
        "portfolio_idea": monitoring_office.get("portfolio_idea"),
        "events": monitoring_office.get("events"),
        "event_ids": monitoring_office.get("event_ids"),
        "n_events": monitoring_office.get("n_events"),
        "requires_review": monitoring_office.get("requires_review"),
        "review_queue": monitoring_office.get("review_queue"),
        "domains_covered": monitoring_office.get("domains_covered"),
        "persisted": monitoring_office.get("persisted"),
        "mutates_thesis": False,
        "mutates_decision": False,
        "mutates_portfolio": False,
        "positions_emitted": False,
        "orders_emitted": False,
        "reasoning_changed": False,
        "judgment_changed": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
    }
    # Soft overlay — Institutional Learning Office (process memory; final Office)
    packs["learning_office"] = {
        "ilo_version": learning_office.get("ilo_version"),
        "schema_version": learning_office.get("schema_version"),
        "learning": learning_office.get("learning"),
        "learning_id": (learning_office.get("learning") or {}).get("learning_id"),
        "n_learnings": learning_office.get("n_learnings"),
        "outcome": learning_office.get("outcome"),
        "category": learning_office.get("category"),
        "persisted": learning_office.get("persisted"),
        "knowledge_factory_updated": False,
        "process_memory": True,
        "mutates_thesis": False,
        "mutates_decision": False,
        "mutates_portfolio": False,
        "positions_emitted": False,
        "orders_emitted": False,
        "reasoning_changed": False,
        "judgment_changed": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
    }

    # S09 Reasoning (+ S10 portfolio via flags)
    governance: dict[str, Any] = {}
    try:
        from institutional_reasoning.execution_governance import govern_answer

        with trace_span(
            "reasoning.governance",
            inputs={
                "question_type": question_type,
                "packs": sorted(packs.keys()),
                "build_institutional_evidence": bool(policy.get("build_institutional_evidence")),
            },
            tags=["ask", "reasoning"],
        ) as _sp:
            governance = govern_answer(
                question,
                ticker_hint=hint,
                entity_resolution_pack=None if irl.get("concept_mode") else entity_resolution_pack,
                packs=packs,
                academy=academy,
                build_institutional_evidence=bool(policy.get("build_institutional_evidence")),
                build_portfolio_intelligence=bool(policy.get("build_portfolio_intelligence")),
                build_outcome_intelligence=bool(policy.get("build_outcome_intelligence")),
                question_type_override=question_type,
            )
            _sp.end(
                outputs={
                    "path": governance.get("path"),
                    "question_type": governance.get("question_type"),
                    "narrative_allowed": governance.get("narrative_allowed"),
                    "frameworks": len(governance.get("frameworks") or []),
                    "execution_ms": governance.get("execution_ms"),
                }
            )
        stages["governance"] = {
            "status": "executed",
            "run_id": governance.get("run_id"),
            "path": governance.get("path"),
            "question_type": governance.get("question_type"),
            "narrative_allowed": governance.get("narrative_allowed"),
            "validation": governance.get("validation"),
            "frameworks": len(governance.get("frameworks") or []),
            "has_ipi": bool(governance.get("ipi")),
            "execution_ms": governance.get("execution_ms"),
        }
        stages["portfolio"] = {
            "status": "executed" if governance.get("ipi") else (
                "skipped_by_policy" if not policy.get("run_portfolio") else "empty"
            ),
            "has_ipi": bool(governance.get("ipi")),
            "recommendation": governance.get("portfolio_recommendation"),
        }
    except Exception as exc:
        stages["governance"] = {"status": "error", "error": str(exc)[:200]}
        stages["portfolio"] = {
            "status": "skipped_by_policy" if not policy.get("run_portfolio") else "error",
            "error": str(exc)[:120],
        }

    # Track B — bind existing reasoning into the assembly skeleton (no new facts)
    bound = bind_reasoning_to_answer(answer_assembly, governance=governance)
    institutional_answer = bound.get("institutional_answer") or {}
    # Attach Framework Explanation Object (auditable; not shown by default)
    institutional_answer = {
        **institutional_answer,
        "framework_selection": {
            "framework_ids": framework_selection.get("framework_ids"),
            "selected": framework_selection.get("selected"),
            "explanation": framework_selection.get("explanation"),
            "confidence": framework_selection.get("confidence"),
            "ifse_version": framework_selection.get("ifse_version"),
        },
        "playbook_selection": {
            "playbook_id": playbook_selection.get("playbook_id"),
            "playbook_name": playbook_selection.get("playbook_name"),
            "category": playbook_selection.get("category"),
            "checklist": playbook_selection.get("checklist"),
            "procedure": playbook_selection.get("procedure"),
            "common_mistakes": playbook_selection.get("common_mistakes"),
            "output_structure": playbook_selection.get("output_structure"),
            "explanation": playbook_selection.get("explanation"),
            "confidence": playbook_selection.get("confidence"),
            "iap_version": playbook_selection.get("iap_version"),
            "guides_reasoning": True,
        },
        "evidence_graph": {
            "graph_id": evidence_graph.get("graph_id"),
            "entities": evidence_graph.get("entities"),
            "n_nodes": evidence_graph.get("n_nodes"),
            "n_edges": evidence_graph.get("n_edges"),
            "domain_coverage_pct": evidence_graph.get("domain_coverage_pct"),
            "chains": evidence_graph.get("chains"),
            "surface_bullets": evidence_graph.get("surface_bullets"),
            "as_of": evidence_graph.get("as_of"),
            "ieg_version": evidence_graph.get("ieg_version"),
            "guides_evidence": True,
        },
        "institutional_memory": {
            "imai_version": institutional_memory.get("imai_version") or IMAI_VERSION,
            "have_we_seen_this_before": institutional_memory.get("have_we_seen_this_before"),
            "top_memory_ids": institutional_memory.get("top_memory_ids"),
            "memories": institutional_memory.get("memories"),
            "surface_bullets": institutional_memory.get("surface_bullets"),
            "comparison": institutional_memory.get("comparison"),
            "regimes": institutional_memory.get("regimes"),
            "as_of": institutional_memory.get("as_of"),
            "guides_memory": True,
            "invented_analogues": False,
        },
    }
    stages["answer_binding"] = {
        "status": "executed",
        "governance_bound": bool(bound.get("governance_bound")),
        "governance_path": bound.get("governance_path"),
        "confidence_band": (institutional_answer.get("confidence") or {}).get("band"),
        "generic": bool(institutional_answer.get("generic")),
        "llm_used": False,
        "fabricated": False,
    }

    # ------------------------------------------------------------------
    # AGIB v3.4 Track D — Institutional Communication Engine (ICE)
    # Deterministic renderer of InstitutionalAnswer — no new reasoning.
    # ------------------------------------------------------------------
    with trace_span(
        "institutional_communication",
        inputs={"intent": irl.get("intent"), "path": governance.get("path")},
        tags=["ask", "ice"],
    ) as _sp:
        communication = communicate_from_ask(
            question=question,
            intent_resolution=irl,
            answer_assembly=answer_assembly,
            framework_selection=framework_selection,
            playbook_selection=playbook_selection,
            evidence_graph=evidence_graph,
            institutional_memory=institutional_memory,
            institutional_answer=institutional_answer,
            governance=governance,
            evidence=evidence,
            knowledge=knowledge,
            replay_id=context.get("replay_id"),
        )
        _sp.end(
            outputs={
                "template": communication.get("template"),
                "executive_summary": communication.get("executive_summary"),
                "answer_source": communication.get("answer_source"),
            }
        )
    stages["institutional_communication"] = {
        "status": "executed",
        "ice_version": communication.get("ice_version") or ICE_VERSION,
        "template": communication.get("template"),
        "framework_visible": communication.get("framework_visible"),
        "citation_density": communication.get("citation_density"),
        "narrative_style": communication.get("narrative_style"),
        "validation_passed": (communication.get("validation") or {}).get("passed"),
        "narrative_completeness": (communication.get("validation") or {}).get(
            "narrative_completeness"
        ),
        "generic_template": communication.get("generic_template"),
        "llm_used": False,
        "fabricated": False,
        "reasoning_changed": False,
    }

    # Grounded generative synthesis. The deterministic ICE response remains the
    # fallback and the model receives only bounded, attributed pipeline evidence.
    # Build CRE client sections locally. Internal causal relationships are not
    # exported to the external synthesis provider.
    causal_pack: dict[str, Any] = {}
    causal_sections: dict[str, Any] = {}
    if hint:
        try:
            from causal_research_engine.institutional_answer import compose_cre_sections
            from causal_research_engine.service import ask_context as causal_ask_context
            causal_pack = causal_ask_context(
                entity=hint, question=question, analysis_as_of=irl.get("as_of")
            ).get("causal_research") or {}
            causal_sections = compose_cre_sections(
                question=question, causal_pack=causal_pack,
                evidence_text=str((evidence or {}).get("packs") or {}),
            )
            stages["causal_research"] = {
                "status": "executed", "chain_count": len(causal_pack.get("chains") or []),
                "contradiction_count": len(causal_pack.get("contradictions") or []),
                "confidence": causal_sections.get("confidence"), "execution_eligible": False,
            }
        except Exception as exc:
            stages["causal_research"] = {"status": "unavailable", "error": str(exc)[:160]}

    llm_synthesis = synthesize_financial_answer(
        question=question,
        evidence=evidence,
        intent_resolution=irl,
        entities=entities_rec,
        deterministic_answer=communication,
        supplemental_packs=packs,
    )
    if llm_synthesis.get("used") and isinstance(llm_synthesis.get("answer"), dict):
        generated = llm_synthesis["answer"]
        generated_sections = generated.get("investment_sections") or {}
        section_titles = {
            "thesis": "Investment Thesis",
            "bull_case": "Bull Case",
            "bear_case": "Bear Case",
            "catalysts": "Catalysts",
            "risks": "Risks",
            "valuation": "Valuation",
            "what_changes_view": "What Would Change the View",
            "evidence_gaps": "Evidence Gaps",
        }
        communication_sections = dict(communication.get("sections") or {})
        for section_key, bullets in generated_sections.items():
            if not bullets:
                continue
            communication_sections[section_key] = {
                "section": section_key,
                "title": section_titles.get(section_key, section_key.replace("_", " ").title()),
                "bullets": bullets,
                "visible": True,
                "source": "openai_grounded_synthesis",
            }
        communication_section_order = list(
            dict.fromkeys(
                [
                    *[
                        key
                        for key in (communication.get("section_order") or [])
                        if key in communication_sections
                    ],
                    *[key for key in generated_sections if generated_sections.get(key)],
                ]
            )
        )
        communication = {
            **communication,
            "executive_summary": generated.get("executive_summary"),
            "why": generated.get("why") or communication.get("why") or [],
            "prose": generated.get("prose"),
            "sections": communication_sections,
            "section_order": communication_section_order,
            "answer_source": "openai_grounded_synthesis",
            "llm_cited_evidence_ids": generated.get("cited_evidence_ids") or [],
            "llm_uncertainty": generated.get("uncertainty"),
            "llm_used": True,
            "llm_model": llm_synthesis.get("model"),
        }
    if causal_sections:
        section_titles = {
            "direct_conclusion": "AGI View", "why": "Why",
            "financial_transmission": "Financial Transmission", "bull_case": "Bull Case",
            "bear_case": "Bear Case", "market_may_be_missing": "What the Market May Be Missing",
            "what_changes_view": "What Would Change the View", "monitoring": "What to Monitor",
            "evidence_gaps": "Evidence Gaps",
        }
        communication_sections = dict(communication.get("sections") or {})
        for key, title in section_titles.items():
            bullets = causal_sections.get(key) or []
            if bullets:
                communication_sections[key] = {
                    "section": key, "title": title, "bullets": bullets,
                    "visible": True, "source": "agi_cre_deterministic",
                }
        communication = {
            **communication, "sections": communication_sections,
            "section_order": list(dict.fromkeys([
                "direct_conclusion", "why", "financial_transmission",
                *(communication.get("section_order") or []),
                "market_may_be_missing", "what_changes_view", "monitoring", "evidence_gaps",
            ])),
            "causal_confidence": causal_sections.get("confidence"),
            "premise_challenge": causal_sections.get("premise_challenge") or [],
        }
    stages["llm_synthesis"] = {
        key: value
        for key, value in llm_synthesis.items()
        if key not in {"answer"}
    }
    # Prefer ICE text on the institutional answer surface
    institutional_answer = {
        **institutional_answer,
        "communication": {
            "template": communication.get("template"),
            "executive_summary": communication.get("executive_summary"),
            "section_order": communication.get("section_order"),
            "framework_visible": communication.get("framework_visible"),
            "ice_version": communication.get("ice_version"),
        },
    }

    # S11 DQ record
    dq = record_decision_quality(
        context=context,
        governance=governance,
        evidence=evidence,
        telemetry_latency_ms=int((time.time() - t0) * 1000),
    )
    stages["decision_quality"] = dq

    # S12 Outcome registration
    outcome = register_outcome(policy=policy, governance=governance)
    stages["outcome"] = outcome

    total_ms = int((time.time() - t0) * 1000)

    # Preliminary gates (telemetry filled next)
    stages["telemetry_pending"] = True
    gates = evaluate_gates(stages=stages, policy=policy, context=context)

    # S13 Telemetry
    telemetry = build_telemetry(
        context=context,
        stages=stages,
        policy=policy,
        gates=gates,
        total_ms=total_ms,
    )
    stages["telemetry"] = telemetry
    stages.pop("telemetry_pending", None)

    # Re-evaluate gates with telemetry present
    gates = evaluate_gates(stages=stages, policy=policy, context=context)

    # Persist
    store.put_context(context["pipeline_id"], context)
    execution = {
        "pipeline_id": context["pipeline_id"],
        "replay_id": context["replay_id"],
        "programme": PROGRAMME,
        "pipeline_version": PIPELINE_VERSION,
        "started_at": context["timestamp"],
        "finished_at": store.utc_now(),
        "latency_ms": total_ms,
        "intent": intent_rec["intent"],
        "question": context["question"],
        "stages": {
            k: (
                {sk: sv for sk, sv in v.items() if sk not in {"bag", "packs", "governance_packs", "plan", "knowledge", "evidence"}}
                if isinstance(v, dict)
                else v
            )
            for k, v in stages.items()
        },
        "institutionally_complete": gates.get("institutionally_complete"),
        "quality_gates": gates,
        "decision_id": dq.get("decision_id"),
        "outcome_decision_id": outcome.get("decision_id"),
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
    }
    # Keep full stage payloads for replay (separate)
    replay_payload = {
        "replay_id": context["replay_id"],
        "pipeline_id": context["pipeline_id"],
        "context": context,
        "intent": intent_rec,
        "intent_resolution": {
            "intent": irl.get("intent"),
            "question_type": irl.get("question_type"),
            "concept_mode": irl.get("concept_mode"),
            "as_of": irl.get("as_of"),
        },
        "entities": entities_rec,
        "policy": policy,
        "knowledge": knowledge,
        "evidence": evidence,
        "answer_assembly": answer_assembly,
        "framework_selection": framework_selection,
        "playbook_selection": playbook_selection,
        "evidence_graph": evidence_graph,
        "institutional_memory": institutional_memory,
        "institutional_answer": institutional_answer,
        "communication": communication,
        "llm_synthesis": stages.get("llm_synthesis"),
        "planner": planner,
        "dag": dag,
        "governance": governance,
        "decision_quality": dq,
        "outcome": outcome,
        "telemetry": telemetry,
        "quality_gates": gates,
        "packs_keys": list(packs.keys()),
        "fabricated": False,
    }
    store.put_execution(context["pipeline_id"], execution)
    store.put_replay(context["replay_id"], replay_payload)

    return {
        "programme": PROGRAMME,
        "pipeline_version": PIPELINE_VERSION,
        "pipeline_id": context["pipeline_id"],
        "replay_id": context["replay_id"],
        "context": context,
        "intent_resolution": irl,
        "intent": intent_rec,
        "entities": entities_rec,
        "policy": policy,
        "knowledge": knowledge,
        "evidence": evidence,
        "answer_assembly": answer_assembly,
        "answer_assembly_version": AAE_VERSION,
        "framework_selection": framework_selection,
        "framework_selection_version": IFSE_VERSION,
        "playbook_selection": playbook_selection,
        "playbook_selection_version": IAP_VERSION,
        "evidence_graph": evidence_graph,
        "evidence_graph_version": IEG_VERSION,
        "institutional_memory": institutional_memory,
        "institutional_memory_version": IMAI_VERSION,
        "institutional_answer": institutional_answer,
        "communication": communication,
        "institutional_communication_version": ICE_VERSION,
        "answer": {
            "summary": communication.get("executive_summary"),
            "executive_summary": communication.get("executive_summary"),
            "why": communication.get("why") or [],
            "prose": communication.get("prose"),
            "template": communication.get("template"),
            "sections": communication.get("sections"),
            "source": communication.get("answer_source") or "institutional_communication",
            "fabricated": False,
            "llm_used": bool(llm_synthesis.get("used")),
        },
        "planner": planner,
        "dag": dag,
        "governance": governance,
        "decision_quality": dq,
        "outcome": outcome,
        "telemetry": telemetry,
        "quality_gates": gates,
        "institutionally_complete": bool(gates.get("institutionally_complete")),
        "latency_ms": total_ms,
        "as_of": irl.get("as_of"),
        "concept_mode": bool(irl.get("concept_mode")),
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
        "reasoning_changed": False,
        "knowledge_factory_changed": False,
        "llm_used": bool(llm_synthesis.get("used")),
        "llm_synthesis_used": bool(llm_synthesis.get("used")),
        "model": llm_synthesis.get("model"),
        "llm": {
            key: value
            for key, value in llm_synthesis.items()
            if key not in {"answer"}
        },
        # AGI v4.0 Investment Office soft surface (thin; full packs in store/context)
        "investment_office_os": {
            "release": "AGI v4.0",
            "investment_thesis": (context.get("investment_thesis") or {}),
            "decision_office": (context.get("decision_office") or {}),
            "portfolio_office": (context.get("portfolio_office") or {}),
            "monitoring_office": (context.get("monitoring_office") or {}),
            "learning_office": (context.get("learning_office") or {}),
            "positions": False,
            "orders": False,
            "execution": False,
        },
    }
