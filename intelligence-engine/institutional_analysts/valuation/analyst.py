"""Valuation Analyst — Does today's price reflect long-term intrinsic value and expectations?"""

from __future__ import annotations

from typing import Any

from institutional_analysts.base import as_list, company_name, pick_confidence, structured_opinion, ticker_of
from institutional_analysts.flags import is_iai_valuation_enabled
from institutional_analysts.memory import get_previous_opinion


def _legacy_analyse(ctx: dict[str, Any]) -> dict[str, Any]:
    val = ctx.get("valuation") if isinstance(ctx.get("valuation"), dict) else {}
    ca = ctx.get("company_analysis") if isinstance(ctx.get("company_analysis"), dict) else {}
    ca_val = ca.get("valuation_intelligence") if isinstance(ca.get("valuation_intelligence"), dict) else {}
    dvc = ctx.get("data_validation") if isinstance(ctx.get("data_validation"), dict) else {}
    briefing = ctx.get("institutional_briefing") if isinstance(ctx.get("institutional_briefing"), dict) else {}
    de = ctx.get("decision_engine") if isinstance(ctx.get("decision_engine"), dict) else {}
    summary = de.get("summary") if isinstance(de.get("summary"), dict) else {}
    name = company_name(ctx)

    src = ca_val or val or {}
    multiples = src.get("multiples") if isinstance(src.get("multiples"), dict) else src
    mos = str(src.get("margin_of_safety") or "").lower()
    stance = "Neutral"
    if any(w in mos for w in ("high", "wide", "attractive", "ample")):
        stance = "Bullish"
    elif any(w in mos for w in ("modest", "thin", "limited", "rich", "low")):
        stance = "Bearish"
    pe = multiples.get("pe") or multiples.get("trailing_pe") or src.get("pe")
    try:
        if pe is not None and float(pe) >= 22:
            stance = "Bearish"
    except Exception:
        pass

    evidence = as_list(src.get("evidence") or src.get("peer_set") or dvc.get("valuation_checks"), limit=6)
    if not evidence:
        evidence = [f"Current valuation cross-checks for {name}", "Peer and history triangulation"]

    expected = summary.get("expected_return_12m_pct") or src.get("expected_return") or briefing.get("expected_return")
    coverage = pick_confidence(src.get("confidence"), summary.get("confidence_pct"), default=0.54)

    return structured_opinion(
        role="valuation",
        summary=(
            f"{name}: attractiveness depends on multiples versus history, peers, and expected return "
            "— not franchise storytelling."
        ),
        strengths=as_list(
            [
                f"Expected return context: {expected}" if expected is not None else "",
                src.get("peer_comparison") or "Peer multiples available as a cross-check",
            ],
            limit=4,
        )
        or ["Historical multiple context available"],
        weaknesses=as_list(src.get("risks") or ["Multiple compression", "Earnings miss versus expectations"], limit=4),
        evidence=evidence,
        unanswered_questions=[
            "How much growth is already discounted in today's multiple?",
            "What margin of safety remains if earnings undershoot?",
        ],
        sections={
            "historical_valuation": src.get("historical")
            or src.get("history")
            or "Compare current multiples with the franchise's own history",
            "current_multiples": {
                "pe": pe,
                "forward_pe": multiples.get("forward_pe") or src.get("forward_pe"),
                "pb": multiples.get("pb") or multiples.get("price_to_book") or src.get("pb"),
                "peg": multiples.get("peg") or src.get("peg"),
                "dividend_yield": multiples.get("dividend_yield") or src.get("dividend_yield"),
            },
            "peer_comparison": src.get("peer_comparison")
            or src.get("peers")
            or "Peer multiples used as a cross-check, not a verdict",
            "intrinsic_value": src.get("intrinsic_value")
            or src.get("fair_value")
            or "Intrinsic value band remains an estimate under uncertainty",
            "margin_of_safety": src.get("margin_of_safety")
            or "Margin of safety rises when price embeds pessimistic assumptions",
            "valuation_risks": src.get("risks") or ["Multiple compression", "Earnings miss versus expectations"],
            "expected_return": expected
            if expected is not None
            else "Scenario-weighted return depends on earnings path and multiple",
        },
        stance=stance,
        confidence={
            "evidence": pick_confidence(0.5 + 0.05 * min(len(evidence), 4), default=0.5),
            "knowledge": coverage,
            "freshness": pick_confidence(dvc.get("freshness"), default=0.52),
            "coverage": coverage,
        },
        ctx=ctx,
    )


