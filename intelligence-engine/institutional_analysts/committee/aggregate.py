"""Investment Committee adapter — soft-calls ICI V1 deliberation when enabled."""

from __future__ import annotations

from typing import Any

from institutional_analysts.base import as_list, pick_confidence, scrub_public

_ROLES = ["business", "financial", "valuation", "market", "sector", "macro", "risk", "management", "ownership"]


def aggregate(
    opinions: dict[str, dict[str, Any]],
    *,
    query: str = "",
    company: str = "",
    ticker: str | None = None,
) -> dict[str, Any]:
    """Prefer Investment Committee Intelligence deliberation; fallback to legacy merge."""
    try:
        from investment_committee.flags import is_enabled as ici_enabled
        from investment_committee.production import package_for_ask_agi as ici_package

        if ici_enabled():
            ici = ici_package(opinions, query=query, company=company, ticker=ticker) or {}
            if ici.get("enabled"):
                return _adapt_ici(ici, opinions)
    except Exception:
        pass
    return _legacy_aggregate(opinions)


def _adapt_ici(ici: dict[str, Any], opinions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Map ICI pack onto the IAF committee contract expected by CIO / UI."""
    desk = ici.get("desk_views") if isinstance(ici.get("desk_views"), dict) else {}
    decision = ici.get("decision") if isinstance(ici.get("decision"), dict) else {}
    vote = ici.get("vote") if isinstance(ici.get("vote"), dict) else {}
    minutes = ici.get("minutes") if isinstance(ici.get("minutes"), dict) else {}

    # Preserve discussion labels on minutes for UI that reads minutes.business etc.
    discussion = minutes.get("discussion") if isinstance(minutes.get("discussion"), dict) else {}
    ui_minutes = {
        **minutes,
        "business": discussion.get("business") or minutes.get("business"),
        "financials": discussion.get("financials") or minutes.get("financials"),
        "valuation": discussion.get("valuation") or minutes.get("valuation"),
        "macro": discussion.get("macro") or minutes.get("macro"),
        "decision": minutes.get("decision"),
        "follow_up": minutes.get("follow_up"),
    }

    return {
        "owner": "committee",
        "analyst": "Investment Committee",
        "question": ici.get("question") or "What is the coordinated institutional view?",
        "meeting": True,
        "ici_enabled": True,
        "ici": ici,
        "stage_1_consensus": ici.get("stage_1_consensus") or {},
        "stage_1_detail": ici.get("stage_1_detail") or ici.get("consensus"),
        "stage_2_conflicts": ici.get("stage_2_conflicts") or [],
        "stage_3_missing_evidence": ici.get("stage_3_missing_evidence") or [],
        "stage_3_challenges": ici.get("stage_3_challenges") or [],
        "stage_4_confidence": ici.get("stage_4_confidence") or {},
        "stage_5_vote": vote,
        "stage_6_minutes": ui_minutes,
        "stage_7_minority": ici.get("stage_7_minority") or [],
        "stage_8_timeline": ici.get("stage_8_timeline") or [],
        "stage_9_accuracy": ici.get("stage_9_accuracy") or {},
        "stage_10_decision": decision,
        "disagreement_matrix": ici.get("disagreement_matrix") or {},
        "minutes": ui_minutes,
        "committee_summary": scrub_public(ici.get("committee_summary"), limit=360),
        "consensus": {
            "business": desk.get("business"),
            "financial": desk.get("financial"),
            "valuation": desk.get("valuation"),
            "market": desk.get("market"),
            "sector": desk.get("sector"),
            "macro": desk.get("macro"),
            "risks": desk.get("risks") or ["Execution", "Earnings", "Multiple compression"],
            "management": desk.get("management"),
            "ownership": desk.get("ownership"),
        },
        "agreements": ici.get("agreements") or [],
        "disagreements": ici.get("disagreements") or [],
        "conflicts": ici.get("conflicts") or [],
        "challenges": ici.get("challenges") or [],
        "minority_opinions": ici.get("minority_opinions") or [],
        "vote": vote,
        "decision": decision,
        "confidence_recalibration": ici.get("confidence_recalibration") or {},
        "open_evidence_requests": ici.get("open_evidence_requests") or [],
        "timeline": ici.get("timeline") or [],
        "accuracy": ici.get("accuracy") or {},
        "missing_evidence": ici.get("missing_evidence") or [],
        "confidence": pick_confidence(ici.get("confidence"), decision.get("confidence"), default=0.55),
        "recommendation_readiness": ici.get("recommendation_readiness") or "partial",
        "recommendation_readiness_label": ici.get("recommendation_readiness_label")
        or decision.get("recommendation_readiness"),
        "committee_stance": ici.get("committee_stance") or vote.get("consensus"),
        "committee_reason": ici.get("committee_reason"),
        "conviction": vote.get("conviction"),
        "vote_tally": vote.get("tally"),
        "opinions_count": ici.get("opinions_count") or len(opinions),
        "analyst_roles_present": ici.get("analyst_roles_present") or list(opinions.keys()),
        "cio_signals": ici.get("cio_signals") or {},
    }


def _legacy_aggregate(opinions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Minimal fallback if ICI is disabled — preserves prior IAF committee shape."""
    present = {
        r: opinions[r]
        for r in _ROLES
        if isinstance(opinions.get(r), dict) and (opinions[r].get("summary") or opinions[r].get("headline"))
    }
    stances = {
        r: str((present[r].get("stance") if r in present else "Missing") or "Missing") for r in _ROLES
    }
    confs = []
    for op in present.values():
        c = op.get("confidence")
        confs.append(float((c or {}).get("overall") if isinstance(c, dict) else (c or 0.55)))
    conf = pick_confidence(sum(confs) / len(confs) if confs else 0.55)
    stance = "Constructive" if list(stances.values()).count("Bullish") >= 4 else "Neutral"
    minutes = {
        "title": "Investment Committee Minutes",
        "business": stances.get("business"),
        "financials": stances.get("financial"),
        "valuation": stances.get("valuation"),
        "macro": stances.get("macro"),
        "decision": f"Remain {stance.lower()}.",
        "follow_up": "Need confirmation after next earnings.",
    }
    return {
        "owner": "committee",
        "analyst": "Investment Committee",
        "question": "What is the coordinated institutional view?",
        "meeting": True,
        "ici_enabled": False,
        "stage_1_consensus": stances,
        "stage_2_conflicts": [],
        "stage_3_missing_evidence": as_list(
            [q for op in present.values() for q in (op.get("unanswered_questions") or [])],
            limit=6,
        ),
        "disagreement_matrix": {
            "analyst_stances": {(present[r].get("analyst") if r in present else r): stances[r] for r in _ROLES},
            "committee_stance": stance,
            "reason": "Legacy committee merge (ICI disabled).",
        },
        "minutes": minutes,
        "committee_summary": scrub_public(f"Committee reviewed specialist opinions. Stance: {stance}.", limit=280),
        "consensus": {r: stances.get(r) for r in ("business", "financial", "valuation", "market", "macro")},
        "agreements": [],
        "disagreements": [],
        "conflicts": [],
        "missing_evidence": [],
        "confidence": conf,
        "recommendation_readiness": "partial",
        "committee_stance": stance,
        "committee_reason": "Legacy committee merge (ICI disabled).",
        "opinions_count": len(present),
        "analyst_roles_present": list(present.keys()),
        "cio_signals": {
            "stances": stances,
            "committee_stance": stance,
            "reason": "Legacy committee merge (ICI disabled).",
            "conflicts": [],
            "missing_evidence": [],
            "risk_items": as_list((present.get("risk") or {}).get("weaknesses"), limit=5),
            "what_changed": [],
        },
    }
