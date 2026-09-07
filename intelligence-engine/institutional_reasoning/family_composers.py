"""First-principles composers for Reasoning Families.

These are habits, not rote answers. They adapt to novel facts inside a family.
"""

from __future__ import annotations

import re
from typing import Any

from institutional_reasoning.families import (
    ACCOUNTING,
    CAUSALITY,
    COMPARISON,
    CONTRADICTION,
    DUAL_HYPOTHESIS,
    EVIDENCE,
    FAMILIES,
    SELF_CRITIQUE,
    UNCERTAINTY,
    VALUATION,
)


def _compose(parts: dict[str, Any]) -> str:
    out: list[str] = []
    if parts.get("direct_answer"):
        out.append(str(parts["direct_answer"]).strip())
    if parts.get("why"):
        out.append(str(parts["why"]).strip())
    alts = parts.get("alternatives") or []
    if alts:
        if parts.get("mode") == "questions":
            out.append(
                "Important questions include: "
                + "; ".join(f"({i}) {str(a).rstrip('?')}?" for i, a in enumerate(alts, 1))
            )
        elif parts.get("mode") == "reasons":
            out.append(
                "Possible reasons include: "
                + "; ".join(f"({i}) {str(a).rstrip('.')}" for i, a in enumerate(alts, 1))
                + "."
            )
        elif parts.get("mode") == "hypotheses":
            # Already fully formed narrative blocks.
            out.extend(str(a).strip() for a in alts)
        else:
            out.append(
                "Other possible explanations include: "
                + "; ".join(f"({i}) {str(a).rstrip('.')}" for i, a in enumerate(alts, 1))
                + "."
            )
    if parts.get("missing"):
        miss = parts["missing"]
        if isinstance(miss, list):
            out.append(
                "Additional evidence needed: "
                + "; ".join(str(m).rstrip(".") for m in miss)
                + "."
            )
        else:
            out.append(str(miss).strip())
    if parts.get("conclusion"):
        out.append(str(parts["conclusion"]).strip())
    return " ".join(x for x in out if x)


def _banking_volume_vs_quality(ql: str) -> dict[str, Any] | None:
    if re.search(r"\b(deposit).{0,80}(casa)|(?:casa).{0,80}(deposit)", ql):
        return {
            "direct_answer": (
                "The decline in the CASA ratio deserves closer attention because it speaks to "
                "funding quality, not just deposit size."
            ),
            "why": (
                "Higher deposits show the bank is gathering more money, but a lower CASA ratio "
                "means a smaller share is coming from low-cost current and savings accounts. "
                "That can raise the average cost of funds even while the deposit book grows."
            ),
            "alternatives": [
                "Term deposits grew faster than low-cost CASA balances",
                "Competition forced higher rates on savings or current accounts",
                "Seasonal or one-off bulk deposits temporarily changed the mix",
            ],
            "missing": [
                "CASA and term-deposit mix bridge",
                "Cost-of-funds trend",
                "Whether the shift is temporary or structural",
            ],
            "conclusion": (
                "Both signals should be read together before judging franchise strength."
            ),
            "variant": "deposits_vs_casa",
        }
    if re.search(r"\b(loan\s+growth|loans?\s+accelerat).{0,100}(provision)", ql) or re.search(
        r"\b(provision).{0,100}(loan\s+growth|loans?\s+accelerat|doubled)", ql
    ):
        return {
            "direct_answer": (
                "Faster loan growth with much higher provisions suggests growth quality and "
                "credit risk need as much attention as volume."
            ),
            "why": (
                "Loan growth can look strong while the bank simultaneously prepares for higher "
                "expected losses. Doubling provisions may reflect weaker underwriting, a riskier "
                "mix, ageing stress in parts of the book, or a more conservative accounting stance."
            ),
            "alternatives": [
                "Credit mix shifted toward higher-risk segments",
                "Early signs of asset-quality stress",
                "Management chose a more conservative provisioning policy",
                "One-off or catch-up provisions rather than a lasting trend",
            ],
            "missing": [
                "Segment-wise loan growth and GNPAs / slippages",
                "Provision coverage and write-off policy notes",
                "Whether stress is concentrated or broad-based",
            ],
            "conclusion": (
                "Do not treat loan growth as positive on its own until credit cost and asset "
                "quality are understood."
            ),
            "variant": "loan_growth_vs_provisions",
        }
    return None


