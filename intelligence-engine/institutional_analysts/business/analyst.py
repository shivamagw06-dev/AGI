"""Business Analyst — Would a long-term institutional investor want to own this business?"""

from __future__ import annotations

from typing import Any

from institutional_analysts.base import as_list, company_name, pick_confidence, structured_opinion, ticker_of
from institutional_analysts.flags import is_iai_business_enabled
from institutional_analysts.memory import get_previous_opinion


def _legacy_analyse(ctx: dict[str, Any]) -> dict[str, Any]:
    ca = ctx.get("company_analysis") if isinstance(ctx.get("company_analysis"), dict) else {}
    cid = ctx.get("company_dossier") if isinstance(ctx.get("company_dossier"), dict) else {}
    academy = ctx.get("finance_academy") if isinstance(ctx.get("finance_academy"), dict) else {}
    leo = ctx.get("live_evidence") if isinstance(ctx.get("live_evidence"), dict) else {}
    name = company_name(ctx)

    bq = ca.get("business_quality") if isinstance(ca.get("business_quality"), dict) else {}
    identity = cid.get("identity") if isinstance(cid.get("identity"), dict) else {}
    profile = cid.get("business_profile") if isinstance(cid.get("business_profile"), dict) else {}
    thesis = ca.get("investment_thesis") if isinstance(ca.get("investment_thesis"), dict) else {}

    model = (
        profile.get("business_model")
        or thesis.get("business_overview")
        or bq.get("business_model")
        or identity.get("business_model")
        or f"{name} runs a deposit- and franchise-driven operating model in its core market."
    )
    strengths = as_list(
        bq.get("strengths")
        or bq.get("advantages")
        or thesis.get("competitive_advantages")
        or ["Scale", "Distribution", "Customer trust"],
        limit=5,
    )
    weaknesses = as_list(
        bq.get("risks") or thesis.get("risks") or ["Competition", "Execution", "Regulatory change"],
        limit=4,
    )
    score = bq.get("business_quality_score")
    try:
        score_f = float(score) if score is not None else None
    except Exception:
        score_f = None

    stance = (
        "Bullish"
        if (score_f is not None and score_f >= 65)
        else "Neutral"
        if score_f is None or score_f >= 50
        else "Bearish"
    )
    evidence = []
    evidence.extend(as_list(leo.get("documents_used"), limit=3))
    evidence.extend(as_list((academy.get("applied_concepts") or [])[:2], limit=2))
    evidence.extend(strengths[:2])

    coverage = pick_confidence(bq.get("confidence"), ca.get("confidence"), default=0.55)
    return structured_opinion(
        role="business",
        summary=(
            f"{name}: franchise quality depends on durable demand drivers and capital discipline "
            "— not on the tape."
        ),
        strengths=strengths,
        weaknesses=weaknesses,
        evidence=evidence or [f"Institutional business profile for {name}"],
        unanswered_questions=[
            "How durable is pricing power through the next competitive cycle?",
            "Which growth adjacencies truly expand the opportunity set?",
        ],
        sections={
            "business_model": model,
            "revenue_drivers": bq.get("revenue_drivers")
            or profile.get("revenue_drivers")
            or ["Core franchise demand", "Mix", "Scale efficiencies"],
            "competitive_position": bq.get("competitive_position")
            or identity.get("industry")
            or "Established franchise in its peer set",
            "competitive_advantages": strengths,
            "pricing_power": bq.get("pricing_power")
            or "Mixed — depends on competitive intensity and product mix",
            "brand": bq.get("brand") or profile.get("brand") or f"{name} brand recognition supports retention",
            "capital_allocation": bq.get("capital_allocation")
            or "Reinvestment versus owner returns must stay disciplined",
            "growth_opportunities": bq.get("growth_opportunities")
            or thesis.get("catalysts")
            or ["Share gains", "Adjacent products"],
            "business_risks": weaknesses,
            "business_quality_score": score_f if score_f is not None else "n/a",
        },
        stance=stance,
        confidence={
            "evidence": pick_confidence(len(evidence) / 6, default=0.5),
            "knowledge": coverage,
            "freshness": pick_confidence(leo.get("freshness_score"), default=0.55),
            "coverage": coverage,
        },
        score=score_f,
        ctx=ctx,
    )


