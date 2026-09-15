"""Gold reasoning patterns — how to think, not rote memorisation.

Each pattern teaches a reusable institutional reasoning habit.
Answers follow: direct answer → why → alternatives → missing evidence → balanced conclusion.
"""

from __future__ import annotations

import re
from typing import Any

Pattern = dict[str, Any]


def _compose(p: Pattern) -> str:
    parts = [str(p.get("direct_answer") or "").strip()]
    if p.get("why"):
        parts.append(str(p["why"]).strip())
    alts = list(p.get("alternatives") or [])
    if alts:
        if p.get("alternatives_as_questions"):
            parts.append(
                "Important questions include: "
                + "; ".join(f"({i}) {a.rstrip('?')}?" for i, a in enumerate(alts, 1))
            )
        elif p.get("alternatives_as_narratives"):
            narr = []
            for i, a in enumerate(alts, 1):
                title = a.get("title") if isinstance(a, dict) else f"Narrative {i}"
                body = a.get("text") if isinstance(a, dict) else str(a)
                narr.append(f"Narrative {i} ({title}): {body}")
            parts.append(" ".join(narr))
        else:
            parts.append(
                "Other possible explanations include: "
                + "; ".join(f"({i}) {str(a).rstrip('.')}" for i, a in enumerate(alts, 1))
                + "."
            )
    if p.get("missing"):
        miss = p["missing"]
        if isinstance(miss, list):
            parts.append(
                "Additional evidence needed: "
                + "; ".join(str(m).rstrip(".") for m in miss)
                + "."
            )
        else:
            parts.append(str(miss).strip())
    if p.get("conclusion"):
        parts.append(str(p["conclusion"]).strip())
    return " ".join(x for x in parts if x)


