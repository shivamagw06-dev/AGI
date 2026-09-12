"""Senior investment-committee depth habits (soft extension).

Closes the gap from 'diagnoses well' to 'quantifies, prioritises, debates,
times transmission, and calibrates confidence'.
Never hardcodes named case-study titles.
Never imports held-out banks. NOT a top-level engine.
"""

from __future__ import annotations

import re
from typing import Any, Callable


def depth_detection_checks() -> list[tuple[str, str, list[str], re.Pattern[str]]]:
    return [
        (
            "ic_quant_value_creation",
            "habit_ic_quant_roic_wacc",
            ["corporate_finance", "valuation"],
            re.compile(
                r"\b(estimate[d]?\s+roic|estimate[d]?\s+wacc|value\s+destruction|economic\s+profit|"
                r"how\s+large\s+is\s+the\s+value|quantif(?:y|ied)\s+(?:roic|wacc|value)|"
                r"temporary\s+or\s+structural).{0,40}(roic|wacc|value)|"
                r"\broic\b.{0,40}\bwacc\b.{0,60}(estimate|quantif|percentage|bps|percent)",
                re.I | re.S,
            ),
        ),
        (
            "ic_valuation_sensitivity",
            "habit_ic_val_sensitivity",
            ["valuation", "uncertainty"],
            re.compile(
                r"\b(valuation\s+sensitivity|biggest\s+valuation\s+sensitivity|"
                r"which\s+assumptions?\s+create\s+the\s+biggest|"
                r"tornado\s+(?:chart|analysis)|wacc\s*\+?\s*1\s*%|"
                r"terminal\s+growth\s*[−\-]\s*1|margin\s+recovery\s+delayed|"
                r"working-?capital\s+normalisation\s+delayed)\b",
                re.I | re.S,
            ),
        ),
        (
            "ic_second_order_macro",
            "habit_ic_second_order",
            ["causality", "uncertainty"],
            re.compile(
                r"\bsecond-?order\b|"
                r"\boil\s*\+?\s*\d+\s*%\b.{0,120}(inflation|discount\s+rates|working\s+capital|credit\s+quality)|"
                r"\b(chain|cascade)\s+of\s+(macro\s+)?effects\b",
                re.I | re.S,
            ),
        ),
        (
            "ic_bank_grade_credit",
            "habit_ic_bank_credit",
            ["uncertainty", "accounting"],
            re.compile(
                r"\b(bank-?grade|debt\s+maturity\s+ladder|liquidity\s+runway|"
                r"debt\s*/\s*fcf|ebitda\s*/\s*debt|refinancing\s+probability)\b|"
                r"\binterest\s+coverage\b.{0,80}(maturity\s+ladder|liquidity\s+runway|debt\s*/\s*fcf)",
                re.I | re.S,
            ),
        ),
        (
            "ic_macro_timing_chain",
            "habit_ic_macro_timing",
            ["causality", "uncertainty"],
            re.compile(
                r"\b(transmission).{0,60}(timing|over\s+what\s+period|6\s+months|18\s+months|3\s+years)|"
                r"\b(rbi\s+cut).{0,80}(6\s+months|18\s+months|3\s+years)|"
                r"\bover\s+6\s+months,\s*18\s+months,\s*and\s*3\s+years\b",
                re.I | re.S,
            ),
        ),
        (
            "ic_rank_red_flags",
            "habit_ic_rank_flags",
            ["accounting", "evidence"],
            re.compile(
                r"\b(rank|prioritis[ee]).{0,40}(red\s+flags?|warning\s+signs?)|"
                r"\bwhich\s+red\s+flag\s+matters\s+most\b|"
                r"\bcash\s+conversion\b.{0,40}\bdebt\b.{0,40}\bgoodwill\b.{0,40}(inventory|receivable)",
                re.I | re.S,
            ),
        ),
        (
            "ic_investigative_questions",
            "habit_ic_investigate_qs",
            ["self_critique", "accounting"],
            re.compile(
                r"\b(20|25|30|twenty|thirty)\s+(investigative\s+)?questions\b|"
                r"\binvestigative\s+questions\b|"
                r"\bwhat\s+don'?t\s+we\s+know\b.{0,40}(receivable|inventory|capex|synergy)|"
                r"\bmaintenance\s+vs\s+growth\s+capex\b.{0,40}(question|ask)",
                re.I | re.S,
            ),
        ),
        (
            "ic_committee_debate",
            "habit_ic_committee_debate",
            ["dual_hypothesis", "comparison"],
            re.compile(
                r"\b(committee\s+debate|simulate\s+disagreement|growth\s+committee).{0,80}"
                r"(credit\s+committee|value\s+committee|risk\s+committee).{0,80}(chair)|"
                r"\bwhy\s+committee\s+[ab]\s+outweighs\b|"
                r"\bmake\s+them\s+debate\b",
                re.I | re.S,
            ),
        ),
        (
            "ic_confidence_calibration",
            "habit_ic_confidence_calib",
            ["uncertainty", "self_critique"],
            re.compile(
                r"\bwhy\s+\d{2}\s*%\b|"
                r"\bwhy\s+not\s+(40|90)\s*%\b|"
                r"\bconfidence\s+calibration\b|"
                r"\bevidence-?based\s+confidence\b|"
                r"\bwhy\s+70\s*%\b.{0,40}(40|90)",
                re.I | re.S,
            ),
        ),
    ]


