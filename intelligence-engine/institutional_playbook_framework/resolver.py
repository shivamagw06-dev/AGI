"""Resolve framework playbook from question, intent, and IAP selection."""

from __future__ import annotations

import re
from typing import Any

from institutional_playbook_framework.registry import PLAYBOOK_REGISTRY, get_playbook


def _match_cues(question: str, cues: tuple[str, ...]) -> bool:
    low = (question or "").lower()
    for cue in cues:
        c = cue.strip().lower()
        if not c:
            continue
        if " " in c or "/" in c:
            if c in low:
                return True
        elif re.search(rf"(?<![a-z0-9]){re.escape(c)}(?![a-z0-9])", low):
            return True
    return False


_IRL_TO_PLAYBOOK: dict[str, str] = {
    "Analyse": "investment_assessment",
    "Valuation": "valuation_assessment",
    "Compare": "peer_comparison",
    "Portfolio": "portfolio_assessment",
    "Risk": "risk_assessment",
    "Explain": "education",
    "Education": "education",
    "Industry": "sector_analysis",
    "Macro": "macro_analysis",
    "Government": "macro_analysis",
    "CorporateEvents": "news_impact",
    "Documents": "financial_analysis",
    "Accounting": "financial_analysis",
    "HistoricalReplay": "thesis_evolution",
    "CrossDomain": "investment_assessment",
    "Unknown": "education",
}

_IAP_TO_PLAYBOOK: dict[str, str] = {
    "PB_COMPANY_QUALITY": "business_quality_assessment",
    "PB_COMPANY_MOAT": "economic_moat",
    "PB_COMPANY_EARNINGS": "earnings_review",
    "PB_VALUATION_RELATIVE": "valuation_assessment",
    "PB_VALUATION_PEER": "peer_comparison",
    "PB_VALUATION_DCF": "valuation_assessment",
    "PB_MACRO_REGIME": "market_overview",
    "PB_INDUSTRY_STRUCTURE": "sector_analysis",
}


def resolve_playbook(
    question: str,
    *,
    irl_intent: str | None = None,
    playbook_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select Institutional Playbook Framework entry for this Ask."""
    q = (question or "").strip()
    low = q.lower()
    iap = playbook_selection or {}
    iap_id = str(iap.get("playbook_id") or "")

    # 1. Question cue match (highest signal for real user intent)
    cue_hits: list[tuple[int, int, str]] = []
    for key, pb in PLAYBOOK_REGISTRY.items():
        if pb.get("alias_of"):
            continue
        cues = pb.get("question_cues") or ()
        for cue in cues:
            c = str(cue).strip().lower()
            if not c:
                continue
            matched = False
            if " " in c or "/" in c:
                matched = c in low
            else:
                matched = re.search(rf"(?<![a-z0-9]){re.escape(c)}(?![a-z0-9])", low) is not None
            if matched:
                cue_hits.append((len(c), -int(pb.get("priority") or 50), key))
    if cue_hits:
        cue_hits.sort(key=lambda x: (-x[0], x[1], x[2]))
        chosen = get_playbook(cue_hits[0][2]) or {}
        return _pack_resolution(chosen, source="question_cue", question=q)

    # 2. IAP selection bridge
    if iap_id and iap_id in _IAP_TO_PLAYBOOK:
        chosen = get_playbook(_IAP_TO_PLAYBOOK[iap_id]) or {}
        return _pack_resolution(chosen, source="iap_selection", question=q, iap_playbook_id=iap_id)

    # 3. IRL intent
    intent = (irl_intent or "").strip()
    if intent and intent in _IRL_TO_PLAYBOOK:
        chosen = get_playbook(_IRL_TO_PLAYBOOK[intent]) or {}
        return _pack_resolution(chosen, source="irl_intent", question=q, irl_intent=intent)

    # 4. Default
    chosen = get_playbook("investment_assessment") or {}
    return _pack_resolution(chosen, source="default", question=q)


def _pack_resolution(
    playbook: dict[str, Any],
    *,
    source: str,
    question: str,
    irl_intent: str | None = None,
    iap_playbook_id: str | None = None,
) -> dict[str, Any]:
    key = str(playbook.get("playbook_key") or "investment_assessment")
    return {
        "playbook_key": key,
        "name": playbook.get("name"),
        "purpose": playbook.get("purpose"),
        "source": source,
        "question": question,
        "irl_intent": irl_intent,
        "iap_playbook_id": iap_playbook_id or playbook.get("iap_playbook_id"),
        "required_intelligence": list(playbook.get("required_intelligence") or []),
        "required_evidence": list(playbook.get("required_evidence") or []),
        "reasoning_framework": list(playbook.get("reasoning_framework") or []),
        "output_contract": list(playbook.get("output_contract") or []),
        "follow_up_templates": list(playbook.get("follow_up_templates") or []),
        "acceptance_tests": list(playbook.get("acceptance_tests") or []),
        "journey_steps": list(playbook.get("journey_steps") or []),
        "execution_pipeline": [
            "Intent",
            "Evidence",
            "Reasoning",
            "Trade-offs",
            "Research Conclusion",
            "Questions Before You Decide",
        ],
    }
