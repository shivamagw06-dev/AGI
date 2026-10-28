"""Soft AGIB probe — measurement only; does not change reasoning internals."""

from __future__ import annotations

from typing import Any


def probe_question(
    question: dict[str, Any],
    *,
    mode: str = "soft",
) -> dict[str, Any]:
    """
    Execute AGIB soft layers for evaluation.

    mode=soft  — intent + frameworks + playbook + evidence graph + IMAI (fast nightly)
    mode=full  — complete ask pipeline (slow; sample use)
    """
    text = str(question.get("question") or "")
    ticker = question.get("ticker_hint")
    as_of = question.get("as_of")

    if mode == "full":
        from ask_pipeline.pipeline import run_complete_ask

        pipe = run_complete_ask(text, ticker_hint=ticker)
        return {
            "mode": "full",
            "question_id": question.get("question_id"),
            "intent_resolution": pipe.get("intent_resolution") or {},
            "framework_selection": pipe.get("framework_selection") or {},
            "playbook_selection": pipe.get("playbook_selection") or {},
            "evidence_graph": pipe.get("evidence_graph") or {},
            "institutional_memory": pipe.get("institutional_memory") or {},
            "communication": pipe.get("communication") or {},
            "governance": {
                "path": (pipe.get("governance") or {}).get("path"),
                "question_type": (pipe.get("governance") or {}).get("question_type"),
            },
            "latency_ms": pipe.get("latency_ms"),
            "reasoning_changed": pipe.get("reasoning_changed"),
            "fabricated": False,
        }

    # Soft structural probe
    from ask_pipeline.intent_resolution import resolve_intent
    from framework_selection import select_frameworks
    from institutional_analog_intelligence.production import retrieve as retrieve_memory
    from institutional_evidence_graph import build_evidence_graph
    from institutional_playbooks import select_playbook

    irl = resolve_intent(text, ticker_hint=ticker)
    if as_of and not irl.get("as_of"):
        irl = {**irl, "as_of": as_of}

    concept_mode = (
        question.get("concept_mode")
        if question.get("concept_mode") is not None
        else bool(irl.get("concept_mode"))
    )
    hint = None if concept_mode else ticker
    entities = [] if concept_mode else ([{"type": "company", "id": hint, "confidence": 0.99}] if hint else [])

    fs = select_frameworks(
        question=text,
        intent_v2=str(irl.get("intent") or "Unknown"),
        ticker_hint=hint,
        concept_mode=concept_mode,
        as_of=irl.get("as_of") or as_of,
        entities=entities or None,
    )
    pb = select_playbook(
        question=text,
        intent_v2=str(irl.get("intent") or "Unknown"),
        sector=fs.get("sector") or question.get("sector"),
        framework_ids=list(fs.get("framework_ids") or []),
        framework_selection=fs,
        concept_mode=concept_mode,
    )
    eg = build_evidence_graph(
        question=text,
        entities=entities or list(irl.get("entities") or []),
        ticker_hint=hint,
        concept_mode=concept_mode,
        as_of=irl.get("as_of") or as_of,
        playbook_selection=pb,
        framework_selection=fs,
        intent_v2=str(irl.get("intent") or "Unknown"),
    )
    # AGI TIRC — Replay Guard (soft probe mirrors Ask pipeline)
    from temporal_integrity.production import guard as tirc_guard

    _as_of = irl.get("as_of") or as_of
    _pre = tirc_guard(as_of=_as_of, evidence_graph=eg, stage="pre_analog")
    eg = _pre.get("evidence_graph") or eg
    im = retrieve_memory(
        question=text,
        evidence_graph=eg,
        playbook=pb,
        as_of=_as_of,
        top_k=5,
    )
    _post = tirc_guard(as_of=_as_of, institutional_memory=im, stage="post_analog")
    im = _post.get("institutional_memory") or im
    # AGI IEW — Evidence Weighting (soft probe mirrors Ask pipeline)
    from institutional_evidence_weighting.production import apply_weighting as iew_apply

    _iew = iew_apply(
        as_of=_as_of,
        evidence_graph=eg,
        institutional_memory=im,
        question_id=str(question.get("question_id") or "") or None,
        intent=str(irl.get("intent") or "") or None,
        framework=(list(fs.get("framework_ids") or []) or [None])[0],
        playbook=pb.get("playbook_id"),
        replay_mode=bool(_as_of),
    )
    eg = _iew.get("evidence_graph") or eg
    im = _iew.get("institutional_memory") or im
    # AGI IHG — Hypothesis Space (soft probe mirrors Ask pipeline)
    from institutional_hypothesis_generation.production import (
        apply_hypothesis_generation as ihg_apply,
    )

    _ihg = ihg_apply(
        question=text,
        evidence_weighting=_iew.get("pack") or {},
        framework_ids=list(fs.get("framework_ids") or []),
        intent=str(irl.get("intent") or "") or None,
        playbook_id=pb.get("playbook_id"),
        as_of=_as_of,
        weight_version=(_iew.get("pack") or {}).get("weight_version"),
    )
    # AGI IHE — Hypothesis Evaluation (soft probe mirrors Ask pipeline)
    from institutional_hypothesis_evaluation.production import (
        apply_hypothesis_evaluation as ihe_apply,
    )

    _ihe = ihe_apply(
        question=text,
        hypothesis_generation=_ihg.get("pack") or {},
        evidence_weighting=_iew.get("pack") or {},
        institutional_memory=im,
        framework_selection=fs,
        framework_ids=list(fs.get("framework_ids") or []),
        playbook_selection=pb,
        evidence_graph=eg,
        as_of=_as_of,
    )
    # AGI ICR — Committee Reasoning (soft probe mirrors Ask pipeline)
    from institutional_committee_reasoning.production import (
        apply_committee_reasoning as icr_apply,
    )

    _icr = icr_apply(
        question=text,
        hypothesis_evaluation=_ihe.get("pack") or {},
        institutional_memory=im,
        framework_selection=fs,
        framework_ids=list(fs.get("framework_ids") or []),
        evidence_weighting=_iew.get("pack") or {},
        as_of=_as_of,
    )
    # AGI ICC — Confidence Calibration (soft probe mirrors Ask pipeline)
    from institutional_confidence_calibration.production import (
        apply_confidence_calibration as icc_apply,
    )

    _icc = icc_apply(
        question=text,
        evidence_weighting=_iew.get("pack") or {},
        hypothesis_generation=_ihg.get("pack") or {},
        hypothesis_evaluation=_ihe.get("pack") or {},
        committee_reasoning=_icr.get("pack") or {},
        institutional_memory=im,
        framework_selection=fs,
        temporal_integrity={
            "pre_analog": _pre.get("report"),
            "post_analog": _post.get("report"),
            "temporal_ok": True,
        },
        replay_integrity=True,
        as_of=_as_of,
    )
    # AGI ITE — Investment Thesis (soft probe mirrors Ask pipeline; persist living object)
    from institutional_investment_thesis.production import (
        apply_investment_thesis as ite_apply,
    )

    _ite = ite_apply(
        question=text,
        ticker=str(question.get("ticker_hint") or "") or None,
        company=str(question.get("ticker_hint") or "") or None,
        evidence_weighting=_iew.get("pack") or {},
        hypothesis_generation=_ihg.get("pack") or {},
        hypothesis_evaluation=_ihe.get("pack") or {},
        committee_reasoning=_icr.get("pack") or {},
        confidence_calibration=_icc.get("pack") or {},
        institutional_memory=im,
        evidence_graph=eg,
        framework_selection=fs,
        as_of=_as_of,
        persist=True,
    )
    # AGI IDO — Decision Office (soft probe mirrors Ask pipeline)
    from institutional_decision_office.production import (
        apply_decision_office as ido_apply,
    )

    _ido = ido_apply(
        question=text,
        investment_thesis=_ite.get("pack") or {},
        committee_reasoning=_icr.get("pack") or {},
        confidence_calibration=_icc.get("pack") or {},
        hypothesis_evaluation=_ihe.get("pack") or {},
        as_of=_as_of,
        persist=True,
    )
    # AGI IPO — Portfolio Office (soft probe mirrors Ask pipeline)
    from institutional_portfolio_office.production import (
        apply_portfolio_office as ipo_apply,
    )

    _ipo = ipo_apply(
        question=text,
        investment_thesis=_ite.get("pack") or {},
        decision_office=_ido.get("pack") or {},
        committee_reasoning=_icr.get("pack") or {},
        confidence_calibration=_icc.get("pack") or {},
        as_of=_as_of,
        persist=True,
    )
    # AGI IMO — Monitoring Office (soft probe mirrors Ask pipeline)
    from institutional_monitoring_office.production import (
        apply_monitoring_office as imo_apply,
    )

    _imo = imo_apply(
        question=text,
        portfolio_office=_ipo.get("pack") or {},
        investment_thesis=_ite.get("pack") or {},
        decision_office=_ido.get("pack") or {},
        confidence_calibration=_icc.get("pack") or {},
        hypothesis_evaluation=_ihe.get("pack") or {},
        committee_reasoning=_icr.get("pack") or {},
        as_of=_as_of,
        persist=True,
    )
    # AGI ILO — Learning Office (soft probe mirrors Ask pipeline; final Office)
    from institutional_learning_office.production import (
        apply_learning_office as ilo_apply,
    )

    _ilo = ilo_apply(
        question=text,
        investment_thesis=_ite.get("pack") or {},
        decision_office=_ido.get("pack") or {},
        portfolio_office=_ipo.get("pack") or {},
        monitoring_office=_imo.get("pack") or {},
        confidence_calibration=_icc.get("pack") or {},
        as_of=_as_of,
        persist=True,
    )
    return {
        "mode": "soft",
        "question_id": question.get("question_id"),
        "intent_resolution": irl,
        "framework_selection": fs,
        "playbook_selection": pb,
        "evidence_graph": eg,
        "institutional_memory": im,
        "evidence_weighting": _iew.get("pack") or {},
        "hypothesis_generation": _ihg.get("pack") or {},
        "hypothesis_evaluation": _ihe.get("pack") or {},
        "committee_reasoning": _icr.get("pack") or {},
        "confidence_calibration": _icc.get("pack") or {},
        "investment_thesis": _ite.get("pack") or {},
        "decision_office": _ido.get("pack") or {},
        "portfolio_office": _ipo.get("pack") or {},
        "monitoring_office": _imo.get("pack") or {},
        "learning_office": _ilo.get("pack") or {},
        "temporal_integrity": {
            "pre_analog": _pre.get("report"),
            "post_analog": _post.get("report"),
        },
        "communication": {},
        "governance": {},
        "latency_ms": None,
        "reasoning_changed": False,
        "fabricated": False,
    }