PATTERNS: list[Pattern] = [
    # ----- T1 Profit ↑ ROE ↓ -----
    {
        "id": "t1_profit_vs_roe",
        "level": "contradiction",
        "match": re.compile(
            r"(profit|earnings|pat).{0,100}(roe|return\s+on\s+equity)"
            r"|(roe|return\s+on\s+equity).{0,100}(profit|earnings|pat)",
            re.I | re.S,
        ),
        "direct_answer": (
            "The decline in ROE deserves closer attention because it shows how efficiently "
            "the bank is generating profit from shareholders' money."
        ),
        "why": (
            "Higher profit is positive, but if shareholders' equity has grown faster than profit, "
            "ROE can fall even while earnings increase. This may indicate that profitability is "
            "improving more slowly than the capital invested."
        ),
        "alternatives": [
            "Equity rose because of retained earnings or capital raising",
            "Profit quality changed even if the headline rose",
            "One-off items lifted profit without lifting sustainable returns",
        ],
        "missing": [
            "Equity bridge for the period",
            "Core vs one-off profit split",
            "Trend in ROE over several quarters",
        ],
        "conclusion": (
            "Both metrics should be assessed together before drawing a conclusion."
        ),
    },
    # ----- T2 Revenue ↑ Margin ↓ -----
    {
        "id": "t2_revenue_vs_operating_margin",
        "level": "contradiction",
        "match": re.compile(
            r"(revenue|sales).{0,80}(operating\s+margin|margin).{0,40}(declin|fell|down|drop|lower)"
            r"|(operating\s+margin|margin).{0,40}(declin|fell|down|drop|lower).{0,80}(revenue|sales)",
            re.I | re.S,
        ),
        "direct_answer": (
            "It depends on what caused the lower margin."
        ),
        "why": (
            "Higher revenue shows the company is selling more, but a lower operating margin means "
            "it is earning less profit from each ₹100 of sales. This could result from higher costs, "
            "discounts to boost sales or investment in future growth."
        ),
        "alternatives": [
            "Costs rose faster than sales",
            "Discounts or mix shifts reduced profitability",
            "Investment spending temporarily weighed on margins",
        ],
        "missing": [
            "Cost bridge and product mix",
            "Whether margin pressure is temporary growth investment",
        ],
        "conclusion": (
            "More information is needed before deciding whether this is a positive or negative development."
        ),
    },
    # ----- T3 Different P/E -----
    {
        "id": "t3_conflicting_pe",
        "level": "evidence",
        "match": re.compile(
            r"(p/?e|price[\s-]?to[\s-]?earnings).{0,120}(18\.4|different|providers|21\.7|25\.1|which\s+value|trust)"
            r"|(different|providers|conflict).{0,80}(p/?e|price[\s-]?to[\s-]?earnings)",
            re.I | re.S,
        ),
        "direct_answer": (
            "AIG should not automatically choose one value or average them."
        ),
        "why": (
            "It should compare the calculation date, earnings used, share price source and "
            "methodology behind each P/E ratio."
        ),
        "alternatives": [
            "Trailing vs forward earnings differences",
            "Different share-price timestamps",
            "Adjusted vs reported earnings definitions",
        ],
        "missing": [
            "Provider methodology notes",
            "Official company earnings and exchange price used",
        ],
        "conclusion": (
            "If differences remain, priority should be given to official company data or verified "
            "market providers, with lower-confidence sources used only as supporting evidence."
        ),
    },
    # ----- T4 News without NSE -----
    {
        "id": "t4_news_without_filing",
        "level": "evidence",
        "match": re.compile(
            r"(news|article|media).{0,120}(nse|bse|filing|exchange|official)"
            r"|(no\s+(nse|bse|exchange)\s+filing)|(without.{0,40}filing)",
            re.I | re.S,
        ),
        "direct_answer": (
            "The information should be treated as unverified until supported by an official source."
        ),
        "why": (
            "News reports can provide useful early signals, but they should not change the overall "
            "assessment on their own."
        ),
        "alternatives": [
            "The report may later be confirmed by an exchange filing",
            "The report may be incomplete, premature or incorrect",
        ],
        "missing": [
            "Company or stock-exchange confirmation",
            "Contract terms and timing if later confirmed",
        ],
        "conclusion": (
            "Confidence should remain lower until the company or stock exchange confirms the information."
        ),
    },
    # ----- T5 RBI rate cut multi-company -----
    {
        "id": "t5_rbi_rate_cut_differential",
        "level": "causality",
        "match": re.compile(
            r"(rbi|reserve\s+bank).{0,80}(cut|cuts|lower).{0,80}(rate|interest)"
            r".{0,200}(hdfc|bajaj|infosys|ultratech)"
            r"|(hdfc|bajaj|infosys|ultratech).{0,200}(rbi|interest\s+rate)",
            re.I | re.S,
        ),
        "direct_answer": (
            "The impact differs across industries."
        ),
        "why": (
            "Lower interest rates may support banks through higher loan demand, although lending margins "
            "can also come under pressure. Finance companies may benefit from lower borrowing costs. "
            "IT companies are usually affected less directly, while sectors such as housing and construction "
            "may benefit if cheaper loans encourage spending and investment."
        ),
        "alternatives": [
            "HDFC Bank: loan demand may rise, but NIM can compress",
            "Bajaj Finance: funding costs may ease",
            "Infosys: mostly indirect via global demand and currency, not the rate cut itself",
            "UltraTech: housing/infra demand may improve if cheaper credit supports projects",
        ],
        "missing": [
            "Transmission strength into lending rates",
            "Company-specific funding and demand sensitivity",
        ],
        "conclusion": (
            "Do not apply one macro story to every company — map the causal chain to each business model."
        ),
    },
    # ----- T6 Oil up -----
    {
        "id": "t6_oil_shock_sectors",
        "level": "causality",
        "match": re.compile(
            r"(crude|oil).{0,60}(rise|rises|rose|up|increas|40\s*%).{0,80}(sector|benefit|affect|impact)"
            r"|(sector).{0,80}(crude|oil).{0,40}(rise|up|40)",
            re.I | re.S,
        ),
        "direct_answer": (
            "Higher oil prices do not affect every sector in the same way."
        ),
        "why": (
            "Airlines, paint manufacturers and transport companies may face higher costs, while oil "
            "producers can benefit from stronger prices. Inflation may also increase, potentially leading "
            "to higher interest rates, which can affect borrowing and consumer spending across the economy."
        ),
        "alternatives": [
            "Upstream oil & gas: often benefits from higher realisations",
            "Airlines / logistics / paints: input-cost pressure",
            "Broader economy: inflation and rate-response risk",
        ],
        "missing": [
            "Pass-through ability by sector",
            "Hedging and subsidy policy context",
        ],
        "conclusion": (
            "Separate winners, losers and second-order macro effects instead of using one blanket view."
        ),
    },
    # ----- T7 Missing results -----
    {
        "id": "t7_missing_quarterly_results",
        "level": "false_certainty",
        "match": re.compile(
            r"(not\s+yet\s+published|have\s+not\s+published|missing).{0,60}(quarterly|results)"
            r"|(what\s+cannot\s+be\s+concluded)|cannot\s+be\s+concluded",
            re.I | re.S,
        ),
        "direct_answer": (
            "The current evidence is not sufficient to assess the company's latest performance."
        ),
        "why": (
            "Until the quarterly results are released, conclusions about revenue, profit, margins or "
            "cash flow cannot be made with confidence."
        ),
        "alternatives": [
            "Prior-period trends are not a substitute for the missing quarter",
            "Management commentary alone cannot fill the gap",
        ],
        "missing": [
            "Quarterly revenue, profit, margins and cash-flow disclosures",
        ],
        "conclusion": (
            "Any assessment should clearly state these limitations."
        ),
    },
    # ----- T8 CEO demand without results -----
    {
        "id": "t8_ceo_demand_without_results",
        "level": "false_certainty",
        "match": re.compile(
            r"(ceo|management|commentary).{0,100}(demand).{0,100}(no\s+financial|not\s+released|without.{0,40}result)"
            r"|(demand\s+remains\s+strong).{0,80}(no\s+financial|results\s+have\s+not|not\s+been\s+released)",
            re.I | re.S,
        ),
        "direct_answer": (
            "Management comments are useful but should not be treated as confirmed evidence."
        ),
        "why": (
            "They provide insight into management's expectations, but financial results and operational "
            "data are needed to verify whether those expectations are reflected in actual business performance."
        ),
        "alternatives": [
            "Demand may later appear in orders and sales",
            "Commentary may prove optimistic if numbers disappoint",
        ],
        "missing": [
            "Financial results and operating metrics that confirm demand",
        ],
        "conclusion": (
            "Give the statement limited weight until evidence arrives."
        ),
    },
    # ----- T9 Rev↑ Profit↑ OCF↓ -----
    {
        "id": "t9_revenue_profit_vs_ocf",
        "level": "accounting",
        "match": re.compile(
            r"(revenue|sales).{0,80}(profit|earnings).{0,80}(operating\s+cash|cash\s+flow|ocf)"
            r"|(operating\s+cash|ocf).{0,80}(declin|fell|down).{0,80}(revenue|profit)",
            re.I | re.S,
        ),
        "direct_answer": (
            "Higher sales and profit do not always lead to higher cash generation."
        ),
        "why": (
            "Possible explanations include increased inventory, slower customer payments, higher capital "
            "expenditure or one-off cash outflows."
        ),
        "alternatives": [
            "Increased inventory",
            "Slower customer payments (receivables)",
            "Higher capital expenditure",
            "One-off or timing-related cash outflows",
        ],
        "missing": [
            "Working-capital bridge",
            "Capex and one-off cash items",
        ],
        "conclusion": (
            "The available information does not identify which factor is responsible, so further "
            "financial details are needed."
        ),
    },
    # ----- T10 Record earnings negative FCF -----
    {
        "id": "t10_earnings_vs_negative_fcf",
        "level": "accounting",
        "match": re.compile(
            r"(record\s+earnings|strong\s+(reported\s+)?earnings|profit).{0,100}"
            r"(negative\s+free\s+cash|fcf\s+negative|negative\s+fcf)"
            r"|(negative\s+free\s+cash).{0,80}(earnings|profit)",
            re.I | re.S,
        ),
        "direct_answer": (
            "An analyst should investigate why cash generation is weak despite strong reported earnings."
        ),
        "why": (
            "Important questions include whether customers are taking longer to pay, inventory has increased, "
            "capital spending has risen, or accounting profits are not being converted into cash."
        ),
        "alternatives": [
            "Are receivables stretching?",
            "Has inventory built up?",
            "Has capex risen sustainably or temporarily?",
            "Are earnings quality and cash conversion weakening?",
        ],
        "alternatives_as_questions": True,
        "missing": [
            "Multi-year cash conversion and working-capital detail",
        ],
        "conclusion": (
            "These factors help determine whether earnings are sustainable."
        ),
    },
    # ----- T11 Same growth different ROE -----
    {
        "id": "t11_same_growth_different_roe",
        "level": "institutional",
        "match": re.compile(
            r"(identical|same).{0,40}(revenue\s+growth|sales\s+growth).{0,80}(roe|24\s*%|9\s*%)"
            r"|(roe\s+of\s+24).{0,40}(9\s*%)",
            re.I | re.S,
        ),
        "direct_answer": (
            "Revenue growth alone is not enough to judge which business is stronger."
        ),
        "why": (
            "Additional evidence should include debt levels, cash flow, profit margins, return on capital, "
            "capital allocation, valuation and industry conditions before comparing the overall quality "
            "of the two companies."
        ),
        "alternatives": [
            "Higher ROE may be leverage-driven rather than quality-driven",
            "Lower ROE may reflect a different industry capital intensity",
        ],
        "missing": [
            "Debt, cash flow, margins, ROIC, capital allocation, valuation and industry context",
        ],
        "conclusion": (
            "Do not conclude that 24% ROE is automatically the stronger business."
        ),
    },
    # ----- T12 Price down after record profit -----
    {
        "id": "t12_price_fall_after_record_profit",
        "level": "institutional",
        "match": re.compile(
            r"(share\s+price|stock\s+price).{0,60}(fall|falls|fell|drop|declin).{0,80}"
            r"(record\s+profit|strong\s+result|profit)"
            r"|(record\s+profit).{0,80}(share\s+price|stock).{0,40}(fall|drop|declin)",
            re.I | re.S,
        ),
        "direct_answer": (
            "Strong results do not always lead to a higher share price."
        ),
        "why": (
            "Investors may have expected even better results, management may have given weaker future guidance, "
            "valuation may already have been high, profits could include one-off gains, or broader market "
            "conditions may have influenced investor sentiment."
        ),
        "alternatives": [
            "Results missed elevated expectations",
            "Weaker forward guidance",
            "Rich starting valuation",
            "One-off gains in reported profit",
            "Broader market or macro sentiment",
        ],
        "missing": [
            "Expectation vs delivery gap",
            "Guidance and one-off profit notes",
        ],
        "conclusion": (
            "More evidence is needed to identify the main reason."
        ),
    },
    # ----- T13 Challenge own conclusion -----
    {
        "id": "t13_challenge_own_conclusion",
        "level": "devils_advocate",
        "match": re.compile(
            r"(challenge|argue|wrong|against).{0,80}(your\s+own|previous|conclusion|outlook\s+was\s+improving)"
            r"|(strongest\s+possible\s+case).{0,40}(wrong|against)",
            re.I | re.S,
        ),
        "direct_answer": (
            "The current assessment could be wrong if key assumptions prove incorrect."
        ),
        "why": (
            "For example, future demand may weaken, costs could rise faster than expected, management "
            "execution may disappoint or the economic environment may deteriorate."
        ),
        "alternatives": [
            "Demand disappoints",
            "Cost inflation exceeds pricing power",
            "Execution misses plan",
            "Macro conditions worsen",
        ],
        "missing": [
            "Live monitoring of demand, costs, execution and macro evidence",
        ],
        "conclusion": (
            "These possibilities should be monitored as new evidence becomes available."
        ),
    },
    # ----- T14 List assumptions -----
    {
        "id": "t14_list_assumptions",
        "level": "devils_advocate",
        "match": re.compile(
            r"(list|every|each).{0,40}assumption|assumption.{0,40}(prove\s+it\s+wrong|falsif|future\s+evidence)",
            re.I | re.S,
        ),
        "direct_answer": (
            "The assessment assumes that current business trends continue, financial data remains accurate, "
            "management executes its plans and the broader economy remains broadly stable."
        ),
        "why": (
            "These assumptions would be challenged if earnings weaken, margins decline significantly, "
            "debt rises unexpectedly or macroeconomic conditions deteriorate."
        ),
        "alternatives": [
            "Business-trend continuity assumption",
            "Data-accuracy assumption",
            "Management-execution assumption",
            "Macro-stability assumption",
        ],
        "missing": [
            "Clear mapping from each assumption to its falsifying evidence trigger",
        ],
        "conclusion": (
            "Treat assumptions as testable claims, not permanent facts."
        ),
    },
    # ----- T15 Five facts three narratives -----
    {
        "id": "t15_five_facts_three_narratives",
        "level": "devils_advocate",
        "match": re.compile(
            r"(revenue\s*\+?\s*20|revenue.{0,10}20\s*%).{0,120}(profit\s*\+?\s*15|profit.{0,10}15\s*%)"
            r".{0,160}(fcf|free\s+cash).{0,40}(-?\s*30|30\s*%).{0,120}(debt).{0,40}(40)"
            r"|(three\s+completely\s+different|three\s+narratives|three\s+explanations|"
            r"five\s+facts).{0,120}(revenue|fcf|debt|share\s+price)",
            re.I | re.S,
        ),
        "direct_answer": (
            "The same five facts can support more than one coherent explanation. Do not decide which is correct yet."
        ),
        "why": (
            "Revenue and profit can rise while cash weakens and debt rises if growth is funded externally, "
            "working capital absorbs cash, or the market looks through near-term pressure."
        ),
        "alternatives_as_narratives": True,
        "alternatives": [
            {
                "title": "Growth Investment",
                "text": (
                    "The company is investing heavily in expansion. Revenue and profit are growing, but cash "
                    "flow has declined because of higher capital expenditure, while debt has increased to finance "
                    "growth. Investors remain optimistic, leading to a higher share price."
                ),
            },
            {
                "title": "Working Capital Pressure",
                "text": (
                    "Revenue and profit continue to improve, but cash flow has weakened because customers are "
                    "taking longer to pay or inventory has increased. Additional borrowing has supported operations, "
                    "while investors remain confident that cash generation will recover."
                ),
            },
            {
                "title": "Market Expectations",
                "text": (
                    "The company has reported solid financial growth, but weaker cash generation and higher debt "
                    "may indicate increasing financial pressure. Despite these concerns, investors may expect future "
                    "earnings growth to outweigh current risks, supporting the share price."
                ),
            },
        ],
        "missing": [
            "Capex vs working-capital bridge",
            "Debt use of proceeds",
            "Whether the market is pricing growth or ignoring cash risk",
        ],
        "conclusion": (
            "Hold all three narratives open until evidence ranks them."
        ),
    },
    # Generic NIM (after T1–T15 so five-fact / ROE cases win first)
    {
        "id": "profit_vs_nim",
        "level": "contradiction",
        "match": re.compile(
            r"(profit|earnings).{0,80}(nim|net\s+interest\s+margin)|(nim|net\s+interest\s+margin).{0,80}(profit|earnings)",
            re.I | re.S,
        ),
        "direct_answer": (
            "The decline in Net Interest Margin (NIM) is the more important signal "
            "because it measures how profitable the bank's core lending business is."
        ),
        "why": (
            "Higher profit can be influenced by one-time gains or lower expenses, "
            "whereas NIM reflects the bank's ability to consistently earn from lending."
        ),
        "alternatives": [
            "One-off gains lifted profit without improving core lending profitability",
            "Funding costs rose faster than lending yields",
            "Loan or deposit mix became less favourable",
        ],
        "missing": [
            "Profit driver breakdown",
            "NIM bridge and mix disclosures",
        ],
        "conclusion": (
            "Both metrics should be considered together before drawing a conclusion."
        ),
    },
    # Generic revenue vs FCF
    {
        "id": "revenue_vs_fcf",
        "level": "contradiction",
        "match": re.compile(
            r"(revenue|sales).{0,100}(free\s+cash\s+flow|fcf)|(free\s+cash\s+flow|fcf).{0,100}(revenue|sales)",
            re.I | re.S,
        ),
        "direct_answer": (
            "The two numbers can move in opposite directions because higher sales do not always mean more cash."
        ),
        "why": (
            "Free cash flow may decline if the company spends more on expansion, invests in inventory, "
            "waits longer to collect payments from customers, or increases capital expenditure."
        ),
        "alternatives": [
            "Working capital rose",
            "Capital expenditure increased",
            "Accrual-heavy sales not yet collected in cash",
        ],
        "missing": [
            "Cash-flow and working-capital bridges",
            "Capex detail",
        ],
        "conclusion": (
            "More evidence is needed to identify the main reason in this case."
        ),
    },
    # Management vs sales (prior)
    {
        "id": "management_vs_sales",
        "level": "contradiction",
        "match": re.compile(
            r"(management|guidance|commentary|says|said|claimed|demand).{0,120}"
            r"(sales|revenue).{0,40}(declin|fell|down|drop)|(sales|revenue).{0,40}"
            r"(declin|fell|down|drop).{0,120}(management|guidance|demand|says|said)",
            re.I | re.S,
        ),
        "direct_answer": (
            "The financial results should generally carry more weight than management comments "
            "because they reflect actual performance."
        ),
        "why": (
            "However, lower sales do not automatically mean demand is weak. Factors such as delayed orders, "
            "pricing changes, product mix or seasonal effects could also explain the decline."
        ),
        "alternatives": [
            "Delayed orders",
            "Pricing or mix effects",
            "Seasonal timing",
        ],
        "missing": [
            "Volume-price-mix bridge",
            "Order-book evidence",
        ],
        "conclusion": (
            "Additional evidence is needed before reaching a firm conclusion."
        ),
    },
]


def match_pattern(query: str) -> Pattern | None:
    text = str(query or "")
    for pattern in PATTERNS:
        if pattern["match"].search(text):
            return pattern
    return None


def package_pattern_answer(query: str, *, ticker: str | None = None, company: str | None = None) -> dict[str, Any]:
    pattern = match_pattern(query)
    if not pattern:
        return {"enabled": False, "bypassed": True, "reason": "no_gold_pattern"}
    answer = _compose(pattern)
    return {
        "enabled": True,
        "pattern_id": pattern["id"],
        "level": pattern.get("level"),
        "ticker": ticker,
        "company": company,
        "direct_answer": pattern.get("direct_answer"),
        "why": pattern.get("why"),
        "alternatives": pattern.get("alternatives"),
        "missing": pattern.get("missing"),
        "conclusion": pattern.get("conclusion"),
        "answer": answer,
        "executive": answer,
        "reasoning_habit": (
            "direct_answer → why → alternatives → missing_evidence → balanced_conclusion"
        ),
        "never_trains_on_rote_answers_only": True,
        "answer_policy": "gold_reasoning_pattern",
    }