def _evidence_pack(ctx: dict[str, Any], name: str) -> dict[str, Any]:
    val = ctx.get("valuation") if isinstance(ctx.get("valuation"), dict) else {}
    ca = ctx.get("company_analysis") if isinstance(ctx.get("company_analysis"), dict) else {}
    ca_val = ca.get("valuation_intelligence") if isinstance(ca.get("valuation_intelligence"), dict) else {}
    dvc = ctx.get("data_validation") if isinstance(ctx.get("data_validation"), dict) else {}
    briefing = ctx.get("institutional_briefing") if isinstance(ctx.get("institutional_briefing"), dict) else {}
    de = ctx.get("decision_engine") if isinstance(ctx.get("decision_engine"), dict) else {}
    summary = de.get("summary") if isinstance(de.get("summary"), dict) else {}
    sector = ctx.get("sector_intelligence") if isinstance(ctx.get("sector_intelligence"), dict) else {}
    fin = ca.get("financial_intelligence") if isinstance(ca.get("financial_intelligence"), dict) else {}

    src = ca_val or val or {}
    multiples = src.get("multiples") if isinstance(src.get("multiples"), dict) else src
    pe = multiples.get("pe") or multiples.get("trailing_pe") or src.get("pe")
    expected = summary.get("expected_return_12m_pct") or src.get("expected_return") or briefing.get("expected_return")

    refs = as_list(src.get("evidence") or src.get("peer_set") or dvc.get("valuation_checks"), limit=6)
    if not refs:
        refs = [f"Current valuation cross-checks for {name}", "Peer and history triangulation"]

    return {
        "company": name,
        "ticker": ticker_of(ctx),
        "pe": pe,
        "forward_pe": multiples.get("forward_pe") or src.get("forward_pe"),
        "pb": multiples.get("pb") or multiples.get("price_to_book") or src.get("pb"),
        "ps": multiples.get("ps") or src.get("ps"),
        "ev": multiples.get("ev") or src.get("ev"),
        "ev_ebitda": multiples.get("ev_ebitda") or src.get("ev_ebitda"),
        "ev_sales": multiples.get("ev_sales") or src.get("ev_sales"),
        "peg": multiples.get("peg") or src.get("peg"),
        "dividend_yield": multiples.get("dividend_yield") or src.get("dividend_yield"),
        "margin_of_safety": src.get("margin_of_safety"),
        "intrinsic_value": src.get("intrinsic_value") or src.get("fair_value"),
        "fair_value": src.get("fair_value"),
        "peer_comparison": src.get("peer_comparison") or src.get("peers"),
        "peers": src.get("peers"),
        "historical": src.get("historical") or src.get("history"),
        "history": src.get("history"),
        "narrative": src.get("narrative") or "",
        "risks": as_list(src.get("risks"), limit=5),
        "expected_return": expected,
        "indian_peers": as_list(sector.get("indian_peers") or sector.get("peers"), limit=4),
        "global_peers": as_list(sector.get("global_peers"), limit=4),
        "growth_context": fin.get("trend") or fin.get("narrative") or "",
        "capital_efficiency_context": fin.get("roe") or fin.get("roic") or "",
        "evidence_refs": [{"claim": r, "source_ref": "institutional research"} for r in refs],
    }