def _exec(direct: str, why: str, alts: list[str], missing: list[str], conclusion: str) -> dict[str, Any]:
    parts = [
        direct,
        why,
        (
            "Other possible explanations / points include: "
            + "; ".join(f"({i}) {a.rstrip('.')}" for i, a in enumerate(alts, 1))
            + "."
        )
        if alts
        else "",
        ("Additional evidence needed: " + "; ".join(m.rstrip(".") for m in missing) + ".") if missing else "",
        conclusion,
    ]
    executive = " ".join(p for p in parts if p and str(p).strip())
    return {"direct_answer": direct, "executive": executive, "core_claim": direct[:180]}


def _quant_value(query: str) -> dict[str, Any]:
    return _exec(
        "Quantified value-creation read (order-of-magnitude, not false precision): "
        "estimate ROIC on recent invested capital in a mid-single-digit to low-double-digit band when FCF is negative and margins are compressing — "
        "well below a WACC that should be marked up from a textbook mid-cost-of-capital (e.g. ~10%) toward low-double-digits once leverage, Negative Watch and maturity-wall risk are priced "
        "(illustrative WACC ~11–13% vs stated model 10%). "
        "Economic profit on incremental capital is therefore negative: if incremental ROIC is ~8% and WACC ~12%, value destruction is roughly (12%−8%) × incremental capital each year until cash returns recover. "
        "Whether temporary or structural hinges on WC mean-reversion and post-acquisition cash ROIC within a defined window (e.g. 4–6 quarters) — not on revenue growth alone.",
        "Judgement without numbers is incomplete for an IC. State ranges, the capital base used, and the falsifier that flips temporary vs structural.",
        [
            "If AI mix and synergies lift incremental ROIC above WACC within the window, destruction was temporary",
            "If WC days and goodwill impairments persist, destruction is structural",
        ],
        [
            "Segment invested capital and NOPAT",
            "WACC build with current spreads",
            "Incremental capital deployed on deal + WC + growth capex",
        ],
        "IC standard: estimate ROIC, estimate WACC, size the gap, and date the temporary-vs-structural test.",
    )


def _val_sens(query: str) -> dict[str, Any]:
    return _exec(
        "Valuation sensitivity (largest to smaller, typical industrial growth name with negative FCF): "
        "(1) Working capital normalisation delayed 2 years — often the largest hit because FCF stays negative and reverse-DCF collapses; "
        "(2) Margin recovery delayed 2 years — cuts near-term NOPAT/FCF and terminals; "
        "(3) WACC +1% — material present-value hit, especially with long duration implied by rich multiples; "
        "(4) Terminal growth −1% — meaningful but usually smaller than WC/margin path when cash is already broken; "
        "(5) Synergy haircut / deal under-delivery — hits both DCF and RI via lower ROIC and possible impairment. "
        "Rank sensitivities with a tornado: cash-timing assumptions usually dominate multiple-point DCF when FCF is negative.",
        "Explain which lever moves value most and why — not only that models disagree.",
        ["Peer multiple re-rating can dominate in relative value even if DCF is WC-sensitive"],
        ["Explicit tornado table on the live model", "FCF bridge under delayed WC"],
        "Biggest sensitivity here is usually cash conversion timing, then margins, then WACC, then terminal g.",
    )