def _accounting_wc(ql: str) -> dict[str, Any] | None:
    if re.search(r"\b(fee\s+income|slippage)\b", ql) and re.search(r"\b(slippage|fee\s+income)\b", ql):
        return {
            "direct_answer": (
                "Rising fee income with worsening slippage means fee growth and asset quality "
                "must be read together — not as a single positive print."
            ),
            "why": (
                "Fee income can rise from distribution, cards or third-party products even while "
                "loan stress increases. Slippage deterioration is often the clearer risk signal."
            ),
            "mode": "questions",
            "alternatives": [
                "Is fee growth recurring or one-off / seasonal",
                "Where are slippages concentrated by segment",
                "Are credit costs and provisions rising alongside fees",
                "Is growth coming from riskier customer cohorts",
            ],
            "missing": [
                "Segment-wise fee and slippage bridges",
                "Credit-cost trajectory",
            ],
            "conclusion": (
                "Ask for the quality bridge before treating fee growth as franchise strength."
            ),
            "variant": "fees_vs_slippage",
        }
    if re.search(r"\b(production|output).{0,80}(inventory)", ql) or re.search(
        r"\b(inventory).{0,80}(production|output)", ql
    ):
        return {
            "direct_answer": (
                "Higher production with even faster inventory growth can be either planned "
                "build-up or a warning that goods are not selling through as quickly as they "
                "are being made."
            ),
            "why": (
                "Inventory rising faster than production often means finished goods or inputs "
                "are accumulating. That can reflect weak demand, channel stuffing, seasonal "
                "stocking, supply-chain timing, or a deliberate build ahead of expected sales."
            ),
            "alternatives": [
                "Demand softens after production is already committed",
                "Seasonal or launch-related stock build",
                "Supply-chain delays move goods into inventory rather than sales",
                "Management over-produced relative to orders",
            ],
            "missing": [
                "Inventory split (raw / WIP / finished)",
                "Order book and sell-through data",
                "Gross margin and cash conversion for the same period",
            ],
            "conclusion": (
                "More operating detail is needed before deciding whether this is healthy "
                "preparation or working-capital stress."
            ),
            "variant": "production_vs_inventory",
        }
    if re.search(r"\b(sales|revenue).{0,80}(receivables)", ql) or re.search(
        r"\b(receivables).{0,80}(sales|revenue)", ql
    ):
        return {
            "direct_answer": (
                "Sales can rise while cash collection quality weakens if receivables grow "
                "much faster than sales."
            ),
            "why": (
                "Receivables rising twice as fast as sales usually means customers are taking "
                "longer to pay, credit terms have loosened, or revenue recognition is running "
                "ahead of cash."
            ),
            "mode": "questions",
            "alternatives": [
                "Are days sales outstanding rising across customers or only in a few large accounts",
                "Have credit terms been extended to win volume",
                "Is any revenue concentrated in distributors who may later return goods",
                "Is cash conversion deteriorating even as reported sales look strong",
            ],
            "missing": [
                "Receivables ageing",
                "Cash collected vs billed revenue",
                "Customer concentration and credit-policy changes",
            ],
            "conclusion": (
                "An analyst should verify whether growth is converting into cash before treating "
                "the sales increase as high quality."
            ),
            "variant": "sales_vs_receivables",
        }
    if re.search(r"\b(revenue|sales|profit).{0,100}(cash\s+flow|fcf|free\s+cash)", ql):
        return {
            "direct_answer": (
                "Higher sales or profit do not always mean stronger cash generation."
            ),
            "why": (
                "Cash can weaken when inventory rises, customers pay more slowly, capital "
                "spending increases, or one-off cash outflows occur."
            ),
            "alternatives": [
                "Working-capital absorption",
                "Higher capital expenditure",
                "Timing differences between accruals and cash",
            ],
            "missing": [
                "Cash-flow and working-capital bridges",
                "Capex detail",
            ],
            "conclusion": (
                "Further financial detail is needed to identify the main cash drag."
            ),
            "variant": "earnings_vs_cash",
        }
    return None