def _evidence_pack(ctx: dict[str, Any], name: str) -> dict[str, Any]:
    ca = ctx.get("company_analysis") if isinstance(ctx.get("company_analysis"), dict) else {}
    cid = ctx.get("company_dossier") if isinstance(ctx.get("company_dossier"), dict) else {}
    academy = ctx.get("finance_academy") if isinstance(ctx.get("finance_academy"), dict) else {}
    leo = ctx.get("live_evidence") if isinstance(ctx.get("live_evidence"), dict) else {}
    sector = ctx.get("sector_intelligence") if isinstance(ctx.get("sector_intelligence"), dict) else {}

    bq = ca.get("business_quality") if isinstance(ca.get("business_quality"), dict) else {}
    identity = cid.get("identity") if isinstance(cid.get("identity"), dict) else {}
    profile = cid.get("business_profile") if isinstance(cid.get("business_profile"), dict) else {}
    thesis = ca.get("investment_thesis") if isinstance(ca.get("investment_thesis"), dict) else {}
    management = cid.get("management") if isinstance(cid.get("management"), dict) else {}

    advantages = as_list(
        bq.get("strengths")
        or bq.get("advantages")
        or thesis.get("competitive_advantages")
        or ["Scale", "Distribution", "Customer trust"],
        limit=5,
    )
    risks = as_list(
        bq.get("risks") or thesis.get("risks") or ["Competition", "Execution", "Regulatory change"],
        limit=5,
    )
    refs = []
    refs.extend(as_list(leo.get("documents_used"), limit=3))
    refs.extend(as_list((academy.get("applied_concepts") or [])[:2], limit=2))
    refs.extend(advantages[:2])

    score = bq.get("business_quality_score")
    try:
        score_f = float(score) if score is not None else None
    except Exception:
        score_f = None

    return {
        "company": name,
        "business_model": (
            profile.get("business_model")
            or thesis.get("business_overview")
            or bq.get("business_model")
            or identity.get("business_model")
            or f"{name} runs a franchise-driven operating model in its core market."
        ),
        "advantages": advantages,
        "revenue_drivers": as_list(
            bq.get("revenue_drivers")
            or profile.get("revenue_drivers")
            or ["Core franchise demand", "Mix", "Scale efficiencies"],
            limit=5,
        ),
        "competitive_position": bq.get("competitive_position")
        or identity.get("industry")
        or "Established franchise in its peer set",
        "pricing_power": bq.get("pricing_power")
        or "Mixed — depends on competitive intensity and product mix",
        "brand": bq.get("brand") or profile.get("brand") or f"{name} brand recognition supports retention",
        "capital_allocation": bq.get("capital_allocation")
        or "Reinvestment versus owner returns must stay disciplined",
        "growth_opportunities": as_list(
            bq.get("growth_opportunities") or thesis.get("catalysts") or ["Share gains", "Adjacent products"],
            limit=4,
        ),
        "business_risks": risks,
        "business_quality_score": score_f,
        "management": management,
        "governance": management.get("governance") if isinstance(management, dict) else None,
        "documents_used": as_list(leo.get("documents_used"), limit=5),
        "sector": sector,
        "global_peers": as_list(sector.get("global_peers"), limit=4),
        "indian_peers": as_list(sector.get("indian_peers") or sector.get("peers"), limit=4),
        "historical_performance": as_list(bq.get("historical_performance"), limit=4),
        "evidence_refs": [
            {"claim": r, "source_ref": "institutional research"} for r in refs
        ]
        or [{"claim": f"Institutional business profile for {name}", "source_ref": "institutional research"}],
    }