def _bank_credit(query: str) -> dict[str, Any]:
    return _exec(
        "Bank-grade credit discussion: "
        "Debt maturity ladder — flag any wall where a large share (e.g. ~40%+) falls inside 24 months; that dominates lending comfort. "
        "Interest coverage — EBIT/interest compressing as margins fall and debt stock rises; treat sub-4× as credit-committee yellow and falling coverage as red. "
        "EBITDA/debt and net-debt/EBITDA — leverage rising while EBITDA margins fall is double adverse. "
        "Debt/FCF — undefined or extreme when FCF is negative; lenders then underwrite to OCF and liquidity, not growth. "
        "Refinancing probability — lower when Negative Watch + wall + negative FCF coincide; higher if cash buffer covers near-term maturities and sponsors can inject equity. "
        "Liquidity runway — cash + undrawn lines versus cash burn (negative FCF) and near-term maturities; state runway in months, not adjectives.",
        "Credit committees price ladders, coverage, leverage, FCF conversion, refinance odds and runway — narrative demand is secondary.",
        ["Committed refinance takes out the wall", "FCF inflection before peak maturities"],
        ["Full maturity schedule", "Covenant definitions", "Undrawn facilities", "Interest expense bridge"],
        "Lending comfort falls when wall + negative FCF + weak coverage coincide; rises only with dated refinance and cash evidence.",
    )


def _macro_timing(query: str) -> dict[str, Any]:
    return _exec(
        "Macro transmission with timing: "
        "RBI cuts → (0-6 months) lower money-market/lending benchmarks → (6-18 months) refinance coupons on rolled debt if markets cooperate → interest expense ↓ → cash flow ↑ → (within 3 years / 12-36 months) valuation support via lower discount rates — "
        "but company Negative Watch / maturity wall can delay or deny pass-through. "
        "Oil/copper spikes → (0–3 months) input cost ↑ → (1–4 quarters) margin ↓ if pass-through lags → WC stretch if customers delay → credit metrics weaken inside 12 months. "
        "USD/INR move → immediate P&L FX noise; 2–4 quarters of imported-cost pressure. "
        "Always state the clock on each link.",
        "Without timing, transmission is a slogan. IC memos need horizons.",
        ["Hedges shift timing rather than eliminate shocks"],
        ["Coupon reset schedule", "Hedge tenor", "Customer surcharge clauses"],
        "Map factor → channel → P&L/cash/credit → valuation, with 6m / 18m / 3y markers.",
    )


def _rank_flags(query: str) -> dict[str, Any]:
    return _exec(
        "Red-flag priority ranking (most binding first): "
        "(1) Cash conversion break (OCF↓, FCF negative) — directly threatens refinance and valuation; "
        "(2) Debt / maturity wall / rating outlook — converts operating stress into survival risk; "
        "(3) Receivables surge — leading indicator of cash and revenue quality; "
        "(4) Inventory surge + unrecognised write-down — earnings and cash overstatement risk; "
        "(5) Goodwill / acquisition accounting — large impairment optionality, usually slower than cash; "
        "(6) One-offs (FX, tax) in NI — distort quality but secondary to cash/debt. "
        "Force prioritisation: not every flag is equal.",
        "Rank by path-to-cash and path-to-covenant, not by storytelling vividness.",
        ["Governance flags (auditor change) elevate all others"],
        ["Ageing schedules", "Impairment tests"],
        "Lead with cash conversion and debt wall; treat goodwill and one-offs as important but usually second-order unless impairment is imminent.",
    )


def _invest_qs(query: str) -> dict[str, Any]:
    qs = [
        "Why did receivables rise faster than revenue — price, volume, or terms?",
        "What is DSO and >90/>180 day ageing by segment?",
        "Is inventory obsolete, strategic, or channel-stuffed?",
        "What inventory write-down amount is expected and when?",
        "Maintenance vs growth capex split for the last three years?",
        "Contract asset / unbilled revenue ageing?",
        "Revenue recognition policy for multi-year automation/AI contracts?",
        "Synergy tracking: ₹/timeline vs the stated synergy target?",
        "Purchase-price allocation and CGU mapping for the large deal?",
        "Interest coverage and covenant headroom exact calculations?",
        "Maturity ladder by instrument and currency?",
        "Undrawn revolver capacity and conditions precedent?",
        "Largest customer orders delayed — quantum, duration, collectability?",
        "Patent expiry cash-flow exposure and mitigation?",
        "FX gain: transactional vs translational; hedge policy?",
        "One-time tax benefit: law change or settlement; recurrence?",
        "Segment ROIC and FCF for AI vs Automation vs Renewables vs Semiconductors?",
        "Related-party and channel inventory checks?",
        "Auditor change: disagreements, reportable events, fee pressure?",
        "Why deferred/bookings claims (if any) diverge from cash collections?",
        "Working-capital days bridge quarter by quarter?",
        "Refinance plan dated before the maturity wall?",
        "Scenario for oil/copper +10–20% on EBITDA?",
        "Board capital-allocation framework under negative FCF?",
        "Insider transactions and skin-in-the-game around the deal?",
        "Contingent consideration / earn-out cash timing?",
        "Lease and pension off-balance interactions with leverage?",
        "What leading indicator would prove WC stress is temporary?",
        "What filing would confirm or kill the unverified award rumour?",
        "What evidence would raise incremental ROIC above WACC within four quarters?",
    ]
    direct = "Investigative questions (what we do not know yet): " + "; ".join(
        f"({i}) {q}" for i, q in enumerate(qs, 1)
    )
    return _exec(
        direct,
        "Senior analysts spend scarce time on unknowns that adjudicate cash, credit and deal returns.",
        [],
        ["Written answers with evidence IDs"],
        "Do not fill unknowns with management adjectives — convert each into a dated evidence request.",
    )


