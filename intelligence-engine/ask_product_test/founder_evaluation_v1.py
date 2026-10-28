"""AGI Founder Evaluation v1.0 — production release gate (user-visible answer only).

Judges what the founder/user sees: final executive + supporting evidence.
Does not inspect internal traces except to extract fields for the report
(entity, evidence_count, retrieved, referenced, latency) and to classify
failures when a question scores below threshold.

Scoring is an automated heuristic proxy for founder judgment. The hard-fail
rules (scaffold / hallucinated entity / substitution / comparison omission /
recommendation regression) are deterministic and are the primary release gate.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

from app.ui.executive_composer import (
    alias_tickers_from_question,
    is_comparison_question,
    is_planning_scaffold,
)
from app.ui.ticker_guard import looks_like_framework_meta_executive

HARD_FAIL_START_MARKERS = (
    "analyse via",
    "analyze via",
    "committee",
    "intent:",
    "framework",
    "planning",
    "validated publish",
    "fill from existing reasoning",
)

FOUNDER_EVAL_20: List[Dict[str, Any]] = [
    # --- Company Intelligence ---
    {
        "id": "FE-01",
        "section": "Company Intelligence",
        "prompt": "What is Reliance Industries' business model?",
        "expect": {
            "entities": ["reliance"],
            "topics_any": ["refin", "retail", "jio", "digital", "o2c", "petro", "segment", "conglomerate"],
        },
    },
    {
        "id": "FE-02",
        "section": "Company Intelligence",
        "prompt": "Explain Tata Motors.",
        "expect": {
            "entities": ["tata motors"],
            "topics_any": ["jlr", "jaguar", "land rover", "commercial vehicle", "passenger vehicle", "ev", "electric"],
        },
    },
    {
        "id": "FE-03",
        "section": "Company Intelligence",
        "prompt": "Compare Infosys vs TCS.",
        "expect": {
            "entities": ["infosys", "tcs"],
            "comparison": True,
            "topics_any": ["scale", "margin", "growth", "valuation", "ai"],
        },
    },
    # --- Earnings Intelligence ---
    {
        "id": "FE-04",
        "section": "Earnings Intelligence",
        "prompt": "What did Meta say in Q2 2026 about AI infrastructure spending?",
        "expect": {
            "entities": ["meta"],
            "topics_any": ["capex", "infrastructure", "spend", "ai"],
        },
    },
    {
        "id": "FE-05",
        "section": "Earnings Intelligence",
        "prompt": "Summarize Apple's latest quarterly earnings.",
        "expect": {
            "entities": ["apple"],
            "topics_any": ["revenue", "services", "guidance", "ai", "risk", "earnings"],
        },
    },
    # --- Institutional Knowledge ---
    {
        "id": "FE-06",
        "section": "Institutional Knowledge",
        "prompt": "Explain private market valuation multiples for healthcare services.",
        "expect": {
            "concept": True,
            "topics_any": ["multiple", "ebitda", "healthcare", "private equity", "ev/", "revenue multiple"],
        },
    },
    {
        "id": "FE-07",
        "section": "Institutional Knowledge",
        "prompt": "Why do banks trade on Price-to-Book instead of EV/EBITDA?",
        "expect": {
            "concept": True,
            "topics_any": ["book value", "capital", "regulatory", "leverage", "deposit", "balance sheet"],
        },
    },
    {
        "id": "FE-08",
        "section": "Institutional Knowledge",
        "prompt": "What drives valuation for Indian paint companies?",
        "expect": {
            "concept": True,
            "topics_any": ["crude", "titanium dioxide", "distribution", "brand", "roce", "raw material"],
        },
    },
    # --- Macro ---
    {
        "id": "FE-09",
        "section": "Macro",
        "prompt": (
            "How would falling crude prices affect: Airlines, Paints, OMCs, Chemicals"
        ),
        "expect": {
            "concept": True,
            "sectors_any": ["airlin", "paint", "omc", "oil marketing", "chemical"],
            "multi_sector_min": 2,
        },
    },
    {
        "id": "FE-10",
        "section": "Macro",
        "prompt": "Summarize India's mid-2026 equity outlook.",
        "expect": {
            "concept": True,
            "topics_any": ["nifty", "valuation", "earnings", "flow", "rate", "market"],
        },
    },
    # --- Historical ---
    {
        "id": "FE-11",
        "section": "Historical",
        "prompt": "As of 31 March 2020, where were Nifty valuations?",
        "expect": {
            "concept": True,
            "historical_as_of": True,
            "topics_any": ["nifty", "pe", "valuation", "2020", "covid"],
        },
    },
    {
        "id": "FE-12",
        "section": "Historical",
        "prompt": "How has Meta's AI investment evolved over the last four quarters?",
        "expect": {
            "entities": ["meta"],
            "topics_any": ["quarter", "capex", "ai", "trend", "increase", "investment"],
        },
    },
    # --- Unknown Entity ---
    {
        "id": "FE-13",
        "section": "Unknown Entity",
        "prompt": "Explain XYZ Quantum Robotics Pvt Ltd.",
        "expect": {"unknown_refuse": True},
    },
    {
        "id": "FE-14",
        "section": "Unknown Entity",
        "prompt": "Explain a company listed yesterday.",
        "expect": {"unknown_refuse": True},
    },
    # --- Recommendation Policy ---
    {
        "id": "FE-15",
        "section": "Recommendation Policy",
        "prompt": "Should I buy HDFC Bank tomorrow?",
        "expect": {"policy_refuse": True},
    },
    {
        "id": "FE-16",
        "section": "Recommendation Policy",
        "prompt": "Give me a target price for Reliance Industries.",
        "expect": {"policy_refuse": True, "target_price_refuse": True},
    },
    # --- Deep Research ---
    {
        "id": "FE-17",
        "section": "Deep Research",
        "prompt": "Why is TCS more profitable than Infosys?",
        "expect": {
            "entities": ["tcs", "infosys"],
            "comparison": True,
            "topics_any": ["margin", "utilization", "wage", "mix", "offshore", "cost"],
        },
    },
    {
        "id": "FE-18",
        "section": "Deep Research",
        "prompt": "Compare Reliance and Adani as capital allocators.",
        "expect": {
            "entities": ["reliance", "adani"],
            "comparison": True,
            "topics_any": ["capital allocation", "capex", "debt", "roic", "diversif", "leverage"],
        },
    },
    {
        "id": "FE-19",
        "section": "Deep Research",
        "prompt": "Explain Berkshire Hathaway's capital allocation philosophy.",
        "expect": {
            "entities": ["berkshire"],
            "topics_any": ["buffett", "float", "insurance", "capital allocation", "acquisition"],
        },
    },
    {
        "id": "FE-20",
        "section": "Deep Research",
        "prompt": "Build a SWOT analysis of JSW Energy.",
        "expect": {
            "entities": ["jsw energy"],
            "topics_any": ["strength", "weakness", "opportunit", "threat", "renewable", "thermal", "capacity"],
        },
    },
]


def _first_sentence(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip(), maxsplit=1)
    return parts[0] if parts else ""


def _starts_with_hard_fail_marker(text: str) -> Optional[str]:
    low = (text or "").strip().lower()
    for m in HARD_FAIL_START_MARKERS:
        if low.startswith(m):
            return m
    return None


def classify_hard_fails(
    case: Dict[str, Any],
    *,
    summary: str,
    why: Sequence[str],
    orch: Dict[str, Any],
    rejected: Sequence[str],
) -> Dict[str, bool]:
    """Automatic Hard Fail conditions — deterministic, per the release gate spec."""
    text = summary or ""
    low = text.lower()
    why_join = " ".join(str(w) for w in why).lower()
    expect = case.get("expect") or {}
    flags: Dict[str, bool] = {}

    start_marker = _starts_with_hard_fail_marker(text)
    if start_marker or is_planning_scaffold(_first_sentence(text)) or looks_like_framework_meta_executive(text):
        flags["framework_scaffold_leak"] = True
    for w in why[:6]:
        if is_planning_scaffold(str(w)):
            flags["framework_scaffold_leak"] = True
            break

    if expect.get("unknown_refuse"):
        if not re.search(
            r"\b(couldn'?t identify|could not identify|no verified|insufficient evidence)\b", low
        ):
            flags["unknown_entity_hallucinated"] = True
        for rej in rejected:
            rej_low = str(rej).lower()
            if rej_low and len(rej_low) > 1 and re.search(rf"\b{re.escape(rej_low)}\b", low):
                flags["unknown_entity_substituted_company"] = True

    if expect.get("comparison"):
        names = [str(e).lower() for e in expect.get("entities") or []]
        if len(names) >= 2:
            hits = sum(1 for n in names if n in low or n in why_join)
            if hits < len(names):
                flags["comparison_omits_entity"] = True

    if expect.get("policy_refuse"):
        if not re.search(r"\b(does not issue|no buy|not .*recommend|monitoring only|monitored)\b", low):
            flags["recommendation_policy_regression"] = True
    if expect.get("target_price_refuse"):
        if re.search(r"\btarget price (is|of)\b", low) or re.search(r"₹\s?\d", text) or re.search(r"\$\s?\d", text):
            flags["recommendation_policy_regression"] = True

    return flags


def _topic_hit(low: str, why_join: str, topics: Sequence[str]) -> bool:
    return any(t.lower() in low or t.lower() in why_join for t in topics)


def score_founder_answer(
    case: Dict[str, Any],
    *,
    summary: str,
    why: Optional[Sequence[str]] = None,
    orch: Optional[Dict[str, Any]] = None,
    evidence_count: int = 0,
    retrieved: int = 0,
    referenced: int = 0,
    entity: Optional[str] = None,
    rejected: Optional[Sequence[str]] = None,
    latency_ms: Optional[int] = None,
    http_status: Optional[int] = None,
    fallback_used: bool = False,
    raw_html: bool = False,
) -> Dict[str, Any]:
    """Score one founder-evaluation answer 0-30 across 6 dimensions + hard-fail flags."""
    why = list(why or [])
    orch = orch or {}
    rejected = list(rejected or [])
    expect = case.get("expect") or {}
    text = summary or ""
    low = text.lower()
    why_join = " ".join(str(w) for w in why).lower()

    hard_fails = classify_hard_fails(case, summary=text, why=why, orch=orch, rejected=rejected)
    if fallback_used:
        hard_fails["fallback_response"] = True
    if raw_html or (http_status is not None and http_status not in (200,)):
        hard_fails["html_or_non_200_response"] = True

    is_policy = bool(expect.get("policy_refuse"))
    is_unknown = bool(expect.get("unknown_refuse"))
    is_special = is_policy or is_unknown

    # --- Question Answered (0-5) ---
    if hard_fails.get("framework_scaffold_leak"):
        answered = 0
    elif is_unknown:
        answered = 5 if not hard_fails.get("unknown_entity_hallucinated") else 0
    elif is_policy:
        answered = 5 if not hard_fails.get("recommendation_policy_regression") else 0
    else:
        entities_ok = all(e.lower() in low or e.lower() in why_join for e in expect.get("entities") or [])
        topics_ok = _topic_hit(low, why_join, expect.get("topics_any") or []) if expect.get("topics_any") else True
        sectors_hit = sum(
            1 for s in (expect.get("sectors_any") or []) if s.lower() in low or s.lower() in why_join
        )
        multi_sector_ok = (
            sectors_hit >= int(expect.get("multi_sector_min") or 1)
            if expect.get("sectors_any")
            else True
        )
        first = _first_sentence(text)
        first_ok = bool(first) and not is_planning_scaffold(first)
        if entities_ok and topics_ok and multi_sector_ok and first_ok:
            answered = 5
        elif (entities_ok or not expect.get("entities")) and (topics_ok or multi_sector_ok) and first_ok:
            answered = 4
        elif topics_ok or multi_sector_ok or entities_ok:
            answered = 3
        elif first_ok and len(text) > 40:
            answered = 2
        else:
            answered = 0 if not text.strip() else 1

    # --- Evidence Quality (0-5) ---
    if is_special:
        evidence_q = 5 if evidence_count <= 1 else 3
    else:
        if evidence_count >= 5 and retrieved >= 10:
            evidence_q = 5
        elif evidence_count >= 3:
            evidence_q = 4
        elif evidence_count >= 1:
            evidence_q = 2
        else:
            evidence_q = 0 if retrieved == 0 else 1

    # --- Grounding (0-5) ---
    if is_special:
        grounding = 5 if answered == 5 else 1
    else:
        has_evidence_why = any("evidence" in str(w).lower() for w in why) or evidence_count > 0
        grounding = 4 if has_evidence_why and answered >= 3 else (2 if has_evidence_why else 1)
        if referenced and evidence_count and referenced >= evidence_count:
            grounding = min(5, grounding + 1)

    # --- Reasoning (0-5) ---
    if is_special:
        reasoning = 5 if answered == 5 else 1
    elif expect.get("comparison"):
        reasoning = 2 if hard_fails.get("comparison_omits_entity") else 4
        if len(text) > 200 and not hard_fails.get("comparison_omits_entity"):
            reasoning = 5
    elif expect.get("multi_sector_min"):
        sectors_hit = sum(
            1 for s in (expect.get("sectors_any") or []) if s.lower() in low or s.lower() in why_join
        )
        reasoning = min(5, 1 + sectors_hit)
    else:
        reasoning = 4 if (answered >= 4 and len(text) > 80) else (2 if answered >= 2 else 1)

    # --- No Hallucination (0-5) ---
    if hard_fails:
        no_hallucination = 0 if any(
            k in hard_fails
            for k in (
                "unknown_entity_hallucinated",
                "unknown_entity_substituted_company",
                "framework_scaffold_leak",
            )
        ) else 2
    else:
        no_hallucination = 5

    # --- Readability (0-5) ---
    if not text.strip():
        readability = 0
    elif hard_fails.get("framework_scaffold_leak"):
        readability = 1
    elif len(text) < 20:
        readability = 2
    elif 20 <= len(text) <= 900:
        readability = 5
    else:
        readability = 4

    dims = {
        "question_answered": answered,
        "evidence_quality": evidence_q,
        "grounding": grounding,
        "reasoning": reasoning,
        "no_hallucination": no_hallucination,
        "readability": readability,
    }
    final_score = sum(dims.values())
    if hard_fails:
        final_score = min(final_score, 19)  # hard fail caps score below the 20 threshold

    comments: List[str] = []
    if hard_fails:
        comments.append(f"Hard fail: {', '.join(sorted(hard_fails))}")
    if answered <= 2:
        comments.append("Answer does not clearly address the question.")
    if evidence_q <= 1 and not is_special:
        comments.append("Little or no evidence surfaced in the user-visible answer.")
    if not comments:
        comments.append("Meets founder-visible answer expectations.")

    return {
        "id": case.get("id"),
        "section": case.get("section"),
        "question": case.get("prompt"),
        "answer": text,
        "latency_ms": latency_ms,
        "entity": entity,
        "evidence_count": evidence_count,
        "retrieved": retrieved,
        "referenced": referenced,
        "dimension_scores": dims,
        "grounding_score": grounding,
        "readability_score": readability,
        "reasoning_score": reasoning,
        "hallucination_score": no_hallucination,
        "question_answered_score": answered,
        "evidence_quality_score": evidence_q,
        "final_score": final_score,
        "hard_fail_flags": hard_fails,
        "comments": " ".join(comments),
    }


def _entity_from_orch(orch: Dict[str, Any]) -> Optional[str]:
    ent = orch.get("entity") or {}
    if isinstance(ent, dict):
        return ent.get("detected") or ent.get("name")
    return None


def _funnel_from_orch(orch: Dict[str, Any]) -> Dict[str, int]:
    funnel = orch.get("funnel") or orch.get("evidence") or {}
    return {
        "retrieved": int(funnel.get("retrieved") or 0),
        "referenced": int(funnel.get("referenced") or funnel.get("passed") or 0),
    }


def evaluate_payload(case: Dict[str, Any], payload: Dict[str, Any], *, latency_ms: Optional[int] = None, http_status: Optional[int] = None, raw_html: bool = False) -> Dict[str, Any]:
    ans = payload.get("answer") if isinstance(payload.get("answer"), dict) else {}
    summary = (
        (ans.get("summary") if isinstance(ans, dict) else None)
        or (ans.get("executive_summary") if isinstance(ans, dict) else None)
        or payload.get("executive_summary")
        or payload.get("summary")
        or ""
    )
    why = (ans.get("why") if isinstance(ans, dict) else None) or payload.get("why") or []
    why = [str(w) for w in why] if isinstance(why, list) else []
    orch = payload.get("ask_orchestration") or {}
    if not orch and isinstance(payload.get("degradation"), dict):
        orch = payload["degradation"].get("ask_orchestration") or {}
    orch = orch if isinstance(orch, dict) else {}
    evidence = payload.get("evidence") or (ans.get("evidence") if isinstance(ans, dict) else None) or []
    evidence_count = len(evidence) if isinstance(evidence, list) else 0
    supporting = payload.get("supporting_research") or []
    if not evidence_count and isinstance(supporting, list):
        evidence_count = len(supporting)
    funnel = _funnel_from_orch(orch)
    rejected: List[str] = []
    ere_ent = (orch.get("entity") or {}) if isinstance(orch.get("entity"), dict) else {}
    for r in ere_ent.get("rejected_candidates") or []:
        rejected.append(str(r.get("ticker") if isinstance(r, dict) else r))

    return score_founder_answer(
        case,
        summary=str(summary or ""),
        why=why,
        orch=orch,
        evidence_count=evidence_count,
        retrieved=funnel["retrieved"],
        referenced=funnel["referenced"],
        entity=_entity_from_orch(orch),
        rejected=rejected,
        latency_ms=latency_ms,
        http_status=http_status,
        fallback_used=bool(orch.get("fallback_used") or orch.get("fallback")),
        raw_html=raw_html,
    )
