"""Contradiction archetypes — institutional reasoning patterns (not invented facts)."""

from __future__ import annotations

import re
from typing import Any

Archetype = dict[str, Any]

ARCHETYPES: list[Archetype] = [
    {
        "id": "profit_vs_nim",
        "match": re.compile(
            r"(profit|earnings).{0,80}(nim|net\s+interest\s+margin)|(nim|net\s+interest\s+margin).{0,80}(profit|earnings)",
            re.I | re.S,
        ),
        "facts": [
            "Reported profit / earnings moved higher.",
            "Net Interest Margin (NIM) declined.",
        ],
        "conflict": True,
        "direct_answer": (
            "The decline in Net Interest Margin (NIM) is the more important signal "
            "because it measures how profitable the bank's core lending business is."
        ),
        "why": (
            "Higher profit can be influenced by one-time gains or lower expenses, "
            "whereas NIM reflects the bank's ability to consistently earn from lending."
        ),
        "explanations": [
            "One-off gains or lower costs may lift reported profit without improving core lending profitability.",
            "Funding costs may have risen faster than lending yields, compressing NIM.",
            "Loan mix may have shifted toward lower-yielding assets.",
            "Deposit mix may have become more expensive, raising the cost of funds.",
        ],
        "missing_evidence": [
            "Breakdown of profit drivers (core vs one-off / treasury / cost cuts)",
            "NIM bridge: yield on advances vs cost of funds",
            "Loan and deposit mix disclosures for the quarter",
            "Commentary on whether margin pressure is temporary or structural",
        ],
        "conclusion": (
            "Both metrics should be considered together before drawing a conclusion. "
            "Based on the available evidence, margin pressure appears to be the more significant development."
        ),
        "confidence": "medium",
        "strongest_explanation": (
            "NIM is a cleaner read on core lending profitability than headline profit alone."
        ),
    },
    {
        "id": "revenue_vs_fcf",
        "match": re.compile(
            r"(revenue|sales).{0,100}(free\s+cash\s+flow|fcf)|(free\s+cash\s+flow|fcf).{0,100}(revenue|sales)",
            re.I | re.S,
        ),
        "facts": [
            "Revenue / sales increased.",
            "Free cash flow declined.",
        ],
        "conflict": True,
        "direct_answer": (
            "The two numbers can move in opposite directions because higher sales "
            "do not always mean more cash."
        ),
        "why": (
            "Free cash flow may decline if the company spends more on expansion, "
            "invests in inventory, waits longer to collect payments from customers, "
            "or increases capital expenditure."
        ),
        "explanations": [
            "Working capital rose (inventory build or slower collections from customers).",
            "Capital expenditure increased to support growth.",
            "Cash was used for expansion or other investing needs.",
            "Reported sales include accruals that have not yet turned into cash.",
        ],
        "missing_evidence": [
            "Cash-flow statement detail (operating vs investing cash)",
            "Working-capital bridge (inventory, receivables, payables)",
            "Capex vs depreciation for the period",
            "Whether the sales growth was cash-collected or accrual-heavy",
        ],
        "conclusion": (
            "More evidence is needed to identify the main reason in this case. "
            "The contradiction does not by itself prove the business is weaker — "
            "it shows cash generation and reported sales are telling different stories right now."
        ),
        "confidence": "low_to_medium",
        "strongest_explanation": (
            "Cash needs (working capital or capex) likely grew faster than sales converted to cash."
        ),
    },
    {
        "id": "management_vs_sales",
        "match": re.compile(
            r"(management|guidance|commentary|says|said|claimed|demand).{0,120}"
            r"(sales|revenue).{0,40}(declin|fell|down|drop)|(sales|revenue).{0,40}"
            r"(declin|fell|down|drop).{0,120}(management|guidance|demand|says|said)",
            re.I | re.S,
        ),
        "facts": [
            "Management commentary points to strong demand.",
            "Reported sales declined.",
        ],
        "conflict": True,
        "direct_answer": (
            "The financial results should generally carry more weight than management comments "
            "because they reflect actual performance."
        ),
        "why": (
            "However, lower sales do not automatically mean demand is weak. "
            "Reported sales are an outcome; demand commentary may refer to enquiries, "
            "pipelines, or conditions that have not yet converted into billed sales."
        ),
        "explanations": [
            "Orders were delayed and will show up in later periods.",
            "Pricing changes reduced sales value even if volumes were steadier.",
            "Product mix shifted toward lower-priced items.",
            "Seasonal or one-off timing effects reduced the current period's sales.",
        ],
        "missing_evidence": [
            "Volume vs price vs mix bridge for sales",
            "Order book / pipeline disclosures",
            "Channel inventory and sell-through data where relevant",
            "Management clarification linking demand comments to the sales decline",
        ],
        "conclusion": (
            "Additional evidence is needed before reaching a firm conclusion. "
            "Treat the sales decline as the harder fact, and treat demand commentary "
            "as a claim that still needs to be reconciled with the numbers."
        ),
        "confidence": "medium",
        "strongest_explanation": (
            "Numbers outweigh commentary until volume, price, mix or timing evidence reconciles the gap."
        ),
    },
]


def match_archetype(query: str) -> Archetype | None:
    text = str(query or "")
    for arch in ARCHETYPES:
        if arch["match"].search(text):
            return arch
    return None


def generic_archetype(query: str) -> Archetype:
    return {
        "id": "generic_conflict",
        "facts": [
            "The question presents two observations that appear to conflict.",
        ],
        "conflict": True,
        "direct_answer": (
            "The two observations can both be true if they measure different things "
            "or cover different parts of the business."
        ),
        "why": (
            "Apparent contradictions often arise when one figure is a headline result "
            "and the other reflects underlying quality, cash, or timing."
        ),
        "explanations": [
            "The metrics may cover different scopes or time periods.",
            "One metric may include one-off items the other excludes.",
            "Timing differences can separate reported results from underlying conditions.",
            "Accounting recognition can diverge from economic or cash reality.",
        ],
        "missing_evidence": [
            "Clear definitions and time periods for each metric",
            "A bridge explaining how one figure moves relative to the other",
            "Segment or mix detail that could reconcile the tension",
            "Management or disclosure notes addressing the conflict",
        ],
        "conclusion": (
            "More evidence is needed before choosing one signal over the other. "
            "The current conclusion is that the conflict is real enough to investigate, "
            "not yet resolved."
        ),
        "confidence": "low",
        "strongest_explanation": (
            "Without a metric bridge, the safest read is that the signals conflict and need reconciliation."
        ),
        "query_echo": query,
    }
