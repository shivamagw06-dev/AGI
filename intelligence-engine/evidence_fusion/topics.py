"""Map FIRE-03 business statements to fusible financial topics."""

from __future__ import annotations

import re
from typing import Any

from evidence_fusion.schema import (
    CAT_CAPACITY,
    CAT_CAPITAL,
    CAT_CASH,
    CAT_DEBT,
    CAT_GROWTH,
    CAT_GUIDANCE,
    CAT_MARGIN,
    CAT_MISSING,
    CAT_RISK,
    CAT_STRATEGY,
)

# Each rule: match FIRE-03 facts, then evaluate metric expectations.
# expected: up | down | down_or_flat | up_or_flat | present_positive
TOPIC_RULES: list[dict[str, Any]] = [
    {
        "topic_id": "capacity_expansion",
        "category": CAT_CAPACITY,
        "consistency_bucket": "capital_allocation_consistency",
        "categories": {"Capacity Expansion", "Capital Expenditure"},
        "keywords": (
            r"capacity\s+expansion",
            r"expand(?:ing)?\s+manufacturing",
            r"greenfield\s+capacity",
            r"capex\s+(?:supports?|plan|programme|program)",
        ),
        "claim": "expanding capacity / elevating capex",
        "checks": (
            {"metric": "capex", "expected": "up", "weight": 2},
        ),
        "insufficient_if_no_metrics": True,
    },
    {
        "topic_id": "cash_generation",
        "category": CAT_CASH,
        "consistency_bucket": "financial_consistency",
        "categories": set(),
        "keywords": (
            r"improving\s+cash\s+generation",
            r"cash\s+generation",
            r"cash\s+conversion",
            r"strong(?:er)?\s+cash",
        ),
        "claim": "improving cash generation",
        "checks": (
            {"metric": "operating_cash_flow", "expected": "up", "weight": 2},
            {"metric": "free_cash_flow", "expected": "up", "weight": 2},
            {"metric": "working_capital", "expected": "down_or_flat", "weight": 1},
        ),
        "insufficient_if_no_metrics": True,
    },
    {
        "topic_id": "debt_reduction",
        "category": CAT_DEBT,
        "consistency_bucket": "capital_allocation_consistency",
        "categories": {"Debt Reduction"},
        "keywords": (
            r"debt\s+reduction",
            r"debt\s+repayment",
            r"deleverag",
        ),
        "claim": "debt reduction remains a priority",
        "checks": (
            {"metric": "net_debt", "expected": "down", "weight": 2},
            {"metric": "total_debt", "expected": "down", "weight": 2},
            {"metric": "interest_coverage", "expected": "up", "weight": 1},
        ),
        "insufficient_if_no_metrics": True,
        # Prefer net_debt when both available — handled in fusion by weighting available checks
    },
    {
        "topic_id": "margin_improvement",
        "category": CAT_MARGIN,
        "consistency_bucket": "financial_consistency",
        "categories": {"Cost Optimisation", "Margin Guidance"},
        "keywords": (
            r"margin\s+improvement",
            r"margin\s+expansion",
            r"cost\s+(?:optimisation|optimization|efficiency|discipline)",
            r"operating\s+leverage",
        ),
        "claim": "margin improvement initiatives",
        "checks": (
            {"metric": "operating_margin", "expected": "up", "weight": 2},
            {"metric": "ebitda_margin", "expected": "up", "weight": 1},
            {"metric": "net_margin", "expected": "up", "weight": 1},
        ),
        "insufficient_if_no_metrics": True,
    },
    {
        "topic_id": "growth_expansion",
        "category": CAT_GROWTH,
        "consistency_bucket": "financial_consistency",
        "categories": {"Growth Strategy", "Expansion Plans", "Revenue Guidance"},
        "keywords": (
            r"growth\s+strategy",
            r"expand\s+export",
            r"strong\s+growth",
            r"revenue\s+guidance",
            r"growth\s+guidance",
        ),
        "claim": "growth / expansion",
        "checks": (
            {"metric": "revenue", "expected": "up", "weight": 2},
        ),
        "insufficient_if_no_metrics": True,
    },
    {
        "topic_id": "capital_returns",
        "category": CAT_CAPITAL,
        "consistency_bucket": "capital_allocation_consistency",
        "categories": {"Dividends", "Buybacks", "Cash Deployment"},
        "keywords": (
            r"dividend",
            r"buyback",
            r"share\s+repurchase",
            r"shareholder\s+returns?",
            r"capital\s+return",
        ),
        "claim": "capital returns to shareholders",
        "checks": (
            {"metric": "dividends", "expected": "present_positive", "weight": 1},
            {"metric": "share_buybacks", "expected": "present_positive", "weight": 1},
        ),
        "insufficient_if_no_metrics": True,
        "any_support_ok": True,  # dividend OR buyback
    },
    {
        "topic_id": "liquidity",
        "category": CAT_CAPITAL,
        "consistency_bucket": "capital_allocation_consistency",
        "categories": {"Liquidity"},
        "keywords": (r"liquidity",),
        "claim": "adequate liquidity",
        "checks": (
            {"metric": "cash", "expected": "up_or_flat", "weight": 1},
        ),
        "insufficient_if_no_metrics": True,
    },
    {
        "topic_id": "product_launch",
        "category": CAT_MISSING,
        "consistency_bucket": "insufficient_evidence",
        "categories": {"Product Launches"},
        "keywords": (r"product\s+launch", r"new\s+products?"),
        "claim": "new product launch",
        "checks": (),
        "force_insufficient": True,
    },
    {
        "topic_id": "digital_initiatives",
        "category": CAT_MISSING,
        "consistency_bucket": "insufficient_evidence",
        "categories": {"Digital Initiatives"},
        "keywords": (r"digital\s+initiative", r"generative\s+ai", r"cloud\s+transformation"),
        "claim": "digital / AI initiatives",
        "checks": (),
        "force_insufficient": True,
    },
    {
        "topic_id": "guidance_demand",
        "category": CAT_GUIDANCE,
        "consistency_bucket": "guidance_consistency",
        "categories": {"Demand Outlook", "Industry Outlook"},
        "keywords": (r"demand\s+(?:environment|outlook)", r"industry\s+outlook"),
        "claim": "demand / industry outlook",
        "checks": (
            {"metric": "revenue", "expected": "up_or_flat", "weight": 1},
        ),
        "insufficient_if_no_metrics": True,
    },
    {
        "topic_id": "risk_leverage",
        "category": CAT_RISK,
        "consistency_bucket": "risk_consistency",
        "categories": {"Risk"},
        "keywords": (
            r"interest\s+rate",
            r"leverage",
            r"debt\b",
            r"solvency",
            r"liquidity\s+risk",
        ),
        "claim": "disclosed leverage / interest / liquidity risk",
        # Risk disclosure is "consistent" if financial stress exists (debt up or coverage down)
        # and "partial" if finances are improving (risk noted but metrics easing)
        "checks": (
            {"metric": "total_debt", "expected": "up", "weight": 1},
            {"metric": "interest_coverage", "expected": "down", "weight": 1},
        ),
        "risk_alignment_mode": True,
        "insufficient_if_no_metrics": True,
    },
]