def analyse(ctx: dict[str, Any]) -> dict[str, Any]:
    if not is_iai_business_enabled():
        return _legacy_analyse(ctx)

    from institutional_analysts.business.brain import think

    name = company_name(ctx)
    ca = ctx.get("company_analysis") if isinstance(ctx.get("company_analysis"), dict) else {}
    leo = ctx.get("live_evidence") if isinstance(ctx.get("live_evidence"), dict) else {}
    bq = ca.get("business_quality") if isinstance(ca.get("business_quality"), dict) else {}
    evidence = _evidence_pack(ctx, name)

    coverage = pick_confidence(bq.get("confidence"), ca.get("confidence"), default=0.55)
    evidence_n = len(evidence.get("evidence_refs") or [])
    conf = {
        "evidence": pick_confidence(evidence_n / 6, default=0.5),
        "knowledge": coverage,
        "freshness": pick_confidence(leo.get("freshness_score"), default=0.55),
        "coverage": coverage,
    }

    previous = get_previous_opinion(ticker_of(ctx), "business")
    # Enrich prior with V2 fields if present on stored opinion
    if previous and isinstance(ctx.get("_prior_business_v2"), dict):
        previous = {**previous, **ctx["_prior_business_v2"]}

    evidence["ticker"] = ticker_of(ctx)
    brain = think(
        company=name,
        evidence=evidence,
        previous=previous,
        confidence=conf,
        ticker=ticker_of(ctx),
    )

    # Prefer brain confidence (includes reasoning factor)
    conf_out = brain.get("confidence") if isinstance(brain.get("confidence"), dict) else conf

    score = evidence.get("business_quality_score")
    try:
        score_f = float(score) if score is not None else None
    except Exception:
        score_f = None

    summary = str(brain.get("summary") or brain.get("executive_opinion") or "")
    base = structured_opinion(
        role="business",
        summary=summary,
        strengths=list(brain.get("strengths") or []),
        weaknesses=list(brain.get("weaknesses") or []),
        evidence=[
            (e.get("claim") if isinstance(e, dict) else str(e))
            for e in (evidence.get("evidence_refs") or [])
        ],
        unanswered_questions=list(brain.get("unanswered_questions") or brain.get("missing_evidence") or []),
        sections={
            "business_model": (brain.get("business_model") or {}).get("assessment")
            or evidence.get("business_model"),
            "revenue_drivers": brain.get("revenue_drivers") or evidence.get("revenue_drivers"),
            "competitive_position": brain.get("competitive_position") or evidence.get("competitive_position"),
            "competitive_advantages": evidence.get("advantages"),
            "pricing_power": (brain.get("pricing_power") or {}).get("assessment")
            or evidence.get("pricing_power"),
            "brand": evidence.get("brand"),
            "capital_allocation": (brain.get("capital_allocation") or {}).get("assessment")
            or evidence.get("capital_allocation"),
            "growth_opportunities": brain.get("opportunities") or evidence.get("growth_opportunities"),
            "business_risks": brain.get("risks") or evidence.get("business_risks"),
            "business_quality_score": score_f if score_f is not None else "n/a",
            "executive_opinion": brain.get("executive_opinion"),
            "business_quality_grade": (brain.get("business_quality") or {}).get("grade"),
            "moat_durability": (brain.get("moat") or {}).get("durability"),
            "moat_summary": (brain.get("moat") or {}).get("summary")
            or (brain.get("moat") or {}).get("assessment"),
            "growth_runway": brain.get("growth_runway"),
            "industry_position": brain.get("industry_position"),
            "assumptions": brain.get("assumptions"),
            "uncertainties": brain.get("uncertainties"),
            "frameworks_applied": brain.get("frameworks_applied"),
            "trajectory": brain.get("trajectory"),
            "iai_version": brain.get("iai_version"),
            "quality_status": (brain.get("quality_checks") or {}).get("status"),
        },
        stance=str(brain.get("stance") or "Neutral"),
        confidence=conf_out,
        score=score_f,
        ctx=ctx,
    )

    # Canonical V2 structured object + compatibility aliases
    structured = brain.get("structured_business_opinion") or {}
    for key in (
        "executive_opinion",
        "business_quality",
        "moat",
        "competitive_position",
        "business_model",
        "revenue_drivers",
        "customer_economics",
        "pricing_power",
        "capital_allocation",
        "innovation",
        "industry_position",
        "growth_runway",
        "risks",
        "opportunities",
        "assumptions",
        "uncertainties",
        "missing_evidence",
        "quality_checks",
    ):
        if key in structured:
            base[key] = structured[key]
        elif brain.get(key) is not None:
            base[key] = brain.get(key)

    base["structured_business_opinion"] = structured
    base["moat_assessment"] = brain.get("moat_assessment") or brain.get("moat")
    base["competitive_outlook"] = brain.get("competitive_outlook")
    base["reasoning"] = brain.get("reasoning")
    base["uncertainty"] = brain.get("uncertainty") or brain.get("uncertainties")
    base["validation"] = brain.get("validation")
    base["analyst_memory"] = brain.get("memory")
    base["benchmarks"] = brain.get("benchmarks")
    base["trajectory"] = brain.get("trajectory")
    base["primary_question_answer"] = brain.get("primary_question_answer")
    base["institutional_business_opinion"] = brain.get("institutional_business_opinion") or summary
    base["case_studies"] = brain.get("case_studies")
    base["archetype"] = brain.get("archetype")
    base["historical_outcomes"] = brain.get("historical_outcomes")
    base["lessons_learned"] = brain.get("lessons_learned")
    base["business_dna"] = brain.get("business_dna")
    base["learning_chain"] = brain.get("learning_chain")
    base["iai_version"] = brain.get("iai_version")
    base["iai_active"] = True
    base["iai_v2"] = True
    base["iai_v2_1"] = True
    base["ready_for_committee"] = brain.get("ready_for_committee")

    # Ensure confidence exposes reasoning factor
    if isinstance(base.get("confidence"), dict) and "reasoning" in conf_out:
        base["confidence"]["reasoning"] = conf_out["reasoning"]

    if previous:
        brain_changed = list(brain.get("what_changed") or [])
        wc = base.get("what_changed") if isinstance(base.get("what_changed"), dict) else {}
        notes = list(wc.get("notes") or [])
        for note in brain_changed:
            if note and note not in notes:
                notes.append(note)
        traj = brain.get("trajectory")
        if traj and traj != "Stable":
            notes.append(f"Overall business view trajectory: {traj}")
        if wc:
            wc["notes"] = notes[:6]
            wc["trajectory"] = traj
            base["what_changed"] = wc
        elif notes:
            base["what_changed"] = {
                "previous_stance": previous.get("stance"),
                "current_stance": base.get("stance"),
                "changed": True,
                "notes": notes[:6],
                "trajectory": traj,
            }

    return base