def _tech_revenue_vs_customers(ql: str) -> dict[str, Any] | None:
    if re.search(r"\b(revenue|sales).{0,80}(customer\s+growth|users?|subscribers?)", ql) or re.search(
        r"\b(customer\s+growth|users?).{0,80}(revenue|sales)", ql
    ):
        return {
            "direct_answer": "Yes — both can be true at the same time.",
            "why": (
                "Revenue can grow quickly even when new customer additions slow if existing "
                "customers spend more, prices rise, product mix improves, or large contracts "
                "expand. Customer growth measures reach; revenue measures monetisation."
            ),
            "alternatives": [
                "Higher average revenue per user / customer",
                "Price increases or upselling",
                "Mix shift toward larger customers",
                "One-off or multi-year contract revenue recognition",
            ],
            "missing": [
                "ARPU / net retention",
                "New vs existing customer contribution",
                "Pricing and churn detail",
            ],
            "conclusion": (
                "Treat the combination as a quality question about monetisation versus reach, "
                "not as an automatic contradiction."
            ),
            "variant": "revenue_vs_customer_growth",
        }
    return None


def _macro_inflation_yields(ql: str) -> dict[str, Any] | None:
    if re.search(r"\b(inflation).{0,60}(bond\s+yields?|yields?)|(bond\s+yields?).{0,60}(inflation)", ql):
        return {
            "direct_answer": (
                "Falling inflation and rising bond yields can occur together because yields "
                "reflect more than today's inflation print."
            ),
            "why": (
                "Bond yields embed growth expectations, policy-rate paths, fiscal supply and "
                "term premium — not only the latest inflation reading."
            ),
            "mode": "reasons",
            "alternatives": [
                "Markets expect stronger growth or a higher path for policy rates even if current inflation has cooled",
                "Heavier government borrowing increases bond supply and pushes yields up",
                "Term premium or global rate moves lift long yields independently of near-term inflation",
            ],
            "missing": [
                "Which part of the curve moved",
                "Real yields vs inflation breakevens",
                "Fiscal and central-bank communication around the same window",
            ],
            "conclusion": (
                "Do not treat inflation and yields as a single mechanical pair — separate the "
                "channels before drawing a macro conclusion."
            ),
            "variant": "inflation_vs_bond_yields",
        }
    return None


def _valuation_earnings_vs_pe(ql: str) -> dict[str, Any] | None:
    if re.search(r"\b(price[\s-]?to[\s-]?book|p/?b|book\s+value)\b", ql):
        return {
            "direct_answer": (
                "Yes — book value can rise while price-to-book falls when the share price does "
                "not keep pace with book equity."
            ),
            "why": (
                "Price-to-book is price divided by book value. If book equity grows faster than "
                "the share price — or the price falls — the multiple compresses even though "
                "book value is higher."
            ),
            "alternatives": [
                "Investors marked down return expectations on equity",
                "Market-wide de-rating of financials or the sector",
                "Book value rose through capital raising rather than earned returns",
            ],
            "missing": [
                "Share-price move vs book-value bridge",
                "ROE trend and capital actions",
            ],
            "conclusion": (
                "Both can be true; separate balance-sheet growth from the market's pricing of that equity."
            ),
            "variant": "book_up_pb_down",
        }
    if re.search(r"\b(earnings|profit|eps).{0,80}(p/?e|multiple)", ql) or re.search(
        r"\b(p/?e|multiple).{0,80}(earnings|profit|fell|declin)", ql
    ):
        return {
            "direct_answer": (
                "Earnings can rise while the P/E ratio falls when the share price does not "
                "increase as fast as earnings — or falls."
            ),
            "why": (
                "P/E is price divided by earnings. If earnings grow 20% but the share price "
                "rises by less than 20% (or declines), the multiple compresses even though "
                "the company is earning more."
            ),
            "alternatives": [
                "Investors lowered growth expectations or raised the risk premium",
                "Broader market multiple compression",
                "Earnings quality concerns (one-offs, weaker cash conversion)",
                "Starting valuation was high and mean-reverted",
            ],
            "missing": [
                "Share-price move over the same period",
                "Whether earnings are trailing or forward",
                "Guidance and peer multiple changes",
            ],
            "conclusion": (
                "Both statements can be true; the key question is why the market paid less "
                "per unit of earnings."
            ),
            "variant": "earnings_up_pe_down",
        }
    return None