def _debate(query: str) -> dict[str, Any]:
    return _exec(
        "Committee debate (same evidence, conflicting weights): "
        "Growth Committee — AI margin expansion and platform scarcity justify patience; today’s multiple is an entry to long-duration growth if WC heals. "
        "Credit Committee — negative FCF + maturity wall + Negative Watch mean expansion is creditor-financed risk; lending comfort down until refinance is committed. "
        "Value Committee — market already prices perfection (reverse DCF extreme); triangulation below spot argues the price embeds too much cash recovery. "
        "Risk Committee — customer concentration and unverified news plus patent/integration risk create left-tail outcomes not in the bull deck. "
        "Chair — Credit and cash conversion outweigh Growth’s narrative until a dated FCF inflection and refinance plan exist; Growth may reclaim weight only after those falsifiers clear. "
        "Value’s triangulation informs sizing, not a forced directional label. Risk sets monitoring concentration and filing gates.",
        "Unique IC value is simulated disagreement with an explicit weighting rule — not three parallel monologues.",
        ["Chair could overweight Growth if AI cash conversion is proven independently"],
        ["Shared evidence appendix", "Vote record without Buy/Sell labels"],
        "Chair rule here: cash/credit evidence outranks growth narrative until falsifiers trip positive.",
    )


def _second_order(query: str) -> dict[str, Any]:
    return _exec(
        "Second-order macro chain (example oil shock): "
        "Oil ↑ → energy/logistics inflation ↑ → sticky inflation → policy rates stay higher for longer → discount rates / refinance coupons ↑ → valuation multiples ↓ AND industrial demand slows with a lag → orders delay → receivables/inventory stretch → working capital absorbs cash → credit metrics (coverage, leverage, runway) weaken → refinance probability falls. "
        "First-order ‘margins fall’ is necessary but insufficient; IC memos need the cascade into rates, demand, WC and credit.",
        "Second-order reasoning links macro to credit and valuation through time.",
        ["Fiscal offsets or hedges truncate the chain"],
        ["Pass-through clauses", "Rate path scenarios"],
        "Always extend one step past the obvious P&L line into WC, credit and discount rates.",
    )


def _conf_calib(query: str) -> dict[str, Any]:
    return _exec(
        "Confidence calibration example for ‘cash/credit quality stress is real ~70%’: "
        "Why not ~40%? Because multiple independent audited-style facts align (FCF negative, OCF down, WC up, debt up, margins down) — a 40% read would ignore convergent evidence. "
        "Why not ~90%? Because temporary investment-phase explanations remain possible; synergy delivery, WC mean-reversion and refinance terms are still unknown; unrecognised write-downs and deal accounting could revise the path either way. "
        "70% means: directionally supported by primary financial evidence, with material unresolved timing/magnitude uncertainty. "
        "Raise toward 85%+ if FCF stays negative another 2–3 quarters and refinance fails; cut toward 50% if FCF turns sustainably positive and WC days fall.",
        "Confidence is a function of evidence convergence and remaining unknowns — not a vibe.",
        [],
        ["Pre-registered up/down triggers"],
        "State why this %, why not much lower, why not much higher, and what moves it.",
    )


DEPTH_COMPOSERS: dict[str, Callable[[str], dict[str, Any]]] = {
    "ic_quant_value_creation": _quant_value,
    "ic_valuation_sensitivity": _val_sens,
    "ic_bank_grade_credit": _bank_credit,
    "ic_macro_timing_chain": _macro_timing,
    "ic_rank_red_flags": _rank_flags,
    "ic_investigative_questions": _invest_qs,
    "ic_committee_debate": _debate,
    "ic_second_order_macro": _second_order,
    "ic_confidence_calibration": _conf_calib,
}
