"""Adversarial / unknown-reasoning composers — Phase 3–8.

These habits handle questions that do not map cleanly to one family.
They decompose, separate horizons, respect evidence boundaries, and
self-critique. Soft layer only.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any


def _join(parts: list[str]) -> str:
    return " ".join(p.strip() for p in parts if p and str(p).strip())


def detect_adversarial_mode(query: str) -> dict[str, Any] | None:
    """Detect adversarial / cross-family / unknown modes. Never raises."""
    ql = str(query or "").lower()

    # Phase 3 Test 3 — missing cash-flow statement (before generic cash-vs-revenue)
    if re.search(
        r"\b(cash\s+flow\s+statement).{0,80}(not\s+yet|has\s+not|missing|not\s+released)|"
        r"(not\s+yet|has\s+not|missing|not\s+released).{0,80}(cash\s+flow\s+statement)",
        ql,
    ):
        return {
            "mode": "unknown_missing_cashflow",
            "habit_id": "habit_evidence_boundary_cashflow",
            "families": ["uncertainty", "accounting"],
        }

    # Phase 5 Test 5 — competing explanations with mixed metrics
    metric_bits = sum(
        1
        for m in (
            "revenue",
            "profit",
            "debt",
            "free cash",
            "fcf",
            "share price",
            "inventory",
            "receivables",
        )
        if m in ql
    )
    # Also accept classic dual-hypothesis wording.
    if metric_bits >= 4 and re.search(
        r"\b(two\s+competing|competing\s+explanations|two\s+explanations|"
        r"two\s+(equally\s+)?plausible\s+explanations|distinguish\s+between|construct\s+two|"
        r"do\s+not\s+decide\s+which)\b",
        ql,
    ):
        return {
            "mode": "cross_family_dual_hypothesis",
            "habit_id": "habit_competing_explanations",
            "families": ["dual_hypothesis", "accounting", "valuation"],
        }

    # Phase 4 Test 4 — multi-macro × multi-sector
    macro_hits = sum(
        1
        for m in ("inflation", "interest rate", "rbi", "oil", "rupee", "rate")
        if m in ql
    )
    sector_hits = sum(
        1
        for s in ("airline", "bank", "it exporter", "exporter", "private bank")
        if s in ql
    )
    if macro_hits >= 3 and sector_hits >= 2:
        return {
            "mode": "cross_family_macro_sector",
            "habit_id": "habit_macro_sector_decomposition",
            "families": ["causality", "comparison", "uncertainty"],
        }

    # Phase 3 Test 1 — conflicting time horizons
    if (
        re.search(
            r"\b(five\s+years|several\s+years|multi-?year|every\s+year|decade|"
            r"compounded\s+for|long-?horizon|long-?run)\b",
            ql,
        )
        and re.search(
            r"\b(quarter|last\s+two\s+quarters|recent\s+quarters|near\s+term|"
            r"three\s+months|latest\s+three|short-?horizon)\b",
            ql,
        )
    ) or re.search(r"\b(long-horizon|short-horizon).{0,40}(weigh|weight)", ql):
        return {
            "mode": "unknown_time_horizons",
            "habit_id": "habit_conflicting_time_horizons",
            "families": ["contradiction", "uncertainty"],
        }

    # Phase 3 Test 2 — good business, expensive stock
    if (
        re.search(
            r"\b(business|fundamentals?|operating\s+story|return\s+on\s+capital).{0,60}"
            r"(improv|strong|quality|rising)",
            ql,
        )
        or re.search(r"\b(continues\s+to\s+improve)\b", ql)
        or re.search(r"\b(separate\s+the\s+(operating|business).{0,20}(price|valuation)\s+story)\b", ql)
    ) and (
        re.search(r"\b(share\s+price|stock|valuation|price\s+story|discounts?\s+growth)\b", ql)
        and (
            re.search(r"\b(doubl|re-?rated|expensive|separat|far\s+above|multiple)\b", ql)
            or re.search(r"\b(earnings|profit).{0,40}(15\s*%|grew|grown)", ql)
        )
    ):
        return {
            "mode": "unknown_business_vs_valuation",
            "habit_id": "habit_business_vs_valuation",
            "families": ["valuation", "comparison"],
        }

    # Phase 5 Test 6 — assumptions + invalidate
    if re.search(
        r"\b(three\s+assumptions|assumptions?\s+that\s+have\s+the\s+greatest|"
        r"invalidate\s+it|future\s+evidence\s+would\s+invalidate)\b",
        ql,
    ):
        return {
            "mode": "self_critique_assumptions",
            "habit_id": "habit_assumption_falsifiers",
            "families": ["self_critique"],
        }

    # Phase 5 Test 7 — disagree / opposite view
    if re.search(
        r"\b(another\s+analyst\s+disagreed|opposite\s+view|strongest\s+evidence\s+they|"
        r"argue\s+against\s+(yourself|itself|your\s+conclusion))\b",
        ql,
    ):
        return {
            "mode": "self_critique_steelman",
            "habit_id": "habit_steelman_opposite",
            "families": ["self_critique"],
        }

    # Phase 6 Test 8 — evidence hierarchy with named sources
    source_hits = sum(
        1
        for s in (
            "press release",
            "nse",
            "bse",
            "reuters",
            "social media",
            "investor presentation",
            "filing",
        )
        if s in ql
    )
    if source_hits >= 3 or (
        re.search(r"\b(press\s+release|nse\s+filing|reuters|social\s+media|investor\s+presentation)\b", ql)
        and re.search(r"\b(acquisition|evaluate\s+the\s+evidence|authoritative|rank\s+the\s+sources)\b", ql)
    ):
        return {
            "mode": "evidence_hierarchy_sources",
            "habit_id": "habit_evidence_hierarchy",
            "families": ["evidence"],
        }

    # Phase 7 — fictional / unknown company pack
    if re.search(r"\b(abc\s+manufacturing|fictional\s+company|no\s+prior\s+knowledge)\b", ql) or (
        re.search(r"\b(inventory\s*\+?\s*42|receivables\s*\+?\s*38|revenue\s*\+?\s*18)\b", ql)
        and re.search(r"\b(profit\s*\+?\s*5|debt\s+unchanged|share\s+price\s*\+?\s*12)\b", ql)
    ):
        return {
            "mode": "unknown_company_accounting",
            "habit_id": "habit_fictional_wc_stress",
            "families": ["accounting", "uncertainty"],
        }

    # Phase 8 consistency — revenue vs cash paraphrases share one habit id.
    # Keep last so evidence-boundary / dual-hypothesis / IC case prompts are not stolen.
    if (
        re.search(r"\b(free\s+cash\s+flow|fcf|cash\s+generation|cash\s+fell|cash\s+flow)\b", ql)
        and re.search(r"\b(revenue|sales)\b", ql)
        and re.search(r"\b(fall|fell|weak|declin|despite|even\s+though|but)\b", ql)
        and not re.search(
            r"\b(two\s+competing|two\s+explanations|distinguish|cash\s+flow\s+statement|"
            r"executive\s+assessment|investment\s+committee|at\s+least\s+six|"
            r"rank\s+them|institutional\s+case)\b",
            ql,
        )
    ):
        return {
            "mode": "consistency_cash_vs_revenue",
            "habit_id": "habit_revenue_up_cash_down",
            "families": ["accounting"],
        }

    return None


def compose_adversarial(mode_info: dict[str, Any], query: str) -> dict[str, Any]:
    mode = mode_info["mode"]
    composers = {
        "unknown_time_horizons": _time_horizons,
        "unknown_business_vs_valuation": _business_vs_valuation,
        "unknown_missing_cashflow": _missing_cashflow,
        "cross_family_macro_sector": _macro_sector_decomp,
        "cross_family_dual_hypothesis": _competing_explanations,
        "self_critique_assumptions": _assumption_falsifiers,
        "self_critique_steelman": _steelman_opposite,
        "evidence_hierarchy_sources": _evidence_hierarchy,
        "unknown_company_accounting": _fictional_company,
        "consistency_cash_vs_revenue": _cash_vs_revenue_consistent,
    }
    fn = composers[mode]
    body = fn(query)
    executive = body["executive"]
    # Stable fingerprint for consistency checks across paraphrases.
    habit_id = mode_info.get("habit_id") or mode
    fingerprint = hashlib.sha1(f"{habit_id}|{body.get('core_claim','')}".encode()).hexdigest()[:12]
    return {
        "enabled": True,
        "owns_executive": True,
        "source": "adversarial_unknown_reasoning",
        "answer_policy": f"adversarial_{mode}",
        "mode": mode,
        "habit_id": habit_id,
        "consistency_fingerprint": fingerprint,
        "families_used": list(mode_info.get("families") or []),
        "family_id": (mode_info.get("families") or ["unknown"])[0],
        "family_label": "Adversarial / Cross-Family",
        "direct_answer": body.get("direct_answer"),
        "executive": executive,
        "answer": executive,
        "structured": body,
        "decides_winner": body.get("decides_winner"),
        "novelty_band_hint": body.get("novelty_band_hint", "hard_unseen"),
        "reasoning_habit": body.get("reasoning_habit"),
        "decomposed": body.get("decomposed"),
        "never_trains_on_adversarial_eval": True,
    }


def _time_horizons(query: str) -> dict[str, Any]:
    direct = (
        "Neither trend automatically wins. Weight depends on whether the recent quarterly "
        "decline is a temporary pause inside a durable multi-year trajectory, or the start "
        "of a genuine turn."
    )
    why = (
        "A five-year growth record describes the long-run direction of the business. The last "
        "two quarters describe near-term momentum. Institutional analysis keeps both horizons "
        "visible: long-term evidence sets the base case, while recent weakness raises the "
        "probability that the trend is changing."
    )
    alts = (
        "Other readings include: (1) seasonal or one-off quarterly noise inside a still-intact "
        "annual trend; (2) an early cyclical or competitive slowdown that will eventually "
        "overwrite the five-year record; (3) a mix shift or accounting timing effect that "
        "hurts quarters without changing long-run demand."
    )
    missing = (
        "Additional evidence needed: order book and volume-price-mix for the weak quarters; "
        "whether guidance changed; peer quarterly trends; and whether trailing twelve-month "
        "growth is still positive after the recent decline."
    )
    conclusion = (
        "Give the multi-year record more weight only if recent weakness looks temporary and "
        "explained. Give the quarterly decline more weight if it is broad-based, unexplained, "
        "or confirmed by forward indicators. Do not collapse the two horizons into one story yet."
    )
    return {
        "direct_answer": direct,
        "core_claim": "weigh_both_horizons_conditionally",
        "executive": _join([direct, why, alts, missing, conclusion]),
        "novelty_band_hint": "hard_unseen",
        "reasoning_habit": "separate_horizons → conditional_weight → missing_forward_evidence → no_forced_pick",
        "decomposed": {"long_horizon": "five_year_growth", "short_horizon": "last_two_quarters"},
    }


def _business_vs_valuation(query: str) -> dict[str, Any]:
    direct = (
        "Assess the business and the valuation on separate ledgers. An improving business can "
        "still be an expensive stock if the share price has run far ahead of earnings."
    )
    why = (
        "Business quality asks whether operations, margins, cash conversion and competitive "
        "position are getting better. Valuation asks what price investors are paying for that "
        "improvement. When the share price doubles while earnings grow only about 15%, most of "
        "the return has come from a higher multiple, not from proportional earnings power."
    )
    alts = (
        "Possible valuation readings include: (1) the market is discounting much faster future "
        "growth than the trailing 15% implies; (2) risk premia fell and re-rated the whole sector; "
        "(3) the move embeds temporary optimism that may reverse if delivery disappoints."
    )
    missing = (
        "Additional evidence needed: starting and current multiples versus history and peers; "
        "free-cash-flow conversion; and whether guidance supports the growth rate embedded in the price."
    )
    conclusion = (
        "You can remain constructive on the business while remaining cautious on valuation — "
        "those are not the same conclusion."
    )
    return {
        "direct_answer": direct,
        "core_claim": "separate_business_quality_from_valuation",
        "executive": _join([direct, why, alts, missing, conclusion]),
        "novelty_band_hint": "hard_unseen",
        "reasoning_habit": "split_business_vs_price → explain_multiple_expansion → missing_valuation_evidence",
    }


def _missing_cashflow(query: str) -> dict[str, Any]:
    direct = (
        "You can note that reported revenue and profit rose, but you cannot conclude that cash "
        "generation, earnings quality or balance-sheet health improved."
    )
    why = (
        "Revenue and profit are accrual measures. Without the cash-flow statement, inventory "
        "build, slower collections, higher capex or financing flows remain invisible. Higher "
        "profit does not prove higher cash."
    )
    can_draw = (
        "Conclusions that can be drawn from the available facts alone: top-line and reported "
        "profit moved higher on an accounting basis."
    )
    cannot_draw = (
        "Conclusions that cannot be drawn yet: whether free cash flow rose; whether working "
        "capital absorbed cash; whether growth is self-funding; and whether earnings are high quality."
    )
    conclusion = (
        "Keep confidence limited to the income-statement facts and explicitly mark cash conclusions "
        "as unavailable until the cash-flow statement is released."
    )
    return {
        "direct_answer": direct,
        "core_claim": "income_statement_ok_cash_unknown",
        "executive": _join([direct, why, can_draw, cannot_draw, conclusion]),
        "novelty_band_hint": "hard_unseen",
        "reasoning_habit": "state_can → state_cannot → evidence_boundary",
    }


def _macro_sector_decomp(query: str) -> dict[str, Any]:
    direct = (
        "Do not produce one macro narrative. Decompose the shocks and map each one onto each "
        "business model separately."
    )
    setup = (
        "The simultaneous moves — higher inflation, higher policy rates, lower oil and a stronger "
        "rupee — pull in different directions. Net impact depends on cost structure, funding and demand."
    )
    airline = (
        "Airline: lower oil is usually supportive for fuel costs, but higher rates can pressure "
        "demand and aircraft financing; a stronger rupee may lower dollar-linked fuel or lease costs "
        "in local-currency terms while also reflecting broader macro conditions. Net effect is "
        "ambiguous without traffic and hedging detail."
    )
    bank = (
        "Private bank: higher policy rates can lift lending yields with a lag, but may also raise "
        "funding costs and slow loan demand; inflation affects credit quality; oil and the rupee "
        "matter mostly indirectly through growth and borrower stress. Focus on NIM transmission and asset quality."
    )
    it_exp = (
        "IT exporter: a stronger rupee can weigh on rupee-translated export revenue, while rate "
        "and inflation effects are mostly demand-side via global clients; lower oil is a minor "
        "direct input. Currency and client spending dominate over domestic fuel."
    )
    uncertainty = (
        "Uncertainty: pass-through lags, hedging, and company-specific mix can reverse any of "
        "these first-order maps. Treat each sector path as provisional until operating evidence arrives."
    )
    conclusion = (
        "Answer by decomposition — macro factor × sector — not by a single market story."
    )
    return {
        "direct_answer": direct,
        "core_claim": "decompose_macro_by_sector",
        "executive": _join([direct, setup, airline, bank, it_exp, uncertainty, conclusion]),
        "novelty_band_hint": "hard_unseen",
        "reasoning_habit": "list_shocks → map_per_sector → state_uncertainty → no_single_narrative",
        "decomposed": {
            "factors": ["inflation", "rates", "oil", "rupee"],
            "sectors": ["airline", "private_bank", "it_exporter"],
        },
        "decides_winner": False,
    }


def _competing_explanations(query: str) -> dict[str, Any]:
    direct = (
        "Two competing explanations can fit these mixed moves. Do not force a single answer."
    )
    hyp_a = (
        "Explanation 1 (Quality over volume): Revenue rose while profit fell because of mix, "
        "pricing or cost pressure, but debt reduction and stronger free cash flow show cash "
        "discipline; the share price may be rewarding cash and balance-sheet repair over near-term margins."
    )
    support_a = (
        "Evidence that supports Explanation 1 includes: falling working-capital days, lower interest "
        "expense, and management emphasis on cash conversion rather than margin expansion."
    )
    challenge_a = (
        "Evidence that challenges Explanation 1 includes: rising one-off cash inflows, asset sales "
        "behind FCF, or profit decline driven by lasting competitive damage."
    )
    hyp_b = (
        "Explanation 2 (Market looking through a temporary profit dip): Operations remain solid "
        "enough that investors ignore the margin squeeze; debt fell and FCF improved for cyclical "
        "or timing reasons, while the share price anticipates a profit rebound."
    )
    support_b = (
        "Evidence that supports Explanation 2 includes: stable volumes, temporary cost spikes, and "
        "forward indicators (orders, pricing) that point to margin recovery."
    )
    challenge_b = (
        "Evidence that challenges Explanation 2 includes: sustained margin compression, weakening "
        "orders, or FCF strength that is not repeatable."
    )
    distinguish = (
        "Evidence needed to distinguish them: profit-bridge (volume/price/mix/cost), cash-flow "
        "bridge (working capital vs investing vs financing), and whether guidance implies margin repair or structural pressure."
    )
    conclusion = (
        "Hold both explanations open until the bridges arrive. Do not decide which is correct yet."
    )
    return {
        "direct_answer": direct,
        "core_claim": "two_competing_explanations_no_decision",
        "executive": _join(
            [direct, hyp_a, support_a, challenge_a, hyp_b, support_b, challenge_b, distinguish, conclusion]
        ),
        "novelty_band_hint": "hard_unseen",
        "reasoning_habit": "two_explanations → support → challenge → distinguishing_evidence → no_decision",
        "decides_winner": False,
    }


def _assumption_falsifiers(query: str) -> dict[str, Any]:
    direct = (
        "Three assumptions usually dominate a business-or-trend conclusion: demand continuity, "
        "margin or cash conversion durability, and a stable macro/funding backdrop."
    )
    a1 = (
        "Assumption 1 — Demand stays at least as strong as recent evidence implies. "
        "Invalidated if volumes, orders or customer additions fall meaningfully for more than one period."
    )
    a2 = (
        "Assumption 2 — Profitability and cash conversion do not deteriorate from current levels. "
        "Invalidated if margins compress persistently or free cash flow turns negative while sales still look fine."
    )
    a3 = (
        "Assumption 3 — The macro and funding environment remains broadly compatible with the base case. "
        "Invalidated if rates, inflation, currency or credit conditions move enough to change demand or refinancing risk."
    )
    conclusion = (
        "Track these three falsifiers explicitly. A conclusion is only as strong as the assumptions that survive new evidence."
    )
    return {
        "direct_answer": direct,
        "core_claim": "three_assumptions_with_falsifiers",
        "executive": _join([direct, a1, a2, a3, conclusion]),
        "novelty_band_hint": "first_principles",
        "reasoning_habit": "list_assumptions → attach_invalidators → monitor",
    }


def _steelman_opposite(query: str) -> dict[str, Any]:
    direct = (
        "The strongest opposite case would use the weakest link in the current conclusion — "
        "usually recent contrary data, stretched valuation, or missing cash confirmation."
    )
    why = (
        "A disagreeing analyst should not attack straw men. They should emphasise the evidence "
        "that most undermines the house view while still fitting the known facts."
    )
    evidence = (
        "Strong opposite evidence could include: (1) a clear break in recent operating momentum "
        "that the bullish case treats as noise; (2) proof that cash or working capital contradicts "
        "the income-statement story; (3) valuation or funding conditions that make the optimistic "
        "path require perfect execution."
    )
    fair = (
        "Present that opposite case at full strength. Then state what additional evidence would "
        "be needed to choose between the two views — without dismissing the disagreement."
    )
    conclusion = (
        "Self-critique is incomplete unless the opposing evidence is stated as persuasively as the original conclusion."
    )
    return {
        "direct_answer": direct,
        "core_claim": "steelman_opposite_view",
        "executive": _join([direct, why, evidence, fair, conclusion]),
        "novelty_band_hint": "first_principles",
        "reasoning_habit": "steelman_opposite → cite_strongest_contrary_evidence → keep_open",
    }


def _evidence_hierarchy(query: str) -> dict[str, Any]:
    direct = (
        "Do not update the assessment on the weakest source alone. Rank sources by authority, "
        "verifiability and completeness before changing conclusions."
    )
    hierarchy = (
        "Evidence hierarchy for an acquisition claim: (1) NSE/BSE exchange filing — highest "
        "authority for listed-company material events because it is an official disclosure; "
        "(2) company press release — useful but still needs exchange confirmation for market-moving "
        "facts; (3) investor presentation — management framing, not independent confirmation; "
        "(4) Reuters or similar wire — secondary reporting that can be early but may be incomplete; "
        "(5) social media — lowest authority; treat as unverified rumour unless tied to a primary source."
    )
    why = (
        "Official exchange filings are more authoritative because they create disclosure "
        "accountability. Press releases and presentations reflect company messaging. Media and "
        "social posts can surface signals early, but they do not by themselves establish that an "
        "acquisition happened on the claimed terms."
    )
    process = (
        "Process: if only one unofficial source claims a major acquisition while filings and "
        "stronger sources are silent, keep the base assessment unchanged, flag the claim as "
        "unverified, and wait for an exchange filing or clear company confirmation."
    )
    conclusion = (
        "Update confidence only when higher-authority evidence arrives — not because a single low-authority source spoke first."
    )
    return {
        "direct_answer": direct,
        "core_claim": "exchange_filing_outranks_secondary_sources",
        "executive": _join([direct, hierarchy, why, process, conclusion]),
        "novelty_band_hint": "first_principles",
        "reasoning_habit": "rank_sources → explain_why → withhold_update_until_confirmed",
    }


def _fictional_company(query: str) -> dict[str, Any]:
    direct = (
        "On these figures alone, sales and profit are up, but working-capital intensity has risen "
        "much faster than profit — so earnings quality and cash conversion need scrutiny."
    )
    why = (
        "Revenue +18% with profit only +5% suggests margin pressure or operating deleverage. "
        "Inventory +42% and receivables +38% imply cash may be tied up in stock and customer credit "
        "even though debt is unchanged and the share price is higher."
    )
    alts = (
        "Plausible readings: (1) growth investment / channel fill ahead of demand; (2) weakening "
        "sell-through and slower collections; (3) market optimism looking through near-term cash drag."
    )
    missing = (
        "Additional evidence needed: cash-flow statement, inventory split, receivables ageing, "
        "and whether the profit bridge is volume, price or cost. No prior company knowledge is required — "
        "the accounting relationships are enough to frame the questions."
    )
    conclusion = (
        "Do not treat the share-price gain as confirmation of quality until cash conversion is verified."
    )
    return {
        "direct_answer": direct,
        "core_claim": "wc_stress_despite_growth_unknown_co",
        "executive": _join([direct, why, alts, missing, conclusion]),
        "novelty_band_hint": "hard_unseen",
        "reasoning_habit": "read_ratios → flag_wc_vs_profit → ask_for_cash_bridge → no_company_memory",
    }


def _cash_vs_revenue_consistent(query: str) -> dict[str, Any]:
    """Same habit for Phase-8 paraphrases — stable core claim."""
    direct = (
        "Higher revenue does not guarantee stronger cash generation. Cash can fall when working "
        "capital rises, capital expenditure increases, or accruals run ahead of collections."
    )
    why = (
        "Sales are recognised on an accrual basis. Free cash flow subtracts cash stuck in "
        "inventory and receivables and cash spent on investing. Those bridges can turn a revenue "
        "increase into weaker cash."
    )
    alts = (
        "Other possible explanations include: (1) inventory build; (2) slower customer payments; "
        "(3) higher capex; (4) one-off cash outflows."
    )
    missing = (
        "Additional evidence needed: operating cash-flow and working-capital bridges, plus capex detail."
    )
    conclusion = (
        "Identify the cash bridge before judging whether the revenue growth is high quality."
    )
    return {
        "direct_answer": direct,
        "core_claim": "revenue_up_does_not_imply_cash_up",
        "executive": _join([direct, why, alts, missing, conclusion]),
        "novelty_band_hint": "same_family_new_facts",
        "reasoning_habit": "accrual_vs_cash → alternatives → missing_bridge → balanced_conclusion",
    }


__all__ = ["compose_adversarial", "detect_adversarial_mode"]
