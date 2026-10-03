"""Reasoning family engine — gold habits + novelty-aware generalisation.

Priority:
1. Adversarial / unknown / cross-family modes (Phase 3–8)
2. Exact gold pattern (seen) → use gold habit
3. Family match with novel facts → first-principles family compose
4. Else → do not force a template
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.adversarial import compose_adversarial, detect_adversarial_mode
from institutional_reasoning.bias_defense import compose_bias_defense, detect_bias_defense
from institutional_reasoning.families import DUAL_HYPOTHESIS, FAMILIES
from institutional_reasoning.family_classifier import classify_family
from institutional_reasoning.family_composers import compose_family_answer
from institutional_reasoning.gold_patterns import package_pattern_answer
from institutional_reasoning.novelty import score_novelty


def package_reasoning_answer(
    query: str,
    *,
    ticker: str | None = None,
    company: str | None = None,
) -> dict[str, Any]:
    """Package executive answer with family + novelty metadata.

    Soft layer only. Never invents ticker-specific facts beyond the question.
    """
    q = str(query or "").strip()
    family = classify_family(q)
    family_id = family.get("family_id")
    family_conf = float(family.get("confidence") or 0.0)

    # 0a) Bias-defense / cognitive-trap refusals (process integrity).
    bias = detect_bias_defense(q)
    if bias:
        composed = compose_bias_defense(bias, q)
        if composed.get("enabled") and composed.get("executive"):
            novelty = score_novelty(
                gold_exact=False,
                family_id=composed.get("family_id") or "self_critique",
                family_confidence=0.93,
                first_principles=True,
                adversarial=True,
                novelty_band_hint=composed.get("novelty_band_hint"),
            )
            return {
                **composed,
                "family_confidence": 0.93,
                "family_signals": list(composed.get("families_used") or []),
                "novelty": novelty,
                "ticker": ticker,
                "company": company,
            }

    # 0a2) Investment-committee / multi-domain case-study habits (soft).
    try:
        from institutional_reasoning.ic_case_study import compose_ic_case, detect_ic_case_mode

        ic_mode = detect_ic_case_mode(q)
        if ic_mode:
            composed = compose_ic_case(ic_mode, q)
            if composed.get("enabled") and composed.get("executive"):
                novelty = score_novelty(
                    gold_exact=False,
                    family_id=composed.get("family_id") or "uncertainty",
                    family_confidence=0.91,
                    first_principles=True,
                    adversarial=True,
                    novelty_band_hint="first_principles_novel",
                )
                return {
                    **composed,
                    "family_confidence": 0.91,
                    "family_signals": list(composed.get("families_used") or []),
                    "novelty": novelty,
                    "ticker": ticker,
                    "company": company,
                }
    except Exception:
        pass

    # 0b) Adversarial / unknown / cross-family reasoning (Phase 3–8).
    adv_mode = detect_adversarial_mode(q)
    if adv_mode:
        adv = compose_adversarial(adv_mode, q)
        if adv.get("enabled") and adv.get("executive"):
            novelty = score_novelty(
                gold_exact=False,
                family_id=adv.get("family_id") or "adversarial",
                family_confidence=0.92,
                first_principles=True,
                adversarial=True,
                novelty_band_hint=adv.get("novelty_band_hint"),
            )
            return {
                **adv,
                "family_confidence": 0.92,
                "family_signals": list(adv_mode.get("families") or []),
                "novelty": novelty,
                "ticker": ticker,
                "company": company,
            }

    # Hard dual-hypothesis benchmarks must not be stolen by narrower gold templates.
    if family_id == DUAL_HYPOTHESIS and family_conf >= 0.85:
        composed = compose_family_answer(family_id, q)
        if composed and composed.get("executive"):
            novelty = score_novelty(
                gold_exact=False,
                family_id=family_id,
                family_confidence=family_conf,
                first_principles=True,
            )
            return {
                "enabled": True,
                "owns_executive": True,
                "answer_policy": "dual_hypothesis_first_principles",
                "source": "reasoning_family",
                "pattern_id": None,
                "family_id": family_id,
                "family_label": composed.get("family_label")
                or (FAMILIES.get(family_id) or {}).get("label"),
                "family_habit": composed.get("family_habit")
                or (FAMILIES.get(family_id) or {}).get("habit"),
                "family_confidence": family_conf,
                "family_signals": family.get("signals") or [],
                "variant": composed.get("variant"),
                "novelty": novelty,
                "direct_answer": composed.get("direct_answer"),
                "executive": composed["executive"],
                "answer": composed["executive"],
                "structured": composed,
                "reasoning_habit": composed.get("reasoning_habit"),
                "decides_winner": False,
                "ticker": ticker,
                "company": company,
            }

    gold = package_pattern_answer(q, ticker=ticker, company=company)

    # 1) Exact gold pattern — still attach family/novelty diagnostics.
    if gold.get("enabled") and gold.get("executive"):
        level = str(gold.get("level") or "")
        level_to_family = {
            "contradiction": "contradiction",
            "evidence": "evidence",
            "causality": "causality",
            "accounting": "accounting",
            "institutional": "comparison",
            "false_certainty": "uncertainty",
            "devils_advocate": "self_critique",
        }
        mapped = level_to_family.get(level) or family_id
        novelty = score_novelty(
            gold_exact=True,
            family_id=mapped,
            family_confidence=max(family_conf, 0.9),
            first_principles=False,
        )
        return {
            "enabled": True,
            "owns_executive": True,
            "answer_policy": "gold_reasoning_pattern",
            "source": "gold_pattern",
            "pattern_id": gold.get("pattern_id"),
            "level": gold.get("level"),
            "family_id": mapped,
            "family_label": (FAMILIES.get(mapped) or {}).get("label"),
            "family_confidence": max(family_conf, 0.9),
            "novelty": novelty,
            "direct_answer": gold.get("direct_answer"),
            "executive": gold["executive"],
            "answer": gold["executive"],
            "gold_pattern": gold,
            "reasoning_habit": gold.get("reasoning_habit"),
            "habit_id": gold.get("pattern_id"),
            "ticker": ticker,
            "company": company,
        }

    # 2) Family / dual-hypothesis first principles for novel facts.
    if family_id and family_conf >= 0.55:
        composed = compose_family_answer(family_id, q)
        if composed and composed.get("executive"):
            first_principles = True
            novelty = score_novelty(
                gold_exact=False,
                family_id=family_id,
                family_confidence=family_conf,
                first_principles=first_principles,
            )
            policy = (
                "dual_hypothesis_first_principles"
                if family_id == DUAL_HYPOTHESIS
                else "reasoning_family_first_principles"
            )
            return {
                "enabled": True,
                "owns_executive": True,
                "answer_policy": policy,
                "source": "reasoning_family",
                "pattern_id": None,
                "family_id": family_id,
                "family_label": composed.get("family_label")
                or (FAMILIES.get(family_id) or {}).get("label"),
                "family_habit": composed.get("family_habit")
                or (FAMILIES.get(family_id) or {}).get("habit"),
                "family_confidence": family_conf,
                "family_signals": family.get("signals") or [],
                "variant": composed.get("variant"),
                "novelty": novelty,
                "direct_answer": composed.get("direct_answer"),
                "executive": composed["executive"],
                "answer": composed["executive"],
                "structured": composed,
                "reasoning_habit": composed.get("reasoning_habit"),
                "decides_winner": composed.get("decides_winner"),
                "ticker": ticker,
                "company": company,
            }

    # 3) No forced template.
    novelty = score_novelty(
        gold_exact=False,
        family_id=family_id,
        family_confidence=family_conf,
        first_principles=False,
    )
    return {
        "enabled": False,
        "owns_executive": False,
        "bypassed": True,
        "reason": "no_confident_family_or_gold_pattern",
        "family_id": family_id,
        "family_confidence": family_conf,
        "family_signals": family.get("signals") or [],
        "novelty": novelty,
        "answer_policy": "do_not_force_template",
        "ticker": ticker,
        "company": company,
    }


__all__ = ["package_reasoning_answer"]
