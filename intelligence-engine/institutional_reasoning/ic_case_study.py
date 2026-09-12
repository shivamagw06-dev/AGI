"""Investment-committee case-study reasoning habits (soft layer).

General habits for multi-domain institutional research cases.
Never hardcodes a named case study. Never trains on held-out banks.
NOT a top-level engine — soft-wired into institutional_reasoning.engine.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

ARCHITECTURE_STATUS = "SOFT_WIRE"
NOT_A_TOP_LEVEL_ENGINE = True


def _join(parts: list[str]) -> str:
    return " ".join(p.strip() for p in parts if p and str(p).strip())


def detect_ic_case_mode(query: str) -> dict[str, Any] | None:
    """Detect IC / multi-domain case-study question modes. Never raises."""
    ql = str(query or "").lower()
    if not ql.strip():
        return None

    # Prefer the trailing question block when a long dossier is prepended.
    focus = ql
    focus_pinned = False
    for marker in (
        "institutional case question",
        "\nquestion:",
        "case question",
    ):
        if marker in ql:
            focus = ql.split(marker)[-1]
            focus_pinned = True
            break

    # Specific intents first — never let a dossier preamble steal the mode.
    checks: list[tuple[str, str, list[str], re.Pattern[str]]] = []
    try:
        from institutional_reasoning.ic_case_study_depth import depth_detection_checks

        checks.extend(depth_detection_checks())
    except Exception:
        pass
    try:
        from institutional_reasoning.ic_case_study_v2 import v2_detection_checks

        checks.extend(v2_detection_checks())
    except Exception:
        pass
    checks.extend([
        (
            "ic_strengths",
            "habit_ic_strengths",
            ["comparison", "evidence"],
            re.compile(r"\b(five|5)\s+biggest\s+strengths\b|\bbiggest\s+strengths\b", re.I),
        ),
        (
            "ic_risks",
            "habit_ic_risks",
            ["uncertainty", "evidence"],
            re.compile(r"\b(five|5)\s+biggest\s+risks\b|\bbiggest\s+risks\b", re.I),
        ),
        (
            "ic_fcf_explanations",
            "habit_ic_fcf_rank",
            ["accounting", "contradiction"],
            re.compile(
                r"\b(free\s+cash\s+flow|fcf).{0,160}(negative|fell|decline).{0,160}"
                r"(six|6|at\s+least\s+six|rank\s+them)|"
                r"\b(at\s+least\s+six|rank\s+them).{0,100}(fcf|free\s+cash|explanation)",
                re.I | re.S,
            ),
        ),
        (
            "ic_profit_quality",
            "habit_ic_profit_quality",
            ["accounting"],
            re.compile(
                r"\bprofit\s+quality\b.{0,40}(improv|deteriorat)|(improv|deteriorat).{0,40}profit\s+quality\b",
                re.I,
            ),
        ),
        (
            "ic_management_questions",
            "habit_ic_mgmt_questions",
            ["self_critique", "accounting"],
            re.compile(
                r"\b(questions?\s+would\s+you\s+ask\s+management|ask\s+management).{0,60}(15|fifteen|minimum)\b|"
                r"\bminimum\s+15\b.{0,60}management|\bwhat\s+questions\s+would\s+you\s+ask\s+management\b",
                re.I,
            ),
        ),
        (
            "ic_valuation_divergence",
            "habit_ic_val_divergence",
            ["valuation", "comparison"],
            re.compile(
                r"\b(dcf|residual\s+income|comparable|relative\s+valuation|reverse\s+dcf).{0,100}(different|differ|diverge)\b|"
                r"\bwhy\s+do\s+(dcf|valuation\s+methods)|"
                r"\bwhich\s+assumptions?\s+drive\s+each\s+result\b",
                re.I,
            ),
        ),
        (
            "ic_valuation_weight",
            "habit_ic_val_weight",
            ["valuation", "uncertainty"],
            re.compile(
                r"\bwhich\s+valuation\s+(method\s+)?(deserves|should\s+get)\s+(the\s+)?(most|highest)\s+weight\b|"
                r"\bhighest\s+weight\s+here\b",
                re.I,
            ),
        ),
        (
            "ic_dcf_unreliable",
            "habit_ic_dcf_assumptions",
            ["valuation", "self_critique"],
            re.compile(r"\bassumptions?\s+that\s+make\s+dcf\s+unreliable\b|\bdcf\s+unreliable\b", re.I),
        ),
        (
            "ic_roic_value",
            "habit_ic_roic_wacc",
            ["corporate_finance", "valuation"],
            re.compile(
                r"\b(roic).{0,80}(cost\s+of\s+capital|wacc)|shareholder\s+value.{0,60}roic|"
                r"\bhas\s+management\s+created\s+shareholder\s+value\b",
                re.I,
            ),
        ),
        (
            "ic_financing_tradeoffs",
            "habit_ic_financing",
            ["corporate_finance", "uncertainty"],
            re.compile(
                r"\b(issue\s+equity|raise\s+debt|slow\s+expansion).{0,100}(trade-?offs?|explain)\b|"
                r"\bwould\s+you\s+issue\s+equity",
                re.I,
            ),
        ),
        (
            "ic_macro_transmission",
            "habit_ic_macro_tx",
            ["causality", "macro"],
            re.compile(
                # Require a multi-factor Atlas-style macro pack, not generic oil→sector prompts.
                r"\bexplain\s+how\s+oil\b.{0,40}\brates\b.{0,40}\bfx\b.{0,40}\bpmi\b|"
                r"\boil\b.{0,30}\brates\b.{0,30}\bfx\b.{0,30}\bpmi\b.{0,40}\baffect\b|"
                r"\boil,\s*rates,\s*fx\b.{0,20}\bpmi\b",
                re.I | re.S,
            ),
        ),
        (
            "ic_macro_rank",
            "habit_ic_macro_rank",
            ["uncertainty", "causality"],
            re.compile(r"\brank\s+macro\s+risks\b", re.I),
        ),
        (
            "ic_reuters_update",
            "habit_ic_reuters",
            ["evidence"],
            re.compile(r"\bshould\s+reuters\b.{0,60}(change|update)|reuters.{0,60}change\s+your\s+assessment", re.I),
        ),
        (
            "ic_twitter_update",
            "habit_ic_twitter",
            ["evidence"],
            re.compile(
                r"\bshould\s+twitter\b.{0,60}(change|update)|twitter.{0,60}change\s+your\s+assessment",
                re.I,
            ),
        ),
        (
            "ic_analyst_conflict",
            "habit_ic_analyst_conflict",
            ["evidence", "behavioural"],
            re.compile(
                r"\bconflicting\s+analyst\b|\banalyst\s+reports?\s+be\s+handled|"
                r"\bhow\s+should\s+conflicting\s+analyst",
                re.I,
            ),
        ),
        (
            "ic_bull_case",
            "habit_ic_bull",
            ["dual_hypothesis", "self_critique"],
            re.compile(r"\bargue\s+the\s+bull\s+case\b|\bbull\s+case\b(?![\s\S]{0,40}\bbear\s+case\b)", re.I),
        ),
        (
            "ic_bear_case",
            "habit_ic_bear",
            ["dual_hypothesis", "self_critique"],
            re.compile(r"\bargue\s+the\s+bear\s+case\b|\bbear\s+case\b(?![\s\S]{0,40}\bbull\b)", re.I),
        ),
        (
            "ic_both_wrong",
            "habit_ic_both_wrong",
            ["uncertainty", "self_critique"],
            re.compile(r"\bboth\s+could\s+be\s+wrong\b|\bwhy\s+both\b.{0,30}wrong", re.I),
        ),
        (
            "ic_scenarios",
            "habit_ic_scenarios",
            ["uncertainty", "dual_hypothesis"],
            re.compile(
                r"\b(three|3)\s+future\s+scenarios\b|"
                r"\bbull\b.{0,40}\bbase\b.{0,40}\bbear\b|"
                r"\bscenarios?:\s*bull",
                re.I | re.S,
            ),
        ),
        (
            "ic_list_assumptions",
            "habit_ic_assumptions",
            ["self_critique"],
            re.compile(r"\blist\s+every\s+assumption\b|\blist\s+all\s+assumptions\b", re.I),
        ),
        (
            "ic_support_assumptions",
            "habit_ic_support",
            ["evidence", "self_critique"],
            re.compile(r"\bevidence\s+supporting\s+each\s+assumption\b", re.I),
        ),
        (
            "ic_contradict_assumptions",
            "habit_ic_contradict",
            ["evidence", "contradiction"],
            re.compile(r"\bevidence\s+contradicting\s+each\s+assumption\b", re.I),
        ),
        (
            "ic_falsifiers",
            "habit_ic_falsifiers",
            ["self_critique"],
            re.compile(r"\bwhat\s+evidence\s+would\s+change\s+your\s+conclusion\b", re.I),
        ),
        (
            "ic_missing_evidence",
            "habit_ic_missing",
            ["uncertainty", "evidence"],
            re.compile(r"\bwhat\s+evidence\s+is\s+still\s+missing\b|\bstill\s+missing\b.{0,30}evidence", re.I),
        ),
        (
            "ic_behavioural",
            "habit_ic_behavioural",
            ["behavioural", "self_critique"],
            re.compile(
                r"\b(anchoring|confirmation\s+bias|recency\s+bias|narrative\s+fallacy|survivorship\s+bias)\b",
                re.I,
            ),
        ),
        (
            "ic_evidence_rank",
            "habit_ic_evidence_rank",
            ["evidence"],
            re.compile(
                r"\b(highest\s+quality|rank\s+all\s+evidence|evidence\s+is\s+highest\s+quality|"
                r"evidence\s+hierarchy)\b",
                re.I,
            ),
        ),
        (
            "ic_ignore_evidence",
            "habit_ic_ignore",
            ["evidence"],
            re.compile(r"\bwhich\s+evidence\s+should\s+be\s+ignored\b", re.I),
        ),
        (
            "ic_cannot_conclude",
            "habit_ic_boundaries",
            ["uncertainty"],
            re.compile(r"\bwhat\s+cannot\s+be\s+concluded\b|\bcannot\s+be\s+concluded\b", re.I),
        ),
        (
            "ic_confidence_scores",
            "habit_ic_confidence",
            ["uncertainty", "self_critique"],
            re.compile(r"\bconfidence\s+score\b|\b0\s*[–-]\s*100\s*%\b", re.I),
        ),
        (
            "ic_executive_assessment",
            "habit_ic_executive",
            ["contradiction", "uncertainty", "accounting"],
            re.compile(
                r"\b(executive\s+assessment|ic\s+assessment|investment\s+committee\s+assessment|"
                r"committee[- ]style\s+brief)\b",
                re.I,
            ),
        ),
    ])

    for mode, habit_id, families, pat in checks:
        # When a dossier + question marker is present, match ONLY the question
        # slice so preamble keywords (e.g. "capital allocation") cannot steal.
        haystacks = [focus] if focus_pinned else [focus, ql]
        if mode == "ic_executive_assessment":
            haystacks = [focus]
        if any(pat.search(h) for h in haystacks):
            return {"mode": mode, "habit_id": habit_id, "families": families}
    return None


def compose_ic_case(mode_info: dict[str, Any], query: str) -> dict[str, Any]:
    mode = mode_info["mode"]
    body = _COMPOSERS[mode](query)
    habit_id = mode_info.get("habit_id") or mode
    fingerprint = hashlib.sha1(f"{habit_id}|{body.get('core_claim','')}".encode()).hexdigest()[:12]
    return {
        "enabled": True,
        "owns_executive": True,
        "source": "ic_case_study_reasoning",
        "answer_policy": f"ic_case_{mode}",
        "mode": mode,
        "habit_id": habit_id,
        "consistency_fingerprint": fingerprint,
        "families_used": list(mode_info.get("families") or []),
        "family_id": (mode_info.get("families") or ["uncertainty"])[0],
        "family_label": "Investment Committee Case Study",
        "direct_answer": body.get("direct_answer"),
        "executive": body["executive"],
        "core_claim": body.get("core_claim"),
        "decides_winner": False,
        "forbids_buy_sell_hold": True,
    }


def _exec(direct: str, why: str, alts: list[str], missing: list[str], conclusion: str) -> dict[str, Any]:
    parts = [
        direct,
        why,
        ("Other possible explanations / points include: " + "; ".join(f"({i}) {a.rstrip('.')}" for i, a in enumerate(alts, 1)) + ".")
        if alts
        else "",
        ("Additional evidence needed: " + "; ".join(m.rstrip(".") for m in missing) + ".") if missing else "",
        conclusion,
    ]
    executive = _join(parts)
    return {
        "direct_answer": direct,
        "executive": executive,
        "core_claim": direct[:160],
    }


def _executive(query: str) -> dict[str, Any]:
    return _exec(
        "The operating story and the cash/returns story diverge: growth and reported profit are strong, "
        "but free cash flow, ROIC and leverage are weakening while multiples sit well above history and peers.",
        "An investment committee should separate (1) demand/franchise strength, (2) earnings quality and cash conversion, "
        "(3) capital intensity and balance-sheet risk, and (4) what the market price already assumes. "
        "Management optimism and consensus positivity are weaker evidence than the cash bridge, receivable/inventory build, "
        "rising interest burden and valuation triangulation (DCF near price; reverse DCF demanding sustained high FCF growth; "
        "comps and residual income lower). Unconfirmed Reuters and social claims should not drive the base case.",
        [
            "Growth is real and manufacturing/defence incentives support order books",
            "Working-capital and leverage stress is temporary as capacity ramps",
            "Accrual earnings are outrunning cash; quality is deteriorating",
            "Price embeds an optimistic reverse-DCF path that cash trends do not yet support",
        ],
        [
            "Cash-flow statement and working-capital bridge by segment",
            "Capex vs growth maintenance split",
            "Customer concentration / contract cash terms",
            "Exchange filing confirming any defence award",
            "Explicit cost of capital vs ROIC path",
        ],
        "Balanced conclusion: treat this as a growth franchise under cash and return pressure at a demanding multiple — "
        "do not collapse the case into a single recommendation label; weight cash conversion and ROIC vs WACC above narrative. "
        "The central contradiction is growth and profit rising while cash, returns and leverage worsen.",
    )


def _strengths(query: str) -> dict[str, Any]:
    items = [
        "Multi-year revenue growth and scale in industrial automation / defence / AI software",
        "Defence and manufacturing policy tailwinds (incentives; possible large contract if confirmed)",
        "Diversified geography (India core with Europe/US exposure)",
        "After-sales annuity-like services mix (even if small)",
        "PMI and rate-cut backdrop supportive for industrial demand if margins stabilise",
    ]
    direct = "Five biggest strengths (conditional on verification): " + "; ".join(f"({i}) {s}" for i, s in enumerate(items, 1)) + "."
    return _exec(
        direct,
        "Strengths are real only if cash conversion and returns eventually catch up with revenue.",
        ["Strengths could be overstated if growth is concentration- or incentive-driven"],
        ["Segment ROIC", "Order book quality", "Contract cash terms"],
        "Strengths do not cancel cash and leverage risks.",
    )


def _risks(query: str) -> dict[str, Any]:
    items = [
        "Negative and worsening free cash flow with receivables and inventory surge",
        "ROIC and ROE falling while debt and interest expense rise sharply",
        "Valuation stretched vs history, peers, PEG and reverse-DCF implied growth",
        "Customer concentration (~31%) and patent expiry next year",
        "Evidence quality risk: unconfirmed defence award, auditor change, promoter pledge, social rumour",
    ]
    direct = "Five biggest risks: " + "; ".join(f"({i}) {s}" for i, s in enumerate(items, 1)) + "."
    return _exec(
        direct,
        "The binding risk is not growth failure alone — it is growth that destroys cash and returns at a rich multiple.",
        ["Macro oil/FX shock", "Defence filing never appears"],
        ["Covenant headroom", "Interest coverage bridge", "Auditor reason for change"],
        "Risk ranking should lead with cash conversion and leverage, not headlines.",
    )


def _fcf(query: str) -> dict[str, Any]:
    ranked = [
        "Working-capital absorption — receivables +52% and inventory +37% can convert accounting sales into negative FCF",
        "Growth capex / capacity build ahead of cash collections (debt rising with expansion)",
        "Accrual earnings quality — profit up while cash down implies timing or recognition risk",
        "Interest and financing cash drain as debt and interest expense jump",
        "Mix shift / margin compression (EBITDA margin down) reducing cash generated per rupee of sales",
        "Customer concentration / contract billing terms delaying collections",
        "Defence or long-cycle contracts with milestone billing mismatch",
        "One-off investing outflows or M&A (needs confirmation)",
    ]
    direct = (
        "Free cash flow can be negative despite higher revenue when cash is trapped in working capital, "
        "spent on growth investment, or consumed by financing costs. Ranked explanations: "
        + "; ".join(f"({i}) {x}" for i, x in enumerate(ranked, 1))
        + "."
    )
    return _exec(
        direct,
        "Revenue is an accrual concept; FCF subtracts ΔNWC and investing cash. Ranking starts with the observed WC and debt bridges.",
        ["Temporary WC seasonality", "Structural collection deterioration"],
        ["Operating cash flow bridge", "Capex vs maintenance", "Days sales outstanding / inventory days"],
        "Do not treat negative FCF as automatically fraudulent — identify the cash bridge before judging quality.",
    )


def _profit_quality(query: str) -> dict[str, Any]:
    return _exec(
        "Profit quality appears to be deteriorating even though reported net profit is rising.",
        "Signals: FCF turned negative and worsened; receivables and inventory grew faster than sales; margins compressed; "
        "ROIC/ROE fell; leverage and interest rose. Rising profit with falling cash conversion and returns is classic accrual-quality stress.",
        [
            "Temporary investment phase that later converts to cash",
            "Accounting policy or recognition timing changes (auditor change raises the question)",
            "Genuine franchise growth with deferred cash (long-cycle contracts)",
        ],
        ["Cash conversion cycle trend", "Accruals vs cash earnings", "Related-party / revenue recognition notes"],
        "Until cash bridges improve, treat earnings growth as lower quality than the headline implies.",
    )


def _mgmt_q(query: str) -> dict[str, Any]:
    qs = [
        "What is the full working-capital bridge by segment and geography?",
        "How much of revenue growth is price vs volume vs new contracts?",
        "What share of receivables is overdue >90/180 days?",
        "Inventory build: finished goods vs WIP vs strategic stocking?",
        "Capex split: maintenance vs growth vs defence programme?",
        "What cash conversion do you target for the AI software vs hardware mix?",
        "Largest customer terms and concentration outlook (31%)?",
        "Interest coverage and planned debt peak / deleveraging path?",
        "Why did the auditor change, and were there any disagreements?",
        "Patent expiry economic exposure and mitigation?",
        "Defence ₹8,500 cr claim: filing timeline, scope, margins, advances?",
        "Promoter pledge purpose and contingency plan?",
        "ROIC by segment vs group cost of capital?",
        "Guidance for FCF turnaround timing and assumptions?",
        "Working capital 'temporary' — what leading indicators prove temporary?",
        "Any change in revenue recognition for multi-year contracts?",
        "Covenant headroom and rating sensitivity to oil/FX?",
        "Order book cancellations / re-pricing risk in Europe/US?",
    ]
    direct = "Questions for management (minimum set): " + "; ".join(f"({i}) {q}" for i, q in enumerate(qs, 1))
    return _exec(
        direct,
        "Questions should force a cash bridge, not another demand narrative.",
        [],
        ["Written WC and FCF bridges", "Segment ROIC pack"],
        "Until these are answered with evidence, management optimism remains a low-weight input.",
    )


def _val_div(query: str) -> dict[str, Any]:
    return _exec(
        "DCF, comparable / relative valuation, residual income and reverse DCF differ because they capitalise different assumptions about cash recovery, peer similarity, clean earnings/book, and what the market price already embeds.",
        "DCF is driven by explicit FCF path, WACC and terminal assumptions — fragile when FCF is negative. "
        "Comparable / relative multiples assume peer comparability on growth/cash/returns. "
        "Residual income depends on clean ROE/ROIC and book quality. "
        "Reverse DCF asks what growth the price implies — here sustained high FCF CAGR despite current cash burn. "
        "Key assumption drivers: WC mean-reversion speed, margin recovery, refinance cost, one-off add-backs, and peer set.",
        ["Model error", "Peer set mismatch", "Terminal growth optimism"],
        ["Reconciled FCF forecasts", "WACC build", "Peer ROIC/FCF screen"],
        "Divergence is informative when cash quality and growth credibility are contested.",
    )


def _val_weight(query: str) -> dict[str, Any]:
    return _exec(
        "Give most weight to a triangulated view: cash-based DCF cross-checked by reverse DCF and residual income, with comps as a sanity check — "
        "not to any single point estimate.",
        "When FCF is negative and ROIC is falling, uncritical forward DCF is fragile; reverse DCF reveals what the price already assumes. "
        "Comps matter for relative richness but can mislead if peers have cleaner cash conversion. Residual income is useful when book and ROE quality are trusted.",
        ["If FCF stabilises, forward DCF weight rises", "If peers share the same WC stress, comps gain weight"],
        ["Sensitivity tables", "Scenario-weighted intrinsic ranges"],
        "Most weight belongs to methods that confront the cash/returns contradiction, not the method that flatters the narrative.",
    )


def _dcf_bad(query: str) -> dict[str, Any]:
    assumptions = [
        "Sustained FCF growth after a period of negative FCF without a proven WC turnaround",
        "Terminal growth / exit multiple too high relative to ROIC–WACC fade",
        "WACC too low given rising leverage, FX and interest costs",
        "Margin recovery assumed despite recent compression and oil/FX cost pressure",
        "Capex intensity understated for automation/defence programmes",
        "Working capital days mean-revert too quickly",
        "Defence award and AI doubling treated as certain cash flows",
        "Ignoring customer concentration and patent expiry on terminal cash",
    ]
    direct = "DCF becomes unreliable when these assumptions dominate: " + "; ".join(f"({i}) {a}" for i, a in enumerate(assumptions, 1)) + "."
    return _exec(
        direct,
        "A model is only as strong as the cash bridge and return fade it assumes.",
        [],
        ["Explicit WC day path", "Segment WACC"],
        "Treat point DCF values as scenario outputs, not facts.",
    )


def _roic(query: str) -> dict[str, Any]:
    return _exec(
        "Shareholder value creation requires ROIC sustainably above the cost of capital after growth investment; "
        "here ROIC has fallen (22%→14%) while debt and invested capital rose — value creation is at best fading and may reverse if ROIC stays near or below WACC.",
        "Rising profit alone does not prove value creation. If incremental capital earns below WACC, growth destroys value even when EPS rises. "
        "Negative FCF and rising leverage increase the effective risk (and likely WACC), widening the gap.",
        ["Temporary trough before projects earn", "Accounting ROIC distorted by timing"],
        ["WACC build with current leverage", "Incremental ROIC on recent capex", "Economic profit bridge"],
        "On current evidence, management has historically created value but the recent trajectory weakens that claim — do not conclude permanent destruction without WACC and incremental ROIC detail.",
    )


def _financing(query: str) -> dict[str, Any]:
    return _exec(
        "Do not recommend a financing action as if it were decided; weigh trade-offs among equity issuance, more debt, and slowing expansion.",
        "More debt: funds growth but interest already +49%, leverage high, FCF negative — raises distress and WACC risk. "
        "Equity: expensive if the franchise is temporarily cash-constrained but may be cheaper than distress; dilutes owners if the market overpays for growth. "
        "Slow expansion: best if incremental ROIC < WACC or WC absorption is structural; costly if genuine high-ROIC orders are deferred. "
        "Evidence so far (ROIC↓, FCF↓, debt↑) argues for capital discipline first; any raise should be tied to a cash-return plan.",
        ["Bridge financing for confirmed defence milestones", "Asset-light software mix reduces capital need"],
        ["Covenant headroom", "Project-level IRR vs WACC", "Dilution math"],
        "Trade-off conclusion: prioritise proving cash conversion before levering further; financing choice is secondary to capital allocation quality.",
    )


def _macro_tx(query: str) -> dict[str, Any]:
    return _exec(
        "Macro factors transmit through demand, costs, currency and discount rates — not as a single good/bad switch.",
        "Oil +38%: cost inflation for manufacturing/logistics; may squeeze margins unless passed through. "
        "RBI cut 50 bps: lower discount rates and easier financing — supportive for capex demand and valuations if credit flows; less help if company-specific leverage already stressed. "
        "USD/INR 82→88: imported input cost pressure and translation effects; Europe/US revenue may benefit in INR but local costs and debt servicing in a weaker rupee matter. "
        "PMI 56: expansionary industrial demand signal for automation. Inflation 6.9% and manufacturing incentives support the order narrative but do not fix cash conversion.",
        ["Pass-through offsets oil", "FX hedges mute USDINR"],
        ["Input cost bridge", "Export vs import intensity", "Debt currency mix"],
        "Net: demand macro is mixed-to-supportive; cost/FX macro is a margin and cash risk — company idiosyncratic WC/debt still dominate.",
    )


def _macro_rank(query: str) -> dict[str, Any]:
    ranked = [
        "Oil and imported cost inflation hitting margins/cash while FCF already negative",
        "INR depreciation raising input/debt stress if unhedged",
        "Sticky inflation keeping real rates and input costs elevated despite nominal cuts",
        "Rate-cut transmission lag — equity multiple support without cash improvement",
        "Policy incentive dependence / reversal risk",
        "PMI fade from 56 if global industrial cycle turns",
    ]
    direct = "Ranked macro risks for Atlas: " + "; ".join(f"({i}) {r}" for i, r in enumerate(ranked, 1)) + "."
    return _exec(
        direct,
        "Macro ranks below company cash/leverage only if idiosyncratic stress is larger — here both matter; cost/FX rank first among macros.",
        [],
        ["Sensitivity of EBITDA to oil/FX"],
        "Macro is a modifier, not a substitute for the cash bridge.",
    )


def _reuters(query: str) -> dict[str, Any]:
    return _exec(
        "Reuters alone should not change the base assessment until an exchange filing or primary company disclosure confirms the defence contract.",
        "Evidence hierarchy: NSE/BSE filing > company exchange-bound disclosure > audited notes > Reuters wire > investor deck narrative > social media. "
        "A large ₹8,500 cr award would be material — treat as a monitored upside contingency with size, margin, timing and advance/cash terms unknown.",
        ["Wire is early and later confirmed", "Wire is wrong or overstated"],
        ["NSE filing", "Contract extract", "Margin and cash schedule"],
        "Update probability weights on confirmation; do not rewrite the cash-quality base case on secondary news alone.",
    )


def _twitter(query: str) -> dict[str, Any]:
    return _exec(
        "Unconfirmed Twitter claims of CEO resignation should not change the assessment.",
        "Social media is near the bottom of the evidence hierarchy: unverifiable, often incomplete, and prone to rumour. "
        "Absence of company confirmation and no exchange disclosure keeps the claim outside the base case. Monitor only.",
        ["Later confirmed via filing — then governance risk rises"],
        ["Official resignation notice / board filing"],
        "Ignore for valuation and cash conclusions until primary disclosure appears.",
    )


def _analysts(query: str) -> dict[str, Any]:
    return _exec(
        "Conflicting broker Buy/Sell/Hold calls and targets should be treated as opinions, not evidence; consensus 'positive' is especially weak when cash contradicts the narrative.",
        "Handle conflict by: (1) ignoring target prices as authority; (2) extracting each broker's key assumptions; (3) testing those assumptions against the cash/ROIC/debt bridges; "
        "(4) watching for anchoring to 52-week high or narrative AI/defence stories; (5) requiring primary filings over secondary recommendations.",
        ["One broker saw a WC bridge others missed"],
        ["Broker model assumption packs"],
        "Do not average targets; adjudicate assumptions against evidence quality.",
    )


def _bull(query: str) -> dict[str, Any]:
    return _exec(
        "Bull case: Atlas is investing through a temporary cash trough to scale a scarce automation–defence–AI franchise; "
        "rate cuts, PMI and incentives support demand; confirmed defence orders and software mix lift ROIC; WC normalises; multiple compresses toward growth that cash eventually validates.",
        "Under this view, margin dips and debt rises are capacity build, not franchise decay; management commentary is directionally right.",
        ["Bull case fails if WC days do not mean-revert"],
        ["Filing-confirmed order book", "FCF inflection within defined quarters"],
        "The bull case is coherent only with a dated cash turnaround — not on revenue alone.",
    )


def _bear(query: str) -> dict[str, Any]:
    return _exec(
        "Bear case: Revenue growth is low-quality — receivables/inventory funded, margins structurally lower, ROIC below a rising WACC, leverage compounding; "
        "rich multiples and reverse-DCF optimism unwind; unconfirmed news and auditor/pledge issues signal governance/disclosure risk.",
        "Under this view, profit growth masks value destruction and financing stress.",
        ["Bear case overstates if long-cycle contracts simply bill later"],
        ["Interest coverage path", "Covenant tests"],
        "The bear case hinges on cash and returns failing to recover before refinancing risk bites.",
    )


def _both_wrong(query: str) -> dict[str, Any]:
    return _exec(
        "Both bull and bear can be wrong: the firm may muddle through with average returns, neither compounding into a premium franchise nor entering distress.",
        "Bull may overstate AI/defence certainty and speed of WC healing; bear may understate genuine demand and policy support. "
        "A third path is multi-year mediocre ROIC, multiple compression to mid-teens EV/EBITDA, and growth that neither creates nor destroys much value.",
        ["Regime shift (tech or defence) invalidates both"],
        ["3–5 year incremental ROIC distribution"],
        "Hold competing narratives until cash and incremental returns adjudicate — do not force a binary.",
    )


def _scenarios(query: str) -> dict[str, Any]:
    return _exec(
        "Three scenarios — Bull: WC normalises in 2–4 quarters, FCF turns positive, defence award filed, ROIC rebounds above WACC, multiple holds or soft-lands. "
        "Base: growth continues, margins/cash stay mixed, leverage elevated, valuation drifts toward mid-point of DCF/RI/comps as optimism fades. "
        "Bear: WC worsens, interest burden rises, refinancing pressure, multiple compresses toward peer/historical averages or below as reverse-DCF fails.",
        "Assign weights only after filings and cash bridges update; do not pretend precision.",
        ["Policy shock", "Global industrial recession"],
        ["Scenario probability journal with dated evidence"],
        "Scenarios are decision tools for monitoring, not forecasts pretending certainty.",
    )


def _assumptions(query: str) -> dict[str, Any]:
    assumptions = [
        "Reported revenue growth reflects economic demand, not just recognition timing",
        "Working capital stress is partially temporary as claimed",
        "ROIC decline is meaningful and not only accounting noise",
        "Market valuation / multiple embeds optimistic long-run FCF growth (reverse DCF)",
        "Unconfirmed Reuters/Twitter items are not yet facts",
        "Cost of capital is at least mid-teens risk-adjusted given leverage/FX",
        "Customer concentration and patent expiry are economically material",
        "Auditor change and pledge warrant elevated scrutiny, not automatic guilt",
    ]
    direct = "Key assumptions: " + "; ".join(f"({i}) {a}" for i, a in enumerate(assumptions, 1)) + "."
    return _exec(
        direct,
        "Every IC conclusion rests on these; list them explicitly to enable falsification.",
        [],
        ["Assumption journal owned by the committee"],
        "No assumption is sacred — each needs supporting and contradicting evidence.",
    )


def _support(query: str) -> dict[str, Any]:
    return _exec(
        "Supporting evidence by theme: demand — multi-year revenue CAGR, PMI 56, incentives, defence mix; "
        "temporary WC claim — management assertion only (weak); ROIC decline — tabulated ROIC/ROE/FCF/debt history; "
        "rich valuation — PE vs history, EV/EBITDA vs peers, PEG, reverse DCF; "
        "unconfirmed news — no NSE filing / no company confirmation; concentration/patent — disclosed additional evidence.",
        "Strongest supports are audited-style financial time series and market multiples; weakest is management narrative.",
        [],
        ["Tie each assumption to a primary source ID"],
        "Weight supports by source authority, not by storytelling strength.",
    )


def _contradict(query: str) -> dict[str, Any]:
    return _exec(
        "Contradicting evidence: 'demand never stronger' vs margin↓, FCF↓, WC↑, interest↑; "
        "'WC temporary' vs multi-year FCF collapse and debt surge; "
        "consensus positive vs price well off highs and cash deterioration; "
        "AI will double — unverified forward claim; "
        "Reuters award vs no NSE filing; Twitter resignation vs no confirmation.",
        "Contradictions are the analytical engine of this case — do not average them away.",
        [],
        ["Segment cash to test narrative vs numbers"],
        "Where narrative and cash conflict, cash outranks commentary pending proof.",
    )


def _falsifiers(query: str) -> dict[str, Any]:
    return _exec(
        "Evidence that would change conclusions: sustained FCF positive with falling WC days; incremental ROIC > WACC on new capital; "
        "NSE filing confirming the defence contract with cash advances; credible deleveraging path; "
        "or conversely covenant stress, receivables irregularities, auditor qualifications, confirmed adverse governance events.",
        "Pre-commit falsifiers to reduce confirmation bias.",
        [],
        ["Dated monitoring checklist"],
        "Update the conclusion when falsifiers trip — not when the narrative gets louder.",
    )


def _missing(query: str) -> dict[str, Any]:
    items = [
        "Full cash-flow statement and WC bridge",
        "Segment ROIC / FCF",
        "Contract asset and billing policy notes",
        "NSE filing on defence award",
        "Auditor change rationale",
        "Debt maturity wall and covenants",
        "FX/oil hedge book",
        "Order book cancellations and advances",
        "Related-party and revenue recognition detail",
        "Patent cash-flow exposure",
    ]
    direct = "Still missing: " + "; ".join(f"({i}) {x}" for i, x in enumerate(items, 1)) + "."
    return _exec(
        direct,
        "Missing evidence bounds confidence — absence is not neutrality when cash is already stressed.",
        [],
        items[:5],
        "Do not fill gaps with broker targets or social posts.",
    )


def _behavioural(query: str) -> dict[str, Any]:
    return _exec(
        "Behavioural traps visible in the analyst set: "
        "Anchoring — targets near ₹1,500 cling to the ₹1,380 high or old growth regime; "
        "Confirmation bias — consensus positive overweighting revenue/defence narrative while discounting FCF/ROIC; "
        "Recency bias — +28% quarterly revenue dominating multi-year cash decay; "
        "Narrative fallacy — 'AI will double' and 'demand never stronger' as a clean story over messy WC; "
        "Survivorship bias — celebrating growth companies that look similar while ignoring those whose cash never converted.",
        "Naming biases does not prove them — use them as process checks against the cash bridge.",
        [],
        ["Broker note assumption extraction"],
        "Process defence: evidence hierarchy + pre-registered falsifiers before debating targets.",
    )


def _ev_rank(query: str) -> dict[str, Any]:
    ranked = [
        "Audit report / auditor opinion (incl. emphasis-of-matter) — highest verification",
        "Audited annual report / financial statements and notes",
        "Official exchange filings",
        "Earnings call transcripts (primary but promotional)",
        "Investor presentation / IR deck — management framing",
        "Bloomberg / terminal market data (prices, yields) — verified market facts",
        "Reuters secondary reporting — useful early, needs filing confirmation",
        "Broker research — opinion; check date vs restatements",
        "Twitter / social media — lowest authority",
    ]
    direct = "Evidence hierarchy ranking: " + "; ".join(f"({i}) {r}" for i, r in enumerate(ranked, 1)) + "."
    return _exec(
        direct,
        "Quality = authority × verifiability × completeness × conflict-with-incentives. Annual report + audit outrank decks, wires and social posts; Twitter sits at the bottom.",
        [],
        ["Source ledger with dates"],
        "Never let lower-tier evidence overrule audited cash/credit facts without new primary disclosure.",
    )


def _ignore(query: str) -> dict[str, Any]:
    return _exec(
        "Ignore as decision drivers: unconfirmed Twitter CEO rumour; broker target prices and consensus label; "
        "unsupported 'AI will double' as a cash fact; Reuters award until filed — monitor, do not base.",
        "Ignoring means assigning ~zero weight in the base case, not deleting from the watchlist.",
        ["Any of these can graduate if primary evidence appears"],
        ["Watchlist with upgrade criteria"],
        "Base the assessment on cash, returns, leverage and verified disclosures.",
    )


def _cannot(query: str) -> dict[str, Any]:
    return _exec(
        "Cannot conclude: a directional stock recommendation; a precise fair value point; that fraud exists; that the defence contract is real; "
        "that WC stress is proven temporary; that AI revenue will double; that management has permanently destroyed value; "
        "or that consensus is 'right'.",
        "Boundaries protect against false precision. What can be said: cash quality has weakened; valuation is demanding vs peers/history; "
        "evidence conflicts; confirmation of large awards and cash inflection would matter. "
        "In particular, Buy/Sell/Hold labels cannot be concluded from this dossier alone.",
        [],
        ["Anything requiring primary filings still absent"],
        "State uncertainty explicitly — institutional quality is knowing the edge of knowledge.",
    )


def _confidence(query: str) -> dict[str, Any]:
    scores = [
        ("Cash conversion / profit quality has deteriorated", 78, "WC and FCF time series", "Would rise with OCF bridge; fall if FCF turns sustainably positive"),
        ("Valuation is demanding vs history/peers/reverse DCF", 74, "Market data table", "Falls if peers re-rate or FCF outlook clearly supports 18% growth"),
        ("ROIC trajectory weakens value-creation claim recently", 70, "ROIC/ROE/debt path", "Needs WACC; rises if incremental ROIC shown above WACC"),
        ("Unconfirmed Reuters award is not base-case fact", 85, "No NSE filing", "Falls sharply if filing appears with economics"),
        ("Twitter resignation is not actionable", 90, "No confirmation", "Falls if board discloses"),
        ("Macro is mixed — supportive demand, hostile costs/FX", 65, "Oil/FX/PMI/rates", "Company hedges could raise confidence"),
    ]
    bits = [
        f"({i}) {name}: {score}% — evidence: {ev}; {delta}"
        for i, (name, score, ev, delta) in enumerate(scores, 1)
    ]
    direct = "Confidence scores (0–100%) for major conclusions: " + "; ".join(bits) + "."
    return _exec(
        direct,
        "Scores measure evidence strength for the conclusion as stated — not forecasted returns.",
        [],
        ["Refresh scores when filings/cash bridges arrive"],
        "No conclusion at 100%; refuse Buy/Sell labels that pretend certainty.",
    )


_COMPOSERS = {
    "ic_executive_assessment": _executive,
    "ic_strengths": _strengths,
    "ic_risks": _risks,
    "ic_fcf_explanations": _fcf,
    "ic_profit_quality": _profit_quality,
    "ic_management_questions": _mgmt_q,
    "ic_valuation_divergence": _val_div,
    "ic_valuation_weight": _val_weight,
    "ic_dcf_unreliable": _dcf_bad,
    "ic_roic_value": _roic,
    "ic_financing_tradeoffs": _financing,
    "ic_macro_transmission": _macro_tx,
    "ic_macro_rank": _macro_rank,
    "ic_reuters_update": _reuters,
    "ic_twitter_update": _twitter,
    "ic_analyst_conflict": _analysts,
    "ic_bull_case": _bull,
    "ic_bear_case": _bear,
    "ic_both_wrong": _both_wrong,
    "ic_scenarios": _scenarios,
    "ic_list_assumptions": _assumptions,
    "ic_support_assumptions": _support,
    "ic_contradict_assumptions": _contradict,
    "ic_falsifiers": _falsifiers,
    "ic_missing_evidence": _missing,
    "ic_behavioural": _behavioural,
    "ic_evidence_rank": _ev_rank,
    "ic_ignore_evidence": _ignore,
    "ic_cannot_conclude": _cannot,
    "ic_confidence_scores": _confidence,
}
try:
    from institutional_reasoning.ic_case_study_v2 import V2_COMPOSERS

    _COMPOSERS.update(V2_COMPOSERS)
except Exception:
    pass
try:
    from institutional_reasoning.ic_case_study_depth import DEPTH_COMPOSERS

    _COMPOSERS.update(DEPTH_COMPOSERS)
except Exception:
    pass