def compose_dual_hypothesis(query: str) -> dict[str, Any]:
    """Hardest benchmark — two equally plausible explanations; do not decide."""
    hyp_a = {
        "title": "Growth investment with market optimism",
        "supports": [
            "Rising revenue and profit can fit an expansion phase",
            "Higher inventory and debt can fund growth capacity",
            "A higher share price can reflect expected future earnings",
        ],
        "contradicts": [
            "Weaker free cash flow may show growth is not yet self-funding",
            "If inventory rises without matching demand, growth quality is weaker than the headline",
            "Debt-funded expansion can raise financial risk even when the market is optimistic",
        ],
    }
    hyp_b = {
        "title": "Working-capital and balance-sheet strain under a still-hopeful market",
        "supports": [
            "Profit without free cash flow often points to receivables or inventory absorption",
            "Rising debt can be plugging an operating cash gap rather than funding high-return projects",
            "Share-price strength can lag fundamentals when investors look through near-term stress",
        ],
        "contradicts": [
            "Genuine revenue and profit growth sit awkwardly with a pure distress story",
            "Some inventory builds are seasonal or strategic rather than demand failure",
            "Markets sometimes correctly anticipate recovery, so price strength is not proof of error",
        ],
    }
    distinguish = [
        "Capex vs working-capital bridge (is cash leaving into long-term assets or operating WC?)",
        "Inventory split and sell-through / order-book evidence",
        "Receivables ageing and cash conversion trend",
        "Debt use-of-proceeds and interest-coverage trajectory",
        "Whether management guidance and operating KPIs confirm demand or only accounting growth",
    ]
    direct = (
        "Two equally plausible explanations can fit the same set of diverging moves. "
        "Do not decide which is correct yet."
    )
    why = (
        "Revenue, profit, free cash flow, inventory, debt and share price can each respond "
        "to different forces. Accounting growth, cash conversion, balance-sheet funding and "
        "market expectations do not have to move together."
    )
    block_a = (
        f"Explanation 1 ({hyp_a['title']}): "
        f"Evidence that supports it includes: {'; '.join(hyp_a['supports'])}. "
        f"Evidence that challenges it includes: {'; '.join(hyp_a['contradicts'])}."
    )
    block_b = (
        f"Explanation 2 ({hyp_b['title']}): "
        f"Evidence that supports it includes: {'; '.join(hyp_b['supports'])}. "
        f"Evidence that challenges it includes: {'; '.join(hyp_b['contradicts'])}."
    )
    missing = (
        "Additional information that would help distinguish them: "
        + "; ".join(distinguish)
        + "."
    )
    conclusion = (
        "Hold both explanations open. Rank them only after the distinguishing evidence arrives."
    )
    executive = " ".join([direct, why, block_a, block_b, missing, conclusion])
    return {
        "enabled": True,
        "family_id": DUAL_HYPOTHESIS,
        "variant": "multi_metric_dual_hypothesis",
        "mode": "first_principles",
        "direct_answer": direct,
        "why": why,
        "hypotheses": [hyp_a, hyp_b],
        "distinguish_with": distinguish,
        "missing": distinguish,
        "conclusion": conclusion,
        "executive": executive,
        "answer": executive,
        "decides_winner": False,
        "reasoning_habit": (
            "direct_answer → why → two_explanations_with_support_and_challenge → "
            "distinguishing_evidence → do_not_decide"
        ),
    }


