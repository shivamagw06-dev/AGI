"""Normalize FIRE-03 BusinessFacts into durable Objective records with IDs."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from management_execution.periods import period_label
from management_execution.schema import (
    CAT_ACQUISITIONS,
    CAT_CAPACITY,
    CAT_CAPITAL,
    CAT_COST,
    CAT_DEBT,
    CAT_DIGITAL,
    CAT_DIVESTITURES,
    CAT_EFFICIENCY,
    CAT_EXPANSION,
    CAT_EXPORTS,
    CAT_GOVERNANCE,
    CAT_GROWTH,
    CAT_LIQUIDITY,
    CAT_MARGIN,
    CAT_PRODUCTS,
    CAT_RISK,
)

# (topic_key, category, keywords/category matches, horizon, metric checks, evaluable)
OBJECTIVE_TEMPLATES: list[dict[str, Any]] = [
    {
        "topic_key": "DEBT_REDUCTION",
        "category": CAT_DEBT,
        "fact_categories": {"Debt Reduction"},
        "keywords": (r"debt\s+reduction", r"reduce\s+(?:net\s+)?debt", r"debt\s+repayment", r"deleverag"),
        "normalized_statement": "Reduce net debt",
        "expected_horizon": "12–24 months",
        "primary_window": "y2",
        "checks": (
            {"metric": "net_debt", "expected": "down", "weight": 2},
            {"metric": "total_debt", "expected": "down", "weight": 2},
            {"metric": "interest_coverage", "expected": "up", "weight": 1},
        ),
        "prefer_metric": "net_debt",
        "bucket": "capital_allocation_delivery",
    },
    {
        "topic_key": "MARGIN_IMPROVEMENT",
        "category": CAT_MARGIN,
        "fact_categories": {"Cost Optimisation", "Margin Guidance"},
        "keywords": (r"margin\s+improvement", r"margins?\s+to\s+improve", r"operating\s+margins?\s+to\s+improve", r"margin\s+expansion"),
        "normalized_statement": "Improve operating margins",
        "expected_horizon": "12 months",
        "primary_window": "year",
        "checks": (
            {"metric": "operating_margin", "expected": "up", "weight": 2},
            {"metric": "ebitda_margin", "expected": "up", "weight": 1},
        ),
        "bucket": "strategy_delivery",
    },
    {
        "topic_key": "CAPACITY_EXPANSION",
        "category": CAT_CAPACITY,
        "fact_categories": {"Capacity Expansion", "Capital Expenditure"},
        "keywords": (r"capacity\s+expansion", r"invest(?:ing)?\s+heavily\s+in\s+manufacturing", r"expand(?:ing)?\s+manufacturing", r"greenfield\s+capacity"),
        "normalized_statement": "Expand manufacturing capacity",
        "expected_horizon": "12–36 months",
        "primary_window": "y3",
        "checks": ({"metric": "capex", "expected": "up", "weight": 2},),
        "bucket": "capital_allocation_delivery",
    },
    {
        "topic_key": "GROWTH",
        "category": CAT_GROWTH,
        "fact_categories": {"Growth Strategy", "Revenue Guidance"},
        "keywords": (r"growth\s+strategy", r"strong\s+growth", r"revenue\s+guidance", r"expand\s+export"),
        "normalized_statement": "Deliver revenue growth",
        "expected_horizon": "12 months",
        "primary_window": "year",
        "checks": ({"metric": "revenue", "expected": "up", "weight": 2},),
        "bucket": "strategy_delivery",
    },
    {
        "topic_key": "EXPANSION",
        "category": CAT_EXPANSION,
        "fact_categories": {"Expansion Plans"},
        "keywords": (r"expansion\s+plans?", r"expand\s+factory", r"industry\s+expansion"),
        "normalized_statement": "Execute expansion plans",
        "expected_horizon": "12–36 months",
        "primary_window": "y2",
        "checks": (
            {"metric": "capex", "expected": "up", "weight": 1},
            {"metric": "revenue", "expected": "up", "weight": 1},
        ),
        "bucket": "strategy_delivery",
    },
    {
        "topic_key": "CAPITAL_RETURNS",
        "category": CAT_CAPITAL,
        "fact_categories": {"Dividends", "Buybacks", "Cash Deployment"},
        "keywords": (r"dividend", r"buyback", r"shareholder\s+returns?", r"capital\s+return"),
        "normalized_statement": "Return capital to shareholders",
        "expected_horizon": "12 months",
        "primary_window": "year",
        "checks": (
            {"metric": "dividends", "expected": "present_positive", "weight": 1},
            {"metric": "share_buybacks", "expected": "present_positive", "weight": 1},
        ),
        "any_support_ok": True,
        "bucket": "capital_allocation_delivery",
    },
    {
        "topic_key": "LIQUIDITY",
        "category": CAT_LIQUIDITY,
        "fact_categories": {"Liquidity"},
        "keywords": (r"liquidity",),
        "normalized_statement": "Maintain adequate liquidity",
        "expected_horizon": "12 months",
        "primary_window": "year",
        "checks": ({"metric": "cash", "expected": "up_or_flat", "weight": 1},),
        "bucket": "capital_allocation_delivery",
    },
    {
        "topic_key": "COST_OPTIMISATION",
        "category": CAT_COST,
        "fact_categories": {"Cost Optimisation"},
        "keywords": (r"cost\s+(?:optimisation|optimization|efficiency|discipline)", r"efficiency\s+program"),
        "normalized_statement": "Deliver cost optimisation",
        "expected_horizon": "12–24 months",
        "primary_window": "y2",
        "checks": ({"metric": "operating_margin", "expected": "up", "weight": 1},),
        "bucket": "strategy_delivery",
    },
    {
        "topic_key": "DIGITAL_TRANSFORMATION",
        "category": CAT_DIGITAL,
        "fact_categories": {"Digital Initiatives"},
        "keywords": (r"digital", r"generative\s+ai", r"cloud\s+transformation"),
        "normalized_statement": "Advance digital transformation",
        "expected_horizon": "12–36 months",
        "primary_window": "y2",
        "checks": (),
        "force_cannot_evaluate": True,
        "bucket": "strategy_delivery",
    },
    {
        "topic_key": "PRODUCT_LAUNCH",
        "category": CAT_PRODUCTS,
        "fact_categories": {"Product Launches"},
        "keywords": (r"product\s+launch", r"launched\s+product", r"new\s+products?"),
        "normalized_statement": "Launch new product",
        "expected_horizon": "12–36 months",
        "primary_window": "y2",
        "checks": (),
        "force_cannot_evaluate": True,
        "bucket": "strategy_delivery",
    },
    {
        "topic_key": "ACQUISITION",
        "category": CAT_ACQUISITIONS,
        "fact_categories": {"Acquisitions"},
        "keywords": (r"acquisition",),
        "normalized_statement": "Pursue / complete acquisition",
        "expected_horizon": "12–24 months",
        "primary_window": "y2",
        "checks": (),
        "force_cannot_evaluate": True,
        "bucket": "capital_allocation_delivery",
    },
    {
        "topic_key": "DIVESTITURE",
        "category": CAT_DIVESTITURES,
        "fact_categories": {"Divestitures"},
        "keywords": (r"divestiture", r"divestment"),
        "normalized_statement": "Complete divestiture",
        "expected_horizon": "12–24 months",
        "primary_window": "y2",
        "checks": (),
        "force_cannot_evaluate": True,
        "bucket": "capital_allocation_delivery",
    },
    {
        "topic_key": "EXPORT_GROWTH",
        "category": CAT_EXPORTS,
        "fact_categories": set(),
        "keywords": (r"expand\s+export", r"export\s+(?:business|opportunit)"),
        "normalized_statement": "Expand export business",
        "expected_horizon": "12–24 months",
        "primary_window": "y2",
        "checks": ({"metric": "revenue", "expected": "up", "weight": 1},),
        "bucket": "strategy_delivery",
    },
    {
        "topic_key": "EFFICIENCY",
        "category": CAT_EFFICIENCY,
        "fact_categories": set(),
        "keywords": (r"efficiency\s+program", r"utilisation", r"utilization"),
        "normalized_statement": "Improve operating efficiency",
        "expected_horizon": "12–24 months",
        "primary_window": "y2",
        "checks": ({"metric": "operating_margin", "expected": "up", "weight": 1},),
        "bucket": "strategy_delivery",
    },
    {
        "topic_key": "GOVERNANCE",
        "category": CAT_GOVERNANCE,
        "fact_categories": {"Governance"},
        "keywords": (r"board\s+composition", r"related[- ]party", r"auditor\s+change"),
        "normalized_statement": "Governance action disclosed",
        "expected_horizon": "12 months",
        "primary_window": "year",
        "checks": (),
        "force_cannot_evaluate": True,
        "bucket": "strategy_delivery",
    },
    {
        "topic_key": "RISK_MITIGATION",
        "category": CAT_RISK,
        "fact_categories": {"Risk"},
        "keywords": (r"risk\s+mitigation", r"risk\s+management"),
        "normalized_statement": "Risk mitigation programme",
        "expected_horizon": "12–24 months",
        "primary_window": "y2",
        "checks": (),
        "force_cannot_evaluate": True,
        "bucket": "strategy_delivery",
    },
]

_SUPERSEDE_PATTERNS = (
    re.compile(r"\bwithdraw(?:s|n|al)?\b", re.I),
    re.compile(r"\bcancel(?:s|led|ed)?\b", re.I),
    re.compile(r"\bdiscontinu(?:e|ed|es)\b", re.I),
    re.compile(r"\bno longer\b", re.I),
    re.compile(r"\babandon(?:ed|s)?\b", re.I),
    re.compile(r"\bsuspend(?:ed|s)?\b", re.I),
    re.compile(r"\bnot\s+proceed(?:ing)?\b", re.I),
)


def _match_template(fact: dict[str, Any]) -> dict[str, Any] | None:
    cat = str(fact.get("category") or "")
    blob = f"{fact.get('statement') or ''} {fact.get('evidence') or ''}"
    for tmpl in OBJECTIVE_TEMPLATES:
        if cat in (tmpl.get("fact_categories") or set()):
            return tmpl
        for pat in tmpl.get("keywords") or ():
            if re.search(pat, blob, re.I):
                return tmpl
    return None


def make_objective_id(topic_key: str, origin_period: str | None, statement: str, seq: int) -> str:
    pe = re.sub(r"[^A-Z0-9]", "", (origin_period or "UNKNOWN").upper())[:12] or "UNKNOWN"
    return f"{topic_key}_{pe}_{seq:03d}"


def normalize_objectives(facts: list[dict[str, Any]], *, ticker: str = "") -> list[dict[str, Any]]:
    """Convert BusinessFacts into Objective records (deduped by topic+period+normalized statement)."""
    objectives: list[dict[str, Any]] = []
    seen: set[str] = set()
    counters: dict[str, int] = {}

    for fact in facts or []:
        tmpl = _match_template(fact)
        if not tmpl:
            continue
        origin_period = period_label(fact.get("reporting_period")) or period_label(fact.get("document"))
        key = f"{tmpl['topic_key']}|{origin_period}|{tmpl['normalized_statement']}"
        if key in seen:
            continue
        seen.add(key)
        ck = f"{tmpl['topic_key']}|{origin_period}"
        counters[ck] = counters.get(ck, 0) + 1
        oid = make_objective_id(tmpl["topic_key"], origin_period, tmpl["normalized_statement"], counters[ck])
        objectives.append(
            {
                "objective_id": oid,
                "ticker": ticker.upper() if ticker else None,
                "topic_key": tmpl["topic_key"],
                "category": tmpl["category"],
                "statement": tmpl["normalized_statement"],
                "original_statement": fact.get("statement"),
                "origin_document": fact.get("document") or fact.get("source"),
                "origin_document_id": fact.get("document_id"),
                "origin_period": origin_period,
                "origin_page": fact.get("page"),
                "origin_section": fact.get("section"),
                "origin_fact_id": fact.get("fact_id"),
                "expected_horizon": tmpl["expected_horizon"],
                "primary_window": tmpl.get("primary_window") or "year",
                "checks": list(tmpl.get("checks") or []),
                "any_support_ok": bool(tmpl.get("any_support_ok")),
                "force_cannot_evaluate": bool(tmpl.get("force_cannot_evaluate")),
                "prefer_metric": tmpl.get("prefer_metric"),
                "bucket": tmpl.get("bucket") or "strategy_delivery",
                "status": None,
            }
        )
    return objectives


def detect_supersessions(
    objectives: list[dict[str, Any]],
    later_facts: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Map objective_id → superseding fact when later disclosure withdraws the objective."""
    from management_execution.periods import parse_period_to_date

    out: dict[str, dict[str, Any]] = {}
    for obj in objectives:
        o_dt = parse_period_to_date(obj.get("origin_period"))
        topic = str(obj.get("topic_key") or "").lower().replace("_", " ")
        cat = str(obj.get("category") or "").lower()
        orig = str(obj.get("original_statement") or obj.get("statement") or "").lower()
        tokens = [
            t
            for t in re.findall(r"[a-z]{4,}", orig)
            if t not in {"will", "with", "from", "that", "this", "have", "been"}
        ]
        for fact in later_facts or []:
            l_dt = parse_period_to_date(fact.get("reporting_period"))
            if o_dt and l_dt and l_dt <= o_dt:
                continue
            if o_dt and l_dt is None:
                continue
            blob = f"{fact.get('statement') or ''} {fact.get('evidence') or ''}"
            if not any(p.search(blob) for p in _SUPERSEDE_PATTERNS):
                continue
            blob_l = blob.lower()
            topical = (
                (topic.split()[0] in blob_l if topic else False)
                or (cat.split()[0] in blob_l if cat else False)
                or any(t in blob_l for t in tokens[:6])
            )
            if not topical:
                continue
            out[str(obj["objective_id"])] = {
                "fact_id": fact.get("fact_id"),
                "statement": fact.get("statement"),
                "document": fact.get("document"),
                "reporting_period": fact.get("reporting_period"),
                "page": fact.get("page"),
                "section": fact.get("section"),
            }
            break
    return out


def fingerprint_objectives(objectives: list[dict[str, Any]]) -> str:
    raw = "|".join(o.get("objective_id") or "" for o in objectives)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