def analyse(ctx: dict[str, Any]) -> dict[str, Any]:
    if not is_iai_valuation_enabled():
        return _legacy_analyse(ctx)

    from institutional_analysts.valuation.brain import think

    name = company_name(ctx)
    val = ctx.get("valuation") if isinstance(ctx.get("valuation"), dict) else {}
    ca = ctx.get("company_analysis") if isinstance(ctx.get("company_analysis"), dict) else {}
    ca_val = ca.get("valuation_intelligence") if isinstance(ca.get("valuation_intelligence"), dict) else {}
    dvc = ctx.get("data_validation") if isinstance(ctx.get("data_validation"), dict) else {}
    de = ctx.get("decision_engine") if isinstance(ctx.get("decision_engine"), dict) else {}
    summary = de.get("summary") if isinstance(de.get("summary"), dict) else {}
    src = ca_val or val or {}

    evidence = _evidence_pack(ctx, name)
    coverage = pick_confidence(src.get("confidence"), summary.get("confidence_pct"), default=0.54)
    conf = {
        "evidence": pick_confidence(0.5 + 0.05 * min(len(evidence.get("evidence_refs") or []), 4), default=0.5),
        "knowledge": coverage,
        "freshness": pick_confidence(dvc.get("freshness"), default=0.52),
        "coverage": coverage,
        "valuation_coverage": coverage,
        "historical_coverage": coverage,
    }

    previous = get_previous_opinion(ticker_of(ctx), "valuation")
    brain = think(
        company=name,
        evidence=evidence,
        previous=previous,
        confidence=conf,
        ticker=ticker_of(ctx),
    )
    conf_out = brain.get("confidence") if isinstance(brain.get("confidence"), dict) else conf
    text = str(brain.get("summary") or brain.get("executive_opinion") or "")

    base = structured_opinion(
        role="valuation",
        summary=text,
        strengths=list(brain.get("strengths") or []),
        weaknesses=list(brain.get("weaknesses") or []),
        evidence=[
            (e.get("claim") if isinstance(e, dict) else str(e))
            for e in (evidence.get("evidence_refs") or [])
        ],
        unanswered_questions=list(brain.get("unanswered_questions") or brain.get("missing_evidence") or []),
        sections={
            "historical_valuation": (brain.get("historical_valuation") or {}).get("assessment")
            or evidence.get("historical")
            or "Compare current multiples with history",
            "current_multiples": (brain.get("multiple_analysis") or {}).get("multiples")
            or {
                "pe": evidence.get("pe"),
                "forward_pe": evidence.get("forward_pe"),
                "pb": evidence.get("pb"),
                "peg": evidence.get("peg"),
                "dividend_yield": evidence.get("dividend_yield"),
            },
            "peer_comparison": (brain.get("peer_comparison") or {}).get("assessment")
            or evidence.get("peer_comparison"),
            "intrinsic_value": (brain.get("intrinsic_value_view") or {}).get("assessment")
            or evidence.get("intrinsic_value"),
            "margin_of_safety": (brain.get("margin_of_safety") or {}).get("assessment")
            or evidence.get("margin_of_safety"),
            "valuation_risks": list(brain.get("weaknesses") or [])
            or ["Multiple compression", "Earnings miss versus expectations"],
            "expected_return": evidence.get("expected_return")
            if evidence.get("expected_return") is not None
            else "Scenario-weighted return depends on earnings path and multiple",
            "executive_opinion": brain.get("executive_opinion"),
            "valuation_dna_profile": (brain.get("valuation_dna") or {}).get("profile"),
            "iai_version": brain.get("iai_version"),
            "quality_status": (brain.get("quality_checks") or {}).get("status"),
        },
        stance=str(brain.get("stance") or "Neutral"),
        confidence=conf_out,
        ctx=ctx,
    )

    structured = brain.get("structured_valuation_opinion") or {}
    for key in (
        "executive_opinion",
        "intrinsic_value_view",
        "market_expectations",
        "valuation_quality",
        "multiple_analysis",
        "dcf_discussion",
        "relative_valuation",
        "historical_valuation",
        "margin_of_safety",
        "valuation_dna",
        "historical_trend",
        "peer_comparison",
        "assumptions",
        "uncertainties",
        "missing_evidence",
        "quality_checks",
    ):
        if key in structured:
            base[key] = structured[key]
        elif brain.get(key) is not None:
            base[key] = brain.get(key)

    base["structured_valuation_opinion"] = structured
    base["case_studies"] = brain.get("case_studies")
    base["archetype"] = brain.get("archetype")
    base["historical_outcomes"] = brain.get("historical_outcomes")
    base["lessons_learned"] = brain.get("lessons_learned")
    base["learning_chain"] = brain.get("learning_chain")
    base["scenario_valuation"] = brain.get("scenario_valuation")
    base["reasoning"] = brain.get("reasoning")
    base["validation"] = brain.get("validation")
    base["analyst_memory"] = brain.get("memory")
    base["trajectory"] = brain.get("trajectory")
    base["primary_question_answer"] = brain.get("primary_question_answer")
    base["institutional_valuation_opinion"] = brain.get("institutional_valuation_opinion") or text
    base["iai_version"] = brain.get("iai_version")
    base["iai_active"] = True
    base["iai_valuation_v1"] = True
    base["ready_for_committee"] = brain.get("ready_for_committee")

    if isinstance(base.get("confidence"), dict):
        for k in ("valuation_coverage", "historical_coverage", "reasoning"):
            if k in conf_out:
                base["confidence"][k] = conf_out[k]

    if previous:
        wc = base.get("what_changed") if isinstance(base.get("what_changed"), dict) else {}
        notes = list(wc.get("notes") or [])
        for note in brain.get("what_changed") or []:
            if note and note not in notes:
                notes.append(note)
        if wc:
            wc["notes"] = notes[:6]
            wc["trajectory"] = brain.get("trajectory")
            base["what_changed"] = wc
        elif notes:
            base["what_changed"] = {
                "previous_stance": previous.get("stance"),
                "current_stance": base.get("stance"),
                "changed": True,
                "notes": notes[:6],
                "trajectory": brain.get("trajectory"),
            }

    return base
