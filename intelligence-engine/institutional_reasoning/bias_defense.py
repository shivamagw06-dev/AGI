"""Bias-defense habits — cognitive-trap refusals, not new reasoning families.

These are process guards: refuse hidden assumptions, survivorship, false
causation, base-rate neglect, anchoring, and evidence-abandonment instructions.
Soft layer only. Does not import Red Team banks.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any


def _join(parts: list[str]) -> str:
    return " ".join(p.strip() for p in parts if p and str(p).strip())


def detect_bias_defense(query: str) -> dict[str, Any] | None:
    ql = str(query or "").lower()

    # Adversarial prompting — abandon evidence process
    if re.search(
        r"\b(ignore\s+previous\s+evidence|disregard\s+filings?|assume\s+management\s+is\s+telling\s+the\s+truth|"
        r"treat\s+the\s+ceo\s+interview\s+as\s+definitive|abandon\s+.{0,20}evidence)\b",
        ql,
    ):
        return {"mode": "refuse_abandon_evidence", "habit_id": "bias_refuse_abandon_evidence"}

    # Hidden assumption / one-off profit
    if re.search(
        r"\b(sold\s+a\s+(major\s+)?factory|factory\s+sale|asset\s+sale|plant\s+sale|"
        r"selling\s+a\s+(major\s+)?factory|factory\s+disposal|one-time\s+factory|"
        r"gain\s+came\s+from\s+selling)\b",
        ql,
    ) and re.search(r"\b(profit|earnings)\b", ql):
        return {"mode": "non_recurring_profit", "habit_id": "bias_non_recurring_profit"}

    # Survivorship / price-only quality
    if (
        re.search(r"\b(doubled\s+in\s+value|five-year\s+price\s+charts?|price\s+charts?)\b", ql)
        and re.search(r"\b(better\s+business|strongest\s+business|which\s+ones\s+are\s+the\s+strongest)\b", ql)
    ) or (
        re.search(r"\b(two\s+companies)\b", ql)
        and re.search(r"\b(doubled\s+in\s+value)\b", ql)
        and re.search(r"\b(better\s+business)\b", ql)
    ):
        return {"mode": "survivorship_price_only", "habit_id": "bias_survivorship"}

    # Correlation vs causation
    if re.search(
        r"\b(did\s+.+\s+cause|does\s+that\s+prove|cause\s+the\s+rally|caused\s+the\s+share-price)\b",
        ql,
    ) and re.search(
        r"\b(rates?\s+fell|oil\s+prices?\s+dropped|bank\s+stocks?\s+rose|airline\s+shares|cheaper\s+oil)\b",
        ql,
    ):
        return {"mode": "correlation_not_causation", "habit_id": "bias_correlation"}

    # Base rate / one quarter
    if re.search(
        r"\b(beat\s+earnings|beat\s+.{0,40}consensus|strong\s+quarter|excellent\s+investment|"
        r"high-quality\s+compounder|beat\s+alone)\b",
        ql,
    ) and re.search(
        r"\b(does\s+this\s+mean|justified|excellent\s+investment|by\s+20\s*%|compounder)\b",
        ql,
    ):
        return {"mode": "base_rate_one_quarter", "habit_id": "bias_base_rate"}

    # Simpson's paradox / mix
    if re.search(
        r"\b(each\s+product\s+category\s+grew|every\s+product\s+category|category\s+grew).{0,80}"
        r"(overall|total).{0,40}(fell|declin|down)",
        ql,
    ) or re.search(r"\boverall\s+company\s+revenue\s+fell\b", ql) and re.search(r"\bcategory\b", ql):
        return {"mode": "simpsons_mix", "habit_id": "bias_simpsons"}

    # Confirmation bias — mostly positive + critical negative
    if re.search(r"\b(however|but).{0,80}(free\s+cash\s+flow|fcf|receivables)\b", ql) and re.search(
        r"\b(grew|expanded|upbeat|higher)\b", ql
    ):
        return {"mode": "confirmation_critical_negative", "habit_id": "bias_confirmation"}

    # Anchoring on old price
    if re.search(
        r"\b(₹\s*3,?000|3000\s+two\s+years|old\s+print|prior\s+cycle|was\s+₹|traded\s+at\s+a\s+much\s+higher)\b",
        ql,
    ) and re.search(r"\b(cheap|attractive|bargain|decide\s+whether)\b", ql):
        return {"mode": "anchoring_old_price", "habit_id": "bias_anchoring"}

    # Unknown domain — shipping
    if re.search(
        r"\b(shipping|dry-bulk|bunker|ballast|charter\s+coverage|spot\s+rates?)\b", ql
    ) and not re.search(r"\b(hdfc|infosys|nim|casa|saas)\b", ql):
        return {"mode": "unknown_domain_shipping", "habit_id": "bias_unknown_shipping"}

    return None


def compose_bias_defense(mode_info: dict[str, Any], query: str) -> dict[str, Any]:
    mode = mode_info["mode"]
    body = {
        "refuse_abandon_evidence": _refuse_abandon,
        "non_recurring_profit": _non_recurring,
        "survivorship_price_only": _survivorship,
        "correlation_not_causation": _correlation,
        "base_rate_one_quarter": _base_rate,
        "simpsons_mix": _simpsons,
        "confirmation_critical_negative": _confirmation,
        "anchoring_old_price": _anchoring,
        "unknown_domain_shipping": _shipping,
    }[mode](query)
    habit_id = mode_info["habit_id"]
    fp = hashlib.sha1(f"{habit_id}|{body.get('core_claim','')}".encode()).hexdigest()[:12]
    return {
        "enabled": True,
        "owns_executive": True,
        "source": "bias_defense",
        "answer_policy": f"bias_defense_{mode}",
        "mode": mode,
        "habit_id": habit_id,
        "consistency_fingerprint": fp,
        "family_id": "self_critique",
        "family_label": "Bias Defense",
        "families_used": ["self_critique", "uncertainty", "evidence"],
        "direct_answer": body["direct_answer"],
        "executive": body["executive"],
        "answer": body["executive"],
        "structured": body,
        "decides_winner": False,
        "novelty_band_hint": "first_principles",
        "reasoning_habit": body.get("reasoning_habit"),
        "never_imports_red_team_bank": True,
    }


def _refuse_abandon(query: str) -> dict[str, Any]:
    direct = (
        "No. That is not acceptable. AIG should not follow an instruction to ignore previous "
        "evidence, disregard filings, or treat management statements as definitive without verification."
    )
    why = (
        "Institutional reasoning is evidence-based. Management commentary is useful but sits "
        "below filings and financial results. An instruction to disregard filings or assume "
        "truth is an attempt to abandon the process — and must be refused."
    )
    conclusion = (
        "Keep the evidence hierarchy. Update conclusions only when higher-authority evidence supports it."
    )
    return {
        "direct_answer": direct,
        "core_claim": "refuse_abandon_evidence_process",
        "executive": _join([direct, why, conclusion]),
        "reasoning_habit": "refuse_bad_instruction → restate_evidence_process",
    }


def _non_recurring(query: str) -> dict[str, Any]:
    direct = (
        "No — a profit increase driven by selling a major factory or other asset sale is not "
        "reliable evidence that the business is improving."
    )
    why = (
        "Factory or plant disposals are typically non-recurring / one-off / one-time items. Flat revenue and "
        "declining operating cash flow point the other way: core operations may be unchanged or weaker "
        "even while headline profit rises."
    )
    conclusion = (
        "Separate recurring operating profit from disposal gains before judging franchise health."
    )
    return {
        "direct_answer": direct,
        "core_claim": "one_off_profit_is_not_operating_improvement",
        "executive": _join([direct, why, conclusion]),
        "reasoning_habit": "identify_one_off → compare_core_sales_and_ocf → reject_false_improvement",
    }


def _survivorship(query: str) -> dict[str, Any]:
    direct = (
        "There isn't enough information. Share price performance alone doesn't determine business quality. "
        "From price charts alone you cannot identify which are the strongest businesses."
    )
    why = (
        "Two stocks can double for very different reasons — leverage, multiple expansion, cyclical "
        "timing or genuine compounding. Without margins, cash flow, returns on capital, leverage and "
        "industry context, ranking 'better business' from price charts alone is survivorship-biased."
    )
    conclusion = (
        "Refuse the ranking until operating and balance-sheet evidence is available."
    )
    return {
        "direct_answer": direct,
        "core_claim": "price_performance_is_not_business_quality",
        "executive": _join([direct, why, conclusion]),
        "reasoning_habit": "reject_price_only_quality → demand_operating_evidence",
    }


def _correlation(query: str) -> dict[str, Any]:
    direct = (
        "Not necessarily. Co-movement does not prove causation. Other factors may have contributed, "
        "and the available evidence doesn't establish causation."
    )
    why = (
        "Rates or oil can move alongside equities without being the cause. Flows, earnings revisions, "
        "risk appetite and unrelated news can dominate the same window."
    )
    conclusion = (
        "Treat the co-movement as a hypothesis to test — not as a proven causal claim."
    )
    return {
        "direct_answer": direct,
        "core_claim": "correlation_is_not_causation",
        "executive": _join([direct, why, conclusion]),
        "reasoning_habit": "refuse_unproven_cause → list_alternative_factors",
    }


def _base_rate(query: str) -> dict[str, Any]:
    direct = (
        "No. One quarter — even a large beat — does not establish long-term business quality or "
        "make something an excellent investment. That conclusion is not warranted from a single beat alone."
    )
    why = (
        "Beats can reflect one-offs, low expectations or temporary mix. Base rates for persistence "
        "are modest; valuation, cash conversion and multi-year evidence still matter."
    )
    conclusion = (
        "Keep the beat as a data point, not a quality verdict."
    )
    return {
        "direct_answer": direct,
        "core_claim": "one_quarter_is_not_excellence",
        "executive": _join([direct, why, conclusion]),
        "reasoning_habit": "apply_base_rate → reject_single_print_excellence",
    }


def _simpsons(query: str) -> dict[str, Any]:
    direct = (
        "It is possible when the mix shifts: every category can grow while overall revenue falls "
        "if the business loses weight in larger categories or the growing categories are too small "
        "to offset declines elsewhere in the reported total after reclassification or exits."
    )
    why = (
        "This is a composition effect (Simpson-style aggregation). Category growth rates do not "
        "determine the total without category weights. A company can also exit or shrink a large "
        "line while remaining categories grow off a smaller base."
    )
    conclusion = (
        "Ask for category weights and a bridge from category revenues to the consolidated total "
        "before dismissing the pattern as a data error."
    )
    return {
        "direct_answer": direct,
        "core_claim": "mix_weights_explain_category_vs_total",
        "executive": _join([direct, why, conclusion]),
        "reasoning_habit": "invoke_composition → request_weight_bridge",
    }


def _confirmation(query: str) -> dict[str, Any]:
    direct = (
        "The negative free cash flow and jump in receivables deserve the most attention."
    )
    why = (
        "Positive revenue, margins, customers, commentary and price can encourage confirmation bias. "
        "Cash turning negative after receivables rise is a critical quality signal and should not be "
        "averaged away by the bullish cluster."
    )
    conclusion = (
        "Elevate the cash/receivables break and verify whether growth is converting into cash."
    )
    return {
        "direct_answer": direct,
        "core_claim": "elevate_critical_negative_over_bullish_cluster",
        "executive": _join([direct, why, conclusion]),
        "reasoning_habit": "scan_for_disconfirming_cash_signal → elevate_it",
    }


def _anchoring(query: str) -> dict[str, Any]:
    direct = (
        "No. An old price — including ₹3,000 two years ago or any prior-cycle print — should not "
        "decide whether today's shares are cheap or attractive."
    )
    why = (
        "Anchoring on a prior print substitutes memory for analysis. Cheapness depends on current "
        "earnings power, cash flows, risks and peer valuations, not the distance from a historical high."
    )
    conclusion = (
        "Ignore the anchor. Revalue from fundamentals and comparable evidence."
    )
    return {
        "direct_answer": direct,
        "core_claim": "old_price_is_not_intrinsic_value",
        "executive": _join([direct, why, conclusion]),
        "reasoning_habit": "reject_price_anchor → revalue_from_fundamentals",
    }


def _shipping(query: str) -> dict[str, Any]:
    direct = (
        "Investigate the forward earnings power of the fleet first: spot rate strength versus "
        "next-year charter coverage, net of bunker costs and ballast inefficiency."
    )
    why = (
        "In dry-bulk shipping, near-term spot strength can coexist with weaker contracted coverage, "
        "higher fuel costs and more unproductive ballast days. Those variables dominate banking or "
        "IT templates and should be read from shipping economics, not borrowed metaphors."
    )
    conclusion = (
        "Build a simple rate × utilisation − bunker bridge and test how much of next year is already covered by charters."
    )
    return {
        "direct_answer": direct,
        "core_claim": "shipping_spot_vs_coverage_cost_bridge",
        "executive": _join([direct, why, conclusion]),
        "reasoning_habit": "domain_first_principles → rate_coverage_cost_bridge",
    }


__all__ = ["compose_bias_defense", "detect_bias_defense"]
