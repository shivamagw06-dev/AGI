"""Chief Investment Officer — editor of the institutional report.

Reads ONLY committee outputs. Never repeats analyst wording.
Never mentions engines, providers, dossiers, or research subsystems.
"""

from __future__ import annotations

from typing import Any

from institutional_analysts.base import as_list, pick_confidence, scrub_public


def _fresh(*parts: str, limit: int = 420) -> str:
    """Join and scrub — CIO voice only."""
    text = scrub_public(" ".join(p for p in parts if p), limit=limit)
    banned = (
        "company analysis",
        "financial intelligence",
        "academy",
        "yahoo",
        "groww",
        "indianapi",
        "capital iq",
        "cid",
        "leo",
        "irp",
        "dvc",
        "ecp",
        "provider",
        "engine",
    )
    low = text.lower()
    for b in banned:
        if b in low:
            text = scrub_public(text.replace(b, "").replace(b.title(), ""), limit=limit)
            low = text.lower()
    return text


def write_report(committee: dict[str, Any], *, query: str = "", company: str = "") -> dict[str, Any]:
    """CIO never consumes raw provider data — committee signals / ICI decision only."""
    name = company or "the company"
    signals = committee.get("cio_signals") if isinstance(committee.get("cio_signals"), dict) else {}
    matrix = committee.get("disagreement_matrix") if isinstance(committee.get("disagreement_matrix"), dict) else {}
    minutes = committee.get("minutes") if isinstance(committee.get("minutes"), dict) else {}
    decision = committee.get("decision") or signals.get("decision") or {}
    vote = committee.get("vote") or committee.get("stage_5_vote") or {}
    stances = signals.get("stances") if isinstance(signals.get("stances"), dict) else committee.get("stage_1_consensus") or {}
    conflicts = signals.get("conflicts") if isinstance(signals.get("conflicts"), list) else []
    challenges = signals.get("challenges") if isinstance(signals.get("challenges"), list) else []
    missing = as_list(signals.get("missing_evidence") or committee.get("stage_3_missing_evidence"), limit=5)
    risk_items = as_list(signals.get("risk_items") or (committee.get("consensus") or {}).get("risks"), limit=5)
    minority = as_list(signals.get("minority") or [m.get("view") for m in (committee.get("minority_opinions") or []) if isinstance(m, dict)], limit=3)

    committee_stance = (
        decision.get("committee_position")
        or signals.get("committee_stance")
        or matrix.get("committee_stance")
        or committee.get("committee_stance")
        or vote.get("consensus")
        or "Neutral"
    )
    conviction = vote.get("conviction") or matrix.get("conviction") or signals.get("conviction") or "Moderate"
    tally = vote.get("tally") or matrix.get("vote") or signals.get("vote") or ""
    reason = signals.get("reason") or matrix.get("reason") or committee.get("committee_reason") or ""
    conf = pick_confidence(decision.get("confidence"), committee.get("confidence"), default=0.55)

    biz_s = stances.get("business") or "Neutral"
    fin_s = stances.get("financial") or "Neutral"
    val_s = stances.get("valuation") or "Neutral"
    macro_s = stances.get("macro") or "Neutral"
    risk_s = stances.get("risk") or "Neutral"

    exec_summary = _fresh(
        f"{name}: the desk holds a {str(committee_stance).lower()} institutional view "
        f"with {str(conviction).lower()} conviction"
        + (f" (committee vote {tally})" if tally else "")
        + ".",
        f"Business quality {decision.get('business_quality') or biz_s.lower()}; "
        f"financials {decision.get('financials') or fin_s.lower()}; "
        f"valuation {decision.get('valuation') or val_s.lower()}; "
        f"risk {decision.get('risk') or risk_s.lower()}.",
        reason,
        limit=420,
    )

    thesis = _fresh(
        f"Own {name} only when franchise durability and financial quality justify the entry after macro transmission.",
        "Position sizing should respect the valuation cushion, live risk register, and committee conviction.",
        limit=360,
    )

    if biz_s == "Bullish" and val_s != "Bearish":
        bull = [
            _fresh("Franchise delivery exceeds the base path and returns expand while the entry multiple stays reasonable."),
            _fresh("Sector demand and operating leverage reinforce compounding."),
        ]
    else:
        bull = [
            _fresh("Quality compounds and the entry multiple mean-reverts toward a more supportive band."),
            _fresh("Financial conversion improves enough to reopen upside optionality."),
        ]

    base = [
        _fresh("Mid-cycle delivery with stable returns; valuation tracks fundamentals without a re-rating windfall."),
        _fresh(f"Macro remains {macro_s.lower()} and does not force a thesis break."),
    ]

    bear = [
        _fresh("Growth or margins disappoint and the multiple compresses."),
        *[_fresh(r, limit=160) for r in risk_items[:2]],
    ]
    if val_s == "Bearish":
        bear.insert(0, _fresh("Rich starting valuation leaves little room for an earnings miss."))

    catalysts = [
        "Next earnings print and management commentary",
        "Evidence of durable returns / asset quality",
        "Clearer valuation margin of safety",
    ]
    if missing:
        catalysts = [missing[0], *catalysts]
    if challenges:
        need = challenges[0].get("need")
        if need:
            catalysts = [_fresh(need, limit=160), *catalysts]

    conflict_line = ""
    if conflicts:
        tension = conflicts[0].get("tension") or conflicts[0].get("topic")
        conflict_line = f"Core committee tension: {tension}."

    minority_line = ""
    if minority:
        minority_line = f"Minority view noted: {minority[0]}"

    follow = minutes.get("follow_up") or "Reassess after the next material evidence update."
    readiness = (
        decision.get("recommendation_readiness")
        or committee.get("recommendation_readiness_label")
        or committee.get("recommendation_readiness")
        or "partial"
    )
    conclusion = _fresh(
        f"Institutional conclusion remains {str(committee_stance).lower()} — an assessment, not a trade ticket.",
        conflict_line,
        minority_line,
        f"Recommendation readiness: {readiness}.",
        follow,
        limit=400,
    )

    why = [
        _fresh(f"Committee vote {tally or 'n/a'} → {committee_stance} ({conviction} conviction)."),
        _fresh(f"Business {decision.get('business_quality') or biz_s}; financials {decision.get('financials') or fin_s}."),
        _fresh(f"Valuation {decision.get('valuation') or val_s}; risk {decision.get('risk') or risk_s}."),
        _fresh(reason, limit=200),
    ]

    what_changed_notes = []
    for row in signals.get("what_changed") or []:
        if isinstance(row, dict):
            for note in as_list(row.get("notes"), limit=2):
                what_changed_notes.append(_fresh(f"{row.get('analyst')}: {note}", limit=180))

    return {
        "owner": "cio",
        "analyst": "Chief Investment Officer",
        "role": "editor",
        "query": query,
        "company": name,
        "executive_summary": exec_summary,
        "investment_thesis": thesis,
        "bull_case": [x for x in bull if x][:4],
        "base_case": [x for x in base if x][:4],
        "bear_case": [x for x in bear if x][:4],
        "key_risks": risk_items[:6] or ["Execution", "Earnings miss", "Multiple compression"],
        "key_catalysts": [c for c in catalysts if c][:6],
        "institutional_conclusion": conclusion,
        "confidence": conf,
        "recommendation_readiness": readiness,
        "committee_stance": committee_stance,
        "committee_conviction": conviction,
        "committee_vote": tally,
        "committee_decision": decision,
        "disagreement_matrix": matrix,
        "minority_opinions": minority,
        "why": [w for w in why if w][:6],
        "what_changed": what_changed_notes[:6],
        "editor_rules": {
            "never_repeat_analyst_wording": True,
            "never_mention_engines": True,
            "never_mention_providers": True,
            "institutional_language_only": True,
            "recommendation_is_committee_vote": True,
        },
    }