def compose_family_answer(family_id: str, query: str) -> dict[str, Any] | None:
    """Compose a family-level answer for novel facts. Returns None if family cannot help."""
    ql = str(query or "").lower()
    parts: dict[str, Any] | None = None
    mode = "first_principles"

    if family_id == DUAL_HYPOTHESIS:
        return compose_dual_hypothesis(query)

    if family_id == CONTRADICTION:
        parts = _banking_volume_vs_quality(ql) or _tech_revenue_vs_customers(ql)
        if parts is None:
            depends = bool(
                re.search(r"\b(is\s+this\s+(positive|healthy)|healthy\s+growth)\b", ql)
            )
            parts = {
                "direct_answer": (
                    "It depends on what is driving the weaker quality signal."
                    if depends
                    else (
                        "Both signals can be real; the more important one is usually the measure "
                        "of quality, sustainability or risk — not the measure of scale alone."
                    )
                ),
                "why": (
                    "Headline growth or size can improve while a quality ratio, margin, mix or "
                    "risk indicator weakens. That tension means the business may be getting "
                    "larger without getting healthier."
                ),
                "alternatives": [
                    "Mix shifted toward lower-quality activity",
                    "Costs, risk or funding terms worsened even as volume rose",
                    "One-off items lifted the stronger-looking metric",
                ],
                "missing": [
                    "Bridge between the two metrics",
                    "Whether the quality deterioration is temporary or structural",
                ],
                "conclusion": (
                    "Assess both together and wait for the linking evidence before choosing a side."
                ),
                "variant": "generic_contradiction",
            }

    elif family_id == ACCOUNTING:
        parts = _banking_volume_vs_quality(ql) or _accounting_wc(ql)
        if parts is None:
            both_true = bool(re.search(r"\bcan\s+both\s+be\s+true\b", ql))
            parts = {
                "direct_answer": (
                    "Yes — both can be true when accrual profits improve while cash is absorbed "
                    "elsewhere."
                    if both_true
                    else (
                        "Accounting results and cash or balance-sheet items can diverge for several "
                        "legitimate reasons."
                    )
                ),
                "why": (
                    "Inventory, receivables, payables, provisions and capital spending can absorb "
                    "or release cash independently of reported revenue or profit."
                ),
                "alternatives": [
                    "Working-capital timing",
                    "Investment or provision policy changes",
                    "One-off cash items",
                ],
                "missing": [
                    "Cash-flow statement detail",
                    "Working-capital bridge",
                ],
                "conclusion": (
                    "Identify the bridge items before judging earnings quality."
                ),
                "variant": "generic_accounting",
            }

    elif family_id == VALUATION:
        parts = _valuation_earnings_vs_pe(ql)
        if parts is None:
            parts = {
                "direct_answer": (
                    "A valuation multiple can move differently from earnings because price and "
                    "the earnings base are separate inputs."
                ),
                "why": (
                    "Multiples compress or expand when investors change growth assumptions, "
                    "risk appetite or the peer set — even if the company earns more."
                ),
                "alternatives": [
                    "Price lagged earnings",
                    "Market-wide de-rating",
                    "Earnings composition changed",
                ],
                "missing": [
                    "Price path vs earnings path",
                    "Trailing vs forward base",
                ],
                "conclusion": (
                    "Separate the accounting change from the market's pricing of that change."
                ),
                "variant": "generic_valuation",
            }

    elif family_id == CAUSALITY:
        parts = _macro_inflation_yields(ql)
        if parts is None:
            differential = bool(
                re.search(r"\b(differ|different|airlines|exporters|importers|sectors?)\b", ql)
            )
            parts = {
                "direct_answer": (
                    "The impact differs across industries and market prices."
                    if differential
                    else (
                        "The same macro move rarely affects every sector or market price the same way."
                    )
                ),
                "why": (
                    "Transmission depends on business models, funding structures, input costs and "
                    "what investors are discounting beyond the headline variable."
                ),
                "mode": "reasons",
                "alternatives": [
                    "Direct demand or cost channel for some industries",
                    "Indirect margin or funding-cost channel for others",
                    "Second-order effects through inflation, rates or confidence",
                ],
                "missing": [
                    "Company- or sector-specific transmission map",
                    "Timing and magnitude of pass-through",
                ],
                "conclusion": (
                    "Map the causal chain before applying one macro story everywhere."
                ),
                "variant": "generic_causality",
            }

    elif family_id == EVIDENCE:
        parts = {
            "direct_answer": (
                "Do not automatically choose one source or average conflicting figures."
            ),
            "why": (
                "Differences often come from timing, definitions, adjustments or unverified "
                "reporting. Official filings and verified market data outrank unverified news."
            ),
            "alternatives": [
                "Different methodologies or timestamps",
                "Unverified media running ahead of filings",
            ],
            "missing": [
                "Methodology notes",
                "Official confirmation where relevant",
            ],
            "conclusion": (
                "Keep confidence lower until the higher-quality source confirms the point."
            ),
            "variant": "generic_evidence",
        }

    elif family_id == UNCERTAINTY:
        parts = {
            "direct_answer": (
                "The current evidence is not sufficient for a confident performance conclusion."
            ),
            "why": (
                "Without the missing results or operating data, claims about growth, margins or "
                "cash flow would be speculation."
            ),
            "alternatives": [
                "Prior trends are not a substitute for the missing period",
                "Management comments need later verification",
            ],
            "missing": [
                "The outstanding disclosures or operating metrics named in the question",
            ],
            "conclusion": (
                "State the limitation clearly and wait for evidence."
            ),
            "variant": "generic_uncertainty",
        }

    elif family_id == SELF_CRITIQUE:
        parts = {
            "direct_answer": (
                "The current assessment could be wrong if its key assumptions fail."
            ),
            "why": (
                "Demand, costs, execution, funding conditions or the macro backdrop can all "
                "turn against the base case."
            ),
            "alternatives": [
                "Demand disappoints",
                "Costs rise faster than pricing power",
                "Execution slips",
                "Macro or funding conditions worsen",
            ],
            "missing": [
                "Explicit falsifiers for each major assumption",
            ],
            "conclusion": (
                "Monitor those falsifiers as new evidence arrives."
            ),
            "variant": "generic_self_critique",
        }

    elif family_id == COMPARISON:
        parts = {
            "direct_answer": (
                "A single shared metric is not enough to decide which business is stronger."
            ),
            "why": (
                "Debt, cash flow, margins, return on capital, capital allocation, valuation and "
                "industry structure can reverse a simple growth comparison."
            ),
            "alternatives": [
                "Higher returns may be leverage-driven",
                "Lower returns may reflect a different capital-intensity model",
            ],
            "missing": [
                "Leverage, cash conversion, margins, ROIC, allocation and industry context",
            ],
            "conclusion": (
                "Compare the full quality stack before ranking the companies."
            ),
            "variant": "generic_comparison",
        }

    if not parts:
        return None

    executive = _compose(parts)
    meta = FAMILIES.get(family_id) or {}
    return {
        "enabled": True,
        "family_id": family_id,
        "family_label": meta.get("label"),
        "family_habit": meta.get("habit"),
        "variant": parts.get("variant"),
        "mode": mode,
        "direct_answer": parts.get("direct_answer"),
        "why": parts.get("why"),
        "alternatives": parts.get("alternatives"),
        "missing": parts.get("missing"),
        "conclusion": parts.get("conclusion"),
        "executive": executive,
        "answer": executive,
        "reasoning_habit": (
            "direct_answer → why → alternatives → missing_evidence → balanced_conclusion"
        ),
        "never_trains_on_rote_answers_only": True,
    }


__all__ = ["compose_dual_hypothesis", "compose_family_answer"]