def match_topics(fact: dict[str, Any]) -> list[dict[str, Any]]:
    """Return topic rules matching a BusinessFact (category and/or statement keywords)."""
    cat = str(fact.get("category") or "")
    blob = f"{fact.get('statement') or ''} {fact.get('evidence') or ''}".lower()
    hits: list[dict[str, Any]] = []
    for rule in TOPIC_RULES:
        by_cat = cat in (rule.get("categories") or set())
        by_kw = False
        for pat in rule.get("keywords") or ():
            if re.search(pat, blob, re.I):
                by_kw = True
                break
        if by_cat or by_kw:
            hits.append(rule)
    # Prefer specific financial topics over strategy catch-alls; keep unique topic_ids
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for r in hits:
        tid = r["topic_id"]
        if tid in seen:
            continue
        seen.add(tid)
        out.append(r)
    return out


def strategy_bucket_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Facts that are management-strategy flavoured for EFR strategy grouping."""
    strat_cats = {
        "Growth Strategy",
        "Expansion Plans",
        "Cost Optimisation",
        "Digital Initiatives",
        "Capacity Expansion",
        "Product Launches",
        "Acquisitions",
        "Divestitures",
        "Debt Reduction",
        "Capital Expenditure",
    }
    return [f for f in facts if f.get("category") in strat_cats or match_topics(f)]
