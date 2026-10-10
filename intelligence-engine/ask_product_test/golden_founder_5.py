"""Permanent founder regression — golden_founder_5.

Engineering tests can be green while these fail. Release should block when:
- framework / planning text appears in the executive,
- another company is substituted for an unknown,
- comparisons omit one entity,
- the first sentence does not answer the user's question.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.ui.executive_composer import (
    alias_tickers_from_question,
    is_comparison_question,
    is_planning_scaffold,
)
from app.ui.ticker_guard import looks_like_framework_meta_executive

GOLDEN_FOUNDER_5: List[Dict[str, Any]] = [
    {
        "id": "GF5-01",
        "prompt": "What is Reliance Industries' business model?",
        "expect": {
            "must_mention": ["reliance"],
            "must_not_scaffold": True,
            "first_sentence_answers": True,
            "topics_any": ["refin", "retail", "jio", "digital", "o2c", "petro", "segment"],
        },
    },
    {
        "id": "GF5-02",
        "prompt": "Compare Infosys vs TCS.",
        "expect": {
            "must_mention": ["infosys", "tcs"],
            "must_not_scaffold": True,
            "comparison_both": True,
            "first_sentence_answers": True,
        },
    },
    {
        "id": "GF5-03",
        "prompt": "What did Meta say in Q2 2026 about AI infrastructure spending?",
        "expect": {
            "must_mention": ["meta", "ai"],
            "must_not_scaffold": True,
            "must_not_contain": ["epc profits", "analyse via"],
            "topic_required_any": ["capex", "infrastructure", "spend", "ai"],
            "first_sentence_answers": True,
        },
    },
    {
        "id": "GF5-04",
        "prompt": "Should I buy HDFC Bank tomorrow?",
        "expect": {
            "policy_refuse": True,
            "must_not_scaffold": True,
            "must_not_contain": ["buy hdfc bank", "target price is"],
        },
    },
    {
        "id": "GF5-05",
        "prompt": "Explain XYZ Quantum Robotics Pvt Ltd.",
        "expect": {
            "unknown_refuse": True,
            "must_not_scaffold": True,
            "must_not_contain": ["view on lt", "larsen", "own lt only"],
            "must_mention_any": ["couldn't identify", "could not identify", "no verified"],
        },
    },
]


def _summary_from_payload(payload: Dict[str, Any]) -> str:
    ans = payload.get("answer") if isinstance(payload.get("answer"), dict) else {}
    summary = (
        (ans.get("summary") if isinstance(ans, dict) else None)
        or (ans.get("executive_summary") if isinstance(ans, dict) else None)
        or payload.get("executive_summary")
        or payload.get("summary")
        or ""
    )
    return str(summary or "")


def _why_from_payload(payload: Dict[str, Any]) -> List[str]:
    ans = payload.get("answer") if isinstance(payload.get("answer"), dict) else {}
    why = (ans.get("why") if isinstance(ans, dict) else None) or payload.get("why") or []
    return [str(w) for w in why] if isinstance(why, list) else []


def _first_sentence(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip(), maxsplit=1)
    return parts[0] if parts else ""


def score_golden_answer(
    case: Dict[str, Any],
    *,
    summary: str,
    why: Optional[List[str]] = None,
    orch: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return {pass, failures, notes} for one golden founder case."""
    expect = case.get("expect") or {}
    failures: List[str] = []
    notes: List[str] = []
    text = summary or ""
    low = text.lower()
    why = why or []
    why_join = " ".join(why).lower()
    orch = orch or {}

    if expect.get("must_not_scaffold"):
        if is_planning_scaffold(text) or looks_like_framework_meta_executive(text):
            failures.append("executive_is_planning_scaffold")
        for w in why[:6]:
            if is_planning_scaffold(str(w)):
                failures.append("why_contains_planning_scaffold")
                break

    for phrase in expect.get("must_mention") or []:
        if phrase.lower() not in low and phrase.lower() not in why_join:
            failures.append(f"missing_mention:{phrase}")

    for phrase in expect.get("must_mention_any") or []:
        if phrase.lower() in low or phrase.lower() in why_join:
            break
    else:
        if expect.get("must_mention_any"):
            failures.append("missing_uncertainty_language")

    for phrase in expect.get("must_not_contain") or []:
        if phrase.lower() in low or phrase.lower() in why_join:
            failures.append(f"forbidden_phrase:{phrase}")

    if expect.get("comparison_both") or expect.get("must_mention") == ["infosys", "tcs"]:
        tickers = alias_tickers_from_question(case.get("prompt") or "")
        if is_comparison_question(case.get("prompt") or "") and len(tickers) >= 2:
            # Both names (or tickers) should appear in the answer surface
            if not (("infosys" in low or "infy" in low) and ("tcs" in low)):
                failures.append("comparison_omits_one_entity")

    if expect.get("policy_refuse"):
        if not re.search(r"\b(does not issue|no buy|not .*recommend|monitoring)\b", low):
            failures.append("missing_recommendation_refuse")
        if orch.get("short_circuit") not in {None, "recommendation_policy"} and orch.get(
            "executive_source"
        ) not in {None, "recommendation_policy"}:
            # soft — still ok if text refuses
            notes.append(f"executive_source={orch.get('executive_source')}")

    if expect.get("unknown_refuse"):
        if orch.get("short_circuit") == "unknown_entity" or orch.get("entity_hard_stop"):
            notes.append("hard_stop_ok")
        if not re.search(
            r"\b(couldn'?t identify|could not identify|no verified|insufficient evidence)\b",
            low,
        ):
            failures.append("missing_unknown_refuse")
        if re.search(r"\b(view on lt|larsen|own lt)\b", low):
            failures.append("substituted_lookalike_company")

    topics = expect.get("topics_any") or expect.get("topic_required_any") or []
    if topics:
        if not any(t.lower() in low or t.lower() in why_join for t in topics):
            failures.append("missing_topic_substance")

    if expect.get("first_sentence_answers"):
        first = _first_sentence(text)
        if is_planning_scaffold(first) or looks_like_framework_meta_executive(first):
            failures.append("first_sentence_is_scaffold")
        if first.lower().startswith("analyse") or first.lower().startswith("analyze"):
            failures.append("first_sentence_is_plan")

    # Deterministic 0-30 founder-rubric-style score for the release gate (avg < 25 fails).
    critical = {
        "executive_is_planning_scaffold": 15,
        "first_sentence_is_scaffold": 12,
        "first_sentence_is_plan": 12,
        "why_contains_planning_scaffold": 8,
        "missing_unknown_refuse": 20,
        "substituted_lookalike_company": 25,
        "comparison_omits_one_entity": 15,
        "missing_recommendation_refuse": 20,
        "missing_topic_substance": 8,
        "missing_uncertainty_language": 5,
    }
    score = 30
    for f in failures:
        key = f.split(":", 1)[0]
        score -= critical.get(key, 6)
    score = max(0, min(30, score))

    hard_fail_flags = {
        "framework_scaffold_appears": any(
            f.split(":", 1)[0]
            in {"executive_is_planning_scaffold", "first_sentence_is_scaffold", "first_sentence_is_plan"}
            for f in failures
        ),
        "unknown_entity_hallucinates": any(
            f.split(":", 1)[0] in {"missing_unknown_refuse", "substituted_lookalike_company"}
            for f in failures
        ),
        "comparison_omits_entity": "comparison_omits_one_entity" in failures,
        "recommendation_regresses": "missing_recommendation_refuse" in failures,
    }

    return {
        "id": case.get("id"),
        "pass": not failures,
        "failures": failures,
        "notes": notes,
        "summary_excerpt": text[:280],
        "score": score,
        "hard_fail_flags": {k: v for k, v in hard_fail_flags.items() if v},
    }


def evaluate_payload(case: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    orch = payload.get("ask_orchestration") or {}
    if not orch and isinstance(payload.get("degradation"), dict):
        orch = payload["degradation"].get("ask_orchestration") or {}
    return score_golden_answer(
        case,
        summary=_summary_from_payload(payload),
        why=_why_from_payload(payload),
        orch=orch if isinstance(orch, dict) else {},
    )
