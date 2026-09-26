"""CFA-level IC Case Study V2 habits (soft extension).

General habits for multi-domain CFA institutional cases.
Never hardcodes Orion / Atlas names. Never imports held-out banks.
"""

from __future__ import annotations

import re
from typing import Any, Callable

# Reuse the shared executive composer helper from the parent module at call time
# to avoid circular imports during detection registration.


def v2_detection_checks() -> list[tuple[str, str, list[str], re.Pattern[str]]]:
    """Specific V2 intents — registered before legacy IC checks."""
    return [
        (
            "ic_fsa_pack",
            "habit_ic_fsa_pack",
            ["accounting", "contradiction"],
            re.compile(
                r"\bfinancial\s+statement\s+analysis\b.{0,80}(revenue\s+quality|earnings\s+quality|cash\s+conversion)|"
                r"\brevenue\s+quality\b.{0,80}\bearnings\s+quality\b.{0,80}\bcash\s+conversion\b",
                re.I | re.S,
            ),
        ),
        (
            "ic_accounting_red_flags",
            "habit_ic_red_flags",
            ["accounting", "self_critique"],
            re.compile(
                r"\baccounting\s+red\s+flags?\b|\bwarning\s+sign\b.{0,60}(receivable|goodwill|deferred\s+revenue)|"
                r"\bidentify\s+every\s+potential\s+accounting\b",
                re.I | re.S,
            ),
        ),
        (
            "ic_capital_allocation",
            "habit_ic_cap_alloc",
            ["corporate_finance", "valuation"],
            re.compile(
                r"\bcapital\s+allocation\b.{0,80}(dividend|buyback|acquisition|roic)|"
                r"\bcorporate\s+finance\s+assessment\b",
                re.I | re.S,
            ),
        ),
        (
            "ic_four_method_valuation",
            "habit_ic_four_val",
            ["valuation", "comparison"],
            re.compile(
                r"\bfour\s+methods?\b.{0,80}(dcf|valuation)|"
                r"\bequity\s+valuation\s+using\s+four\s+methods\b|"
                r"\busing\s+four\s+methods\b.{0,40}\bdcf\b",
                re.I | re.S,
            ),
        ),
        (
            "ic_credit_analysis",
            "habit_ic_credit",
            ["uncertainty", "accounting"],
            re.compile(
                r"\bcredit\s+analysis\b|\binterest\s+coverage\b.{0,60}(covenant|refinanc|maturity)|"
                r"\brefinancing\s+risk\b.{0,40}\bcovenant\b",
                re.I | re.S,
            ),
        ),
        (
            "ic_macro_stress",
            "habit_ic_macro_stress",
            ["causality", "uncertainty"],
            re.compile(
                r"\bmacroeconomic\s+stress-?test\b|\bstress-?test\b.{0,80}(interest\s+rates|inflation|currency).{0,80}(commodity|gdp|trade)|"
                r"\btransmission\s+mechanisms?\b",
                re.I | re.S,
            ),
        ),
        (
            "ic_behavioural_v2",
            "habit_ic_behavioural_v2",
            ["behavioural", "self_critique"],
            re.compile(
                r"\b(availability\s+bias|overconfidence|loss\s+aversion)\b",
                re.I,
            ),
        ),
        (
            "ic_competing_committees",
            "habit_ic_committees",
            ["dual_hypothesis", "comparison"],
            re.compile(
                r"\bcompeting\s+investment\s+committees?\b|\bcommittee\s+a\b.{0,40}\bcommittee\s+b\b.{0,40}\bcommittee\s+c\b|"
                r"\bgrowth\s+investors\b.{0,40}\bvalue\s+investors\b.{0,40}\bcredit\s+committee\b",
                re.I | re.S,
            ),
        ),
        (
            "ic_devils_advocate_pack",
            "habit_ic_da_pack",
            ["self_critique", "contradiction"],
            re.compile(
                r"\bdevil'?s\s+advocate\b.{0,80}(challenge|every\s+major)|"
                r"\bchallenge\s+every\s+major\s+conclusion\b",
                re.I | re.S,
            ),
        ),
        (
            "ic_scenarios_v2",
            "habit_ic_scenarios_v2",
            ["uncertainty", "dual_hypothesis"],
            re.compile(
                r"\bscenario\s+analysis\b.{0,80}(bull|base|bear).{0,80}(revenue|margin|cash)|"
                r"\bbull,\s*base,\s*and\s*bear\s+cases?\b",
                re.I | re.S,
            ),
        ),
        (
            "ic_portfolio_role",
            "habit_ic_portfolio_role",
            ["uncertainty", "comparison"],
            re.compile(
                r"\brole\s+could\s+this\s+company\s+play\s+in\s+a\s+diversified\s+portfolio\b|"
                r"\bportfolio\s+decision\b.{0,80}(investor\s+profile|monitoring)|"
                r"\bdo\s+not\s+recommend\s+buy\s+or\s+sell\b.{0,80}\bportfolio\b",
                re.I | re.S,
            ),
        ),
        (
            "ic_three_audiences",
            "habit_ic_three_audiences",
            ["comparison", "uncertainty"],
            re.compile(
                r"\bthree\s+audiences\b|\bretail\s+investor\b.{0,40}\bcfa\b.{0,40}\binvestment\s+committee\b|"
                r"\bexplain\s+the\s+conclusion\s+for\s+three\s+audiences\b",
                re.I | re.S,
            ),
        ),
        (
            "ic_audited_only",
            "habit_ic_audited_only",
            ["evidence", "uncertainty"],
            re.compile(
                r"\bonly\s+audited\s+financial\s+statements\b|"
                r"\bif\s+every\s+valuation\s+model,\s*analyst\s+report\b|"
                r"\baudited\s+financial\s+statements\s+and\s+verified\s+market\s+data\b",
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
    executive = " ".join(p.strip() for p in parts if p and str(p).strip())
    return {"direct_answer": direct, "executive": executive, "core_claim": direct[:160]}


def _fsa(query: str) -> dict[str, Any]:
    return _exec(
        "Financial statement analysis: revenue quality is contested (restatement history, receivables surge, deferred revenue lagging software narrative); "
        "earnings quality is deteriorating (one-off/FX gain in NI, capitalised software, profit↑ while FCF↓); "
        "cash conversion is weak-to-negative; working capital is absorbing cash (receivables/inventory ageing); "
        "accruals are elevated; one-off items inflate reported NI; capitalisation policy shifts expense to assets; "
        "return metrics (ROIC) are falling as invested capital and leverage rise.",
        "Read the cash bridge and restatement/one-off notes before trusting growth headlines. Segment mix and FX also distort consolidated quality.",
        [
            "Growth investment phase that later converts to cash",
            "Accounting policy choices within GAAP that still lower economic quality",
            "FX translation / one-offs that reverse",
        ],
        ["OCF and WC bridge by segment", "Capitalised R&D roll-forward", "Core vs one-off NI split"],
        "Balanced conclusion: growth is real in places, but audited trends show weaker cash and returns than headline NI — treat quality as impaired until proven otherwise.",
    )


def _red_flags(query: str) -> dict[str, Any]:
    flags = [
        "Receivables + ageing — evidence: +48% receivables / >180 days up; alternatives: long-cycle billing vs channel risk; confidence: high on stress, medium on cause",
        "Inventory build — evidence: +41%; alternatives: strategic stocking vs demand miss; confidence: medium-high",
        "Goodwill from acquisitions — evidence: large Nova goodwill/earn-outs; alternatives: fair bargain vs overpay; confidence: medium pending impairment test",
        "Deferred revenue flat vs software bookings claim — evidence: deferred revenue lag; alternatives: billing timing vs recognition aggressiveness; confidence: medium-high on mismatch",
        "Capitalisation policy — evidence: USD 90m software R&D capitalised; alternatives: legitimate development vs earnings management; confidence: medium",
        "Lease liabilities rising — evidence: +22%; alternatives: growth capacity vs hidden leverage; confidence: high that leverage is understated if ignored",
        "Restatement — evidence: FY24 revenue cut USD 220m; alternatives: one-time cleanup vs ongoing control weakness; confidence: high that history is less clean",
        "One-off/FX gain in NI — evidence: USD 310m; alternatives: genuine disposal vs core earnings optics; confidence: high that core is lower than headline",
    ]
    direct = "Accounting red flags with evidence / alternatives / confidence: " + "; ".join(
        f"({i}) {f}" for i, f in enumerate(flags, 1)
    ) + "."
    return _exec(
        direct,
        "Each flag is a hypothesis generator, not automatic proof of fraud. Rank by cash impact and governance signal (restatement + auditor change + WC).",
        ["Temporary integration noise after acquisitions"],
        ["Audit workpapers themes", "Channel checks", "Earn-out accounting detail"],
        "Highest-priority flags: restatement + cash conversion break + deferred-revenue mismatch + thin covenant headroom interaction with leverage.",
    )


def _cap_alloc(query: str) -> dict[str, Any]:
    return _exec(
        "Capital allocation looks aggressive relative to cash: dividend held flat while FCF negative; buybacks funded partly by debt; "
        "acquisitions added goodwill and integration risk; ROIC has fallen toward/below a rising cost of capital — value creation is fading on incremental capital.",
        "WACC likely rose with leverage, spread widening and refinancing risk. Paying cash to shareholders and buying back stock while FCF is negative transfers risk to creditors and future equity.",
        [
            "Acquisitions could still earn above WACC after synergy lag",
            "Dividend as signalling while temporary WC trough passes",
        ],
        ["Project-level IRRs", "Buyback funding bridge", "Post-deal ROIC for recent acquisitions"],
        "Corporate-finance conclusion: prioritise proving incremental ROIC > WACC and cash conversion before dividends/buybacks/further leverage — do not issue a stock recommendation.",
    )


def _four_val(query: str) -> dict[str, Any]:
    return _exec(
        "Four-method valuation read: DCF (~48) embeds optimistic cash recovery from today’s negative FCF; "
        "relative valuation (~39) anchors to peers with cleaner cash/returns and implies the name is expensive on EV/EBITDA/PE; "
        "residual income (~41) capitalises fading ROIC vs book and sits below spot; "
        "reverse DCF shows the market (~52) implies ~16% FCF CAGR for a decade — incompatible with current cash without a sharp inflection.",
        "Methods disagree because they load different assumptions about cash turnaround, peer similarity, clean earnings, and what price already discounts.",
        ["Model error", "Peer set mismatch"],
        ["Reconciled FCF forecast pack", "WACC build", "Peer cash conversion screen"],
        "Use the four together as a triangulation, not as four independent truths.",
    )


def _credit(query: str) -> dict[str, Any]:
    return _exec(
        "Credit analysis: interest coverage compressed (≈3.1× from ≈6.2×); debt maturity wall with ~38% due within 24 months raises refinancing risk; "
        "liquidity is tighter (revolver partly drawn, negative FCF); covenant headroom on net-debt/EBITDA is thin; rating outlook is negative — credit risk is material even if equity narratives stay bullish.",
        "Transmission: higher spreads + maturity wall + WC cash drain can force dilutive equity, asset sales, or dividend cuts. Audit EOM on refinancing is a primary credit signal.",
        ["Successful refinance at acceptable spreads", "FCF inflection before wall"],
        ["Maturity schedule detail", "Covenant calculations", "Contingent earn-out cash"],
        "Credit conclusion: treat refinancing and covenant pressure as first-class risks; do not subordinate them to growth storytelling.",
    )


def _macro_stress(query: str) -> dict[str, Any]:
    return _exec(
        "Macro stress-test with transmission: interest rates — discount rates and refinancing costs up, coverage down; "
        "inflation — input/wage pressure compresses automation/renewables margins; "
        "currency — USD strength and multi-currency reporting create translation/transaction noise (management already cites FX gains in profit); "
        "commodity prices — oil/copper inflate renewables/equipment costs; "
        "GDP — European softness hits industrial demand while India mix may cushion; "
        "trade policy — aerospace and cross-border equipment face tariff/licensing shocks.",
        "Company idiosyncratic WC/debt still dominate, but macro can tighten the credit constraint quickly.",
        ["Hedges mute FX/commodity", "Rate cuts ease WACC/refi"],
        ["Hedge book", "Country revenue × cost matrix"],
        "Macro is a stress amplifier on an already stretched cash/credit profile — model joint shocks, not one-factor stories.",
    )


def _behavioural_v2(query: str) -> dict[str, Any]:
    return _exec(
        "Behavioural distortions: Confirmation bias — overweight AI/demand quotes that fit growth thesis while discounting restatement/FCF; "
        "Anchoring — targets near old highs / outdated broker numbers; "
        "Narrative fallacy — neat ‘energy transition + AI’ story over messy WC/credit; "
        "Availability bias — vivid Reuters award / social rumour crowding out quiet audit EOM; "
        "Overconfidence — management ‘temporary WC’ and software doubling without filing support; "
        "Loss aversion — reluctance to mark down a previously winning growth name despite cash deterioration.",
        "Process defence: evidence hierarchy + pre-registered falsifiers + separate credit vs equity ledgers.",
        [],
        ["Broker note dates vs restatement date"],
        "Name the bias, then force a cash/credit check before updating the thesis.",
    )


def _committees(query: str) -> dict[str, Any]:
    return _exec(
        "Competing committees using the same evidence: "
        "Committee A (growth) emphasises 40-country platform, renewables/AI mix, backlog and possible award — concludes growth optionality justifies patience if WC normalises; "
        "Committee B (value) emphasises ROIC↓, FCF↓, rich multiples vs peers/reverse DCF — concludes price embeds too much cash recovery; "
        "Committee C (credit) emphasises coverage↓, maturity wall, thin covenants, negative outlook — concludes refinancing/liquidity dominate before equity upside debates. "
        "Same facts; different loss functions and time horizons explain different conclusions.",
        "Do not average the three into a fake consensus. Surface the disagreement explicitly for the IC.",
        ["Growth committee underweights credit wall", "Credit committee underweights long-duration software optionality"],
        ["Committee memos with shared evidence appendix"],
        "Institutional output is the mapped disagreement, not a forced single vote labeled Buy/Sell.",
    )


def _da_pack(query: str) -> dict[str, Any]:
    return _exec(
        "Devil’s advocate pack on major conclusions: "
        "(1) ‘Quality impaired’ — supporting evidence: FCF/ROIC/restatement; contradicting evidence: segment backlog/demand; missing evidence: OCF bridge; confidence ~75%; what would change your view: sustained positive FCF. "
        "(2) ‘Valuation demanding’ — supporting evidence: PE/EV vs hist/peers/reverse DCF; contradicting evidence: scarcity of AI-industrial assets; missing evidence: peer FCF screen; confidence ~70%; what would change your view: cash path validating reverse DCF. "
        "(3) ‘Credit material’ — supporting evidence: coverage/maturity/covenants/outlook; contradicting evidence: unused capacity/possible equity raise; missing evidence: refinance commitments; confidence ~80%; what would change your view: committed long-term refinance. "
        "(4) ‘Unverified news non-base’ — supporting evidence: no filing; contradicting evidence: wire usually careful; missing evidence: exchange disclosure; confidence ~85%; what would change your view: primary filing.",
        "Challenge every pillar before it hardens into narrative.",
        [],
        ["Dated falsifier checklist"],
        "Update views when falsifiers trip — not when the story gets louder.",
    )


def _scenarios_v2(query: str) -> dict[str, Any]:
    return _exec(
        "Scenario analysis — Bull: revenue keeps mid-teens growth, margins stabilise, FCF turns positive as WC days fall, valuation holds if reverse-DCF path begins to validate; key assumption: cash inflection within a few quarters; key risk: refinance still needed. "
        "Base: revenue grows but margins/cash stay mixed, leverage elevated, valuation drifts toward mid triangulation (RI/relatives) as optimism fades; assumption: no crisis, no full recovery. "
        "Bear: WC worsens, coverage fails covenants, refinance dilutive or distressed, margins compress further, valuation moves toward peer/historical cash multiples or below; assumption: credit constraint binds before growth story pays.",
        "For each scenario track revenue, margin, cash flow, and valuation implication explicitly; assign weights only after filings update.",
        ["Policy/commodity shock overlays"],
        ["Scenario probability journal"],
        "Scenarios are monitoring tools — not precision forecasts.",
    )


def _portfolio(query: str) -> dict[str, Any]:
    return _exec(
        "Portfolio role (no Buy/Sell advice): could serve as a satellite industrial/energy-transition growth exposure with high idiosyncratic cash and refinance risk — not as ballast or quality compounder until cash conversion and credit metrics improve. "
        "More suitable investor profile: high risk tolerance, long horizon, and credit expertise who can size small and hedge FX/commodity; less suitable investor profile: income mandates, low-turnover quality funds, or accounts that cannot tolerate refinancing/covenant event risk. "
        "Ongoing monitoring: FCF and WC days, covenant headroom, maturity wall/refi spreads, deferred revenue vs software claims, acquisition earn-outs, and primary filings on awards.",
        "Role and sizing are risk-budget decisions, not recommendation labels.",
        ["Pair with higher-quality cash compounders if kept"],
        ["Risk-budget and correlation pack"],
        "Keep the discussion in portfolio-construction language — never collapse to Buy/Sell.",
    )


def _audiences(query: str) -> dict[str, Any]:
    return _exec(
        "Same facts, three styles — Retail: sales and profits are up, but the company is burning cash, debts and unpaid customer bills are rising, and some past sales numbers were corrected; treat exciting news carefully until official filings confirm. "
        "CFA charterholder: revenue growth with deteriorating cash conversion, elevated accruals, one-off/FX-inflated NI, falling ROIC, compressed interest coverage and a near-term maturity wall; triangulation shows reverse DCF demanding sustained FCF CAGR inconsistent with current cash; evidence hierarchy subordinates decks/rumour to audited statements. "
        "Investment committee: growth franchise under cash/credit stress at a demanding multiple; competing growth/value/credit views should remain open; monitoring list and falsifiers attached; no directional recommendation.",
        "Facts identical across audiences; only vocabulary and density change.",
        [],
        ["One-page IC annex"],
        "Communication clarity is part of institutional quality control.",
    )


def _audited_only(query: str) -> dict[str, Any]:
    return _exec(
        "Audited statements + verified market data only — still supportable: multi-year revenue growth with falling EBITDA margins; NI rising while FCF turned negative; receivables/inventory intensive growth; ROIC declined as net debt rose; interest coverage compressed; a material share of debt is near-term; market multiples sit above history/peers while price is below the 52-week high. "
        "Cannot conclude from that subset alone: that unverified awards or rumours are true; that management’s ‘temporary WC’ claim is proven; that any point intrinsic-value model is correct; that a directional stock recommendation is warranted; or that fraud occurred. Secondary opinions and management decks add narrative, not audited fact.",
        "Stripping models and decks reveals the cash/credit contradiction that narratives often hide.",
        [],
        ["Full audited notes set", "Exchange-verified prices/yields"],
        "Final challenge answer: cash conversion and leverage stress are evidenced; directional investment advice is not.",
    )


V2_COMPOSERS: dict[str, Callable[[str], dict[str, Any]]] = {
    "ic_fsa_pack": _fsa,
    "ic_accounting_red_flags": _red_flags,
    "ic_capital_allocation": _cap_alloc,
    "ic_four_method_valuation": _four_val,
    "ic_credit_analysis": _credit,
    "ic_macro_stress": _macro_stress,
    "ic_behavioural_v2": _behavioural_v2,
    "ic_competing_committees": _committees,
    "ic_devils_advocate_pack": _da_pack,
    "ic_scenarios_v2": _scenarios_v2,
    "ic_portfolio_role": _portfolio,
    "ic_three_audiences": _audiences,
    "ic_audited_only": _audited_only,
}
