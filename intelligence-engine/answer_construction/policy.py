"""Answer Construction V3 policy — preserve full institutional brief when recommendation is gated."""

from __future__ import annotations

from typing import Any

from answer_construction.flags import flags_dict, is_enabled
from answer_construction.institutional_intelligence import (
    apply_concise_voice,
    build_institutional_recommendation,
    is_recommendation_query,
)
from answer_construction.knowledge_gaps import (
    filter_why_bullets,
    knowledge_gaps_from_sources,
    looks_like_gate_failure_summary,
)
from answer_construction.recommendation_status import build_recommendation_status
from answer_construction.schema import AC_VERSION, ARCHITECTURE_STATUS, PROGRAMME


def _txt(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _first_useful(*candidates: Any, fallback: str | None = None) -> str | None:
    for c in candidates:
        t = _txt(c)
        if t and not looks_like_gate_failure_summary(t):
            return t
    return fallback


def apply_answer_construction_v3(
    *,
    query: str = "",
    executive: str | None = None,
    thesis: str | None = None,
    house_label: str | None = None,
    bull: list[Any] | None = None,
    bear: list[Any] | None = None,
    risks: list[Any] | None = None,
    catalysts: list[Any] | None = None,
    why: list[Any] | None = None,
    intelligence_construction: dict[str, Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
    company_dossier: dict[str, Any] | None = None,
    evidence_completion: dict[str, Any] | None = None,
    live_evidence: dict[str, Any] | None = None,
    sector_intelligence: dict[str, Any] | None = None,
    institutional_briefing: dict[str, Any] | None = None,
    decision_engine: dict[str, Any] | None = None,
    institutional_analysts: dict[str, Any] | None = None,
    reco_gate: dict[str, Any] | None = None,
    leo_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Soft policy applied after IRP/IC and before SearchView return.

    Gate logic is unchanged: Buy/Hold/Sell remains blocked when LEO/SIF say so.
    What changes: the full research briefing is preserved; recommendation status
    becomes a trailing section; checklist language is removed from the lead.
    When the Investment Decision Engine is active, never lead with Buy/Sell —
    frame the executive around the multi-layer stack; decision conclusion trails.
    When Institutional Analyst Framework is present, CIO owns executive/thesis/
    scenarios/conclusion and specialist analysts own their sections.
    """
    if not is_enabled():
        return {
            "enabled": False,
            "programme": PROGRAMME,
            "version": AC_VERSION,
            "bypassed": True,
            "architecture_status": ARCHITECTURE_STATUS,
            "executive": executive,
            "thesis": thesis,
            "house_label": house_label,
            "bull": list(bull or []),
            "bear": list(bear or []),
            "risks": list(risks or []),
            "catalysts": list(catalysts or []),
            "why": list(why or []),
            "recommendation_status": {},
            "knowledge_gaps": [],
        }

    ic = intelligence_construction if isinstance(intelligence_construction, dict) else {}
    enrich = ic.get("answer_enrichment") or {}
    sections = ic.get("sections") or {}
    ca = company_analysis if isinstance(company_analysis, dict) else {}
    briefing = institutional_briefing if isinstance(institutional_briefing, dict) else {}
    cid = company_dossier if isinstance(company_dossier, dict) else {}
    ide = decision_engine if isinstance(decision_engine, dict) else {}
    ide_active = bool(ide.get("active") and ide.get("enabled", True))
    ide_enrich = ide.get("answer_enrichment") if isinstance(ide.get("answer_enrichment"), dict) else {}
    iaf = institutional_analysts if isinstance(institutional_analysts, dict) else {}
    iaf_active = bool(iaf.get("enabled"))
    cio = iaf.get("cio") if isinstance(iaf.get("cio"), dict) else {}
    irw = iaf.get("research_writer") if isinstance(iaf.get("research_writer"), dict) else {}
    irw_active = bool(irw.get("enabled"))
    irw_report = irw.get("institutional_report") if isinstance(irw.get("institutional_report"), dict) else {}

    blocked = bool((reco_gate or {}).get("blocked") or (leo_gate or {}).get("blocked"))

    name = (
        iaf.get("company")
        or ide.get("company_name")
        or ic.get("company_name")
        or (ca.get("identity") or {}).get("company_name")
        or cid.get("ticker")
        or "the company"
    )

    business_bits = [
        _txt((ca.get("identity") or {}).get("business_model")),
        _txt(ca.get("business_overview")),
        _txt((sections.get("business_quality") or {}).get("narrative")),
        _txt((sections.get("market_performance") or {}).get("narrative")),
        _txt((sections.get("financial_intelligence") or {}).get("narrative")),
        _txt((sections.get("valuation") or {}).get("narrative")),
    ]
    business_bits = [b for b in business_bits if b]

    ide_exec_fallback = None
    if ide_active:
        grade = ide.get("investment_grade") or (ide.get("summary") or {}).get("investment_grade")
        overall = ide.get("overall_score") or (ide.get("summary") or {}).get("overall_score")
        framing = _txt(ide_enrich.get("executive_framing"))
        score_bit = (
            f" Layered decision score {overall}/100 (grade {grade})."
            if overall is not None
            else ""
        )
        ide_exec_fallback = (
            framing
            or (
                f"Investment decision stack for {name}: macro, industry, company quality, financials, "
                f"management, valuation, expectations, technicals, risk, catalysts, probability and "
                f"expected return are assessed before any ownership conclusion.{score_bit} "
                "No layer is skipped."
            )
        )

    # Executive Summary ownership: IRP + Intelligence Construction.
    # Decision Engine may trail a conclusion — it must not own the lead executive.
    exec_out = _first_useful(
        irw.get("executive_summary") if irw_active else None,
        irw_report.get("executive_summary") if irw_active else None,
        cio.get("executive_summary") if iaf_active else None,
        ide_exec_fallback if ide_active and not iaf_active else None,
        enrich.get("executive_summary"),
        ic.get("executive_brief"),
        briefing.get("what_is_happening"),
        briefing.get("current_outlook") if not looks_like_gate_failure_summary(briefing.get("current_outlook")) else None,
        " ".join(business_bits[:3]) if business_bits else None,
        executive if not looks_like_gate_failure_summary(executive) else None,
        thesis if not looks_like_gate_failure_summary(thesis) else None,
        ide_exec_fallback if ide_active else None,
        fallback=(
            f"Institutional research brief on {name}: synthesising business model, financial quality, "
            "valuation context, sector position, risks and catalysts from AGI's living intelligence stack. "
            + (
                "An institutional Buy/Hold/Sell recommendation is not yet open — see Recommendation Status at the end."
                if blocked
                else "See the sections below for the full institutional assessment."
            )
        ),
    )

    thesis_out = _first_useful(
        irw.get("investment_thesis") if irw_active else None,
        cio.get("investment_thesis") if iaf_active else None,
        ca.get("investment_thesis"),
        enrich.get("current_outlook"),
        briefing.get("what_is_happening"),
        briefing.get("why_it_matters"),
        thesis if not looks_like_gate_failure_summary(thesis) else None,
        exec_out,
    )

    # Preserve analytical stance labels — never promote "Insufficient Evidence" to the lead view.
    label = _txt(house_label)
    if not label or looks_like_gate_failure_summary(label) or "insufficient" in label.lower():
        label = "Neutral"
        # Prefer CA / briefing stance if present and clean
        for candidate in (
            (ca.get("house_view") or {}).get("stance") if isinstance(ca.get("house_view"), dict) else None,
            briefing.get("current_agi_view"),
        ):
            c = _txt(candidate)
            if c and not looks_like_gate_failure_summary(c) and "insufficient" not in c.lower():
                label = c
                break

    bull_out = [str(x) for x in (bull or []) if _txt(x) and not looks_like_gate_failure_summary(x)]
    bear_out = [str(x) for x in (bear or []) if _txt(x) and not looks_like_gate_failure_summary(x)]
    if iaf_active:
        bull_out = [str(x) for x in (cio.get("bull_case") or bull_out) if _txt(x)][:6] or bull_out
        bear_out = [str(x) for x in (cio.get("bear_case") or bear_out) if _txt(x)][:6] or bear_out
    if not bull_out:
        bull_out = [str(x) for x in (briefing.get("bull_case") or ca.get("bull_case") or []) if _txt(x)][:6]
    if not bear_out:
        bear_out = [str(x) for x in (briefing.get("bear_case") or ca.get("bear_case") or []) if _txt(x)][:6]
    if blocked and not bull_out:
        bull_out = [
            f"If evidence completion lifts coverage, upside would centre on clearer proof of {name}'s demand durability and capital returns.",
        ]
    if blocked and not bear_out:
        bear_out = [
            f"Downside remains open while validated financial and valuation coverage for {name} is still incomplete.",
        ]

    risk_out = [str(x) for x in (risks or []) if _txt(x)][:8]
    if iaf_active and cio.get("key_risks"):
        risk_out = [str(x) for x in cio.get("key_risks") if _txt(x)][:8]
    if not risk_out:
        risk_out = [str(x) for x in (briefing.get("risks") or ca.get("risks") or enrich.get("risks") or []) if _txt(x)][:8]
    if not risk_out:
        risk_out = [
            "Evidence incompleteness itself is a risk — conclusions should be held with appropriate humility.",
            "Competitive intensity and execution risk remain open until operating metrics are fuller.",
        ]

    cat_out = [str(x) for x in (catalysts or []) if _txt(x)][:8]
    if iaf_active and cio.get("key_catalysts"):
        cat_out = [str(x) for x in cio.get("key_catalysts") if _txt(x)][:8]
    if not cat_out:
        cat_out = [str(x) for x in (briefing.get("catalysts") or ca.get("catalysts") or enrich.get("catalysts") or []) if _txt(x)][:8]
    if not cat_out:
        cat_out = [
            "Next earnings print and management commentary",
            "Further enrichment of the living company dossier",
        ]

    gaps = knowledge_gaps_from_sources(
        evidence_completion=evidence_completion,
        company_dossier=company_dossier,
        live_evidence=live_evidence,
        company_analysis=company_analysis,
        limit=8,
    )
    why_out = filter_why_bullets(why, gaps=gaps, limit=12)
    if iaf_active:
        for bullet in list(cio.get("why") or []) + list(iaf.get("ask_agi_hints") or []):
            t = _txt(bullet)
            if t and t not in why_out and not looks_like_gate_failure_summary(t):
                why_out.insert(0, t[:420])
            if len(why_out) >= 12:
                break
    for bullet in list(ide_enrich.get("why_bullets") or []) + list(enrich.get("why_bullets") or []):
        t = _txt(bullet)
        if t and t not in why_out and not looks_like_gate_failure_summary(t):
            why_out.append(t[:420])
        if len(why_out) >= 12:
            break
    if business_bits and not iaf_active:
        for b in business_bits:
            if b not in why_out:
                why_out.insert(0, b[:420])
            if len(why_out) >= 12:
                break

    reco = build_recommendation_status(
        blocked=blocked,
        evidence_completion=evidence_completion,
        company_dossier=company_dossier,
        live_evidence=live_evidence,
        company_analysis=company_analysis,
        sector_intelligence=sector_intelligence,
        company_name=str(name),
        decision_engine=ide,
    )

    decision_conclusion = _txt(irw.get("institutional_conclusion")) if irw_active else None
    if not decision_conclusion:
        decision_conclusion = _txt(cio.get("institutional_conclusion")) if iaf_active else None
    if not decision_conclusion:
        decision_conclusion = _txt(ide_enrich.get("decision_conclusion")) if ide_active else None
    if ide_active and decision_conclusion and not iaf_active:
        # Keep Buy/Hold/Sell-style conclusion trailing — never as the lead executive.
        thesis_out = _first_useful(thesis_out, decision_conclusion)

    institutional_answer: dict[str, Any] = {}
    reco_query = is_recommendation_query(query)
    if reco_query:
        quality_score = None
        for candidate in (
            (ca.get("business_quality") or {}).get("business_quality_score")
            if isinstance(ca.get("business_quality"), dict)
            else None,
            (ca.get("recommendation_readiness") or {}).get("overall"),
            (evidence_completion or {}).get("quality_panel", {}).get("coverage_pct")
            if isinstance(evidence_completion, dict)
            else None,
        ):
            try:
                if candidate is not None:
                    quality_score = float(candidate)
                    break
            except (TypeError, ValueError):
                continue

        institutional_answer = build_institutional_recommendation(
            query=query,
            company_name=str(name),
            stance=label,
            blocked=blocked,
            reason_candidates=[
                thesis_out,
                exec_out,
                *(bull_out[:2]),
                *(why_out[:2]),
            ],
            risk_candidates=risk_out[:3] or bear_out[:2],
            quality_score=quality_score,
        )
        # Lead answer becomes the concise CIO card; full brief remains in thesis/sections.
        if institutional_answer.get("text"):
            exec_out = institutional_answer["text"]
    else:
        # Non-recommendation Ask answers stay institutional and concise at the lead.
        exec_out = apply_concise_voice(exec_out, query=query) or exec_out

    answer_policy = (
        "agib_institutional_intelligence_concise_recommendation"
        if reco_query
        else (
            "institutional_research_writer_publication_note"
            if irw_active
            else (
                "institutional_analyst_framework_cio_report"
                if iaf_active
                else (
                    "multi_layer_investment_decision_never_direct_buy_sell"
                    if ide_active
                    else "full_institutional_brief_even_when_recommendation_withheld"
                )
            )
        )
    )

    return {
        "enabled": True,
        "programme": PROGRAMME,
        "version": AC_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "query": query,
        "gate_blocked": blocked,
        "gate_logic_unchanged": True,
        "preserves_full_brief": True,
        "executive": exec_out,
        "thesis": thesis_out,
        "house_label": label,
        "bull": (list(irw.get("bull_case") or bull_out)[:6] if irw_active else bull_out[:6]),
        "base": (
            list(irw.get("base_case") or cio.get("base_case") or [])[:6]
            if irw_active or iaf_active
            else []
        ),
        "bear": (list(irw.get("bear_case") or bear_out)[:6] if irw_active else bear_out[:6]),
        "risks": risk_out[:8],
        "catalysts": cat_out[:8],
        "why": why_out[:12],
        "knowledge_gaps": gaps,
        "recommendation_status": reco,
        "institutional_answer": institutional_answer,
        "decision_engine_active": ide_active,
        "institutional_analysts_active": iaf_active,
        "institutional_research_writer_active": irw_active,
        "decision_conclusion": decision_conclusion,
        "institutional_analysts": iaf if iaf_active else {},
        "research_writer": irw if irw_active else {},
        "institutional_report": irw_report if irw_active else {},
        "section_owners": iaf.get("section_owners") if iaf_active else {},
        "answer_policy": answer_policy,
        "never_expose_checklist_keys": True,
        "decision_last": True if ide_active or iaf_active else None,
        "voice": "AGIB Institutional Intelligence",
        "max_lead_words": 60,
    }
