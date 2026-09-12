"""Question → comparison type / module routing (deterministic)."""

from __future__ import annotations

import re
from typing import Any

from comparative_intelligence.schema import (
    DEFAULT_COMPARE_MODULES,
    MODULE_FIRE01,
    MODULE_FIRE02,
    MODULE_FIRE03,
    MODULE_FIRE04,
    MODULE_FIRE05,
    MODULE_FIRE06,
)

# Ordered rules: first match wins
_ROUTE_RULES: list[tuple[re.Pattern[str], str, tuple[str, ...]]] = [
    (
        re.compile(r"balance\s+sheet|leverage|net\s+debt|solvency", re.I),
        "Balance Sheet Comparison",
        (MODULE_FIRE02, MODULE_FIRE06),
    ),
    (
        re.compile(r"\bgrowth\b|revenue\s+growth|top[- ]line|improved\s+margins?", re.I),
        "Growth Comparison",
        (MODULE_FIRE01, MODULE_FIRE06),
    ),
    (
        re.compile(r"cash\s+flow|fcf|free\s+cash|cash\s+generation", re.I),
        "Cash Flow Comparison",
        (MODULE_FIRE01, MODULE_FIRE02, MODULE_FIRE06),
    ),
    (
        re.compile(r"capital\s+allocation|buyback|dividend|capex", re.I),
        "Institutional Comparison",
        (MODULE_FIRE01, MODULE_FIRE03, MODULE_FIRE05, MODULE_FIRE06),
    ),
    (
        re.compile(r"execut|delivered|management\s+deliver", re.I),
        "Execution Comparison",
        (MODULE_FIRE05, MODULE_FIRE03),
    ),
    (
        re.compile(r"evidence|alignment|consistency|supported", re.I),
        "Evidence Comparison",
        (MODULE_FIRE03, MODULE_FIRE04),
    ),
    (
        re.compile(r"business\s+quality|quality\s+of|highest[- ]quality", re.I),
        "Business Quality Comparison",
        (MODULE_FIRE06, MODULE_FIRE01, MODULE_FIRE03),
    ),
    (
        re.compile(r"financial\s+health|strongest|margins?", re.I),
        "Financial Health Comparison",
        (MODULE_FIRE01, MODULE_FIRE02, MODULE_FIRE06),
    ),
    (
        re.compile(r"compare|versus|\bvs\.?\b|side[- ]by[- ]side|relative", re.I),
        "Institutional Comparison",
        DEFAULT_COMPARE_MODULES,
    ),
]

# Extract tickers: "Compare HDFC Bank and ICICI Bank" is hard — prefer explicit ticker lists.
# Pattern for uppercase ticker-like tokens (2–12 alnum)
_TICKER_TOKEN = re.compile(r"\b([A-Z][A-Z0-9]{1,11})\b")
_NOISE = {
    "COMPARE",
    "VERSUS",
    "VS",
    "AND",
    "THE",
    "WITH",
    "FOR",
    "WHICH",
    "HOW",
    "WHAT",
    "BANK",
    "COMPANY",
    "COMPANIES",
    "PRIVATE",
    "PUBLIC",
    "BEST",
    "MOST",
    "STRONG",
    "STRONGEST",
    "HIGHEST",
    "QUALITY",
    "CASH",
    "FLOW",
    "FLOWS",
    "BALANCE",
    "SHEET",
    "GROWTH",
    "MARGIN",
    "MARGINS",
    "CAPITAL",
    "ALLOCATION",
    "MANAGEMENT",
    "EXECUTION",
    "EVIDENCE",
    "BUSINESS",
    "FINANCIAL",
    "HEALTH",
    "IMPROVED",
    "CONSISTENTLY",
    "RELATIVE",
    "SIDE",
    "BY",
}


def extract_tickers(question: str | None, *, explicit: list[str] | None = None) -> list[str]:
    if explicit:
        out = []
        seen = set()
        for t in explicit:
            u = str(t or "").strip().upper()
            if u and u not in seen:
                seen.add(u)
                out.append(u)
        return out
    q = (question or "").strip()
    if not q:
        return []
    found = []
    seen = set()
    for m in _TICKER_TOKEN.finditer(q.upper()):
        tok = m.group(1)
        if tok in _NOISE or len(tok) < 2:
            continue
        if tok not in seen:
            seen.add(tok)
            found.append(tok)
    return found


def route_comparison(
    question: str | None = None,
    *,
    comparison_type: str | None = None,
    modules: list[str] | None = None,
) -> dict[str, Any]:
    q = (question or "").strip()
    if comparison_type and modules:
        return {
            "intent": "explicit",
            "comparison_type": comparison_type,
            "modules": list(modules),
            "question": q or None,
            "matched_rule": "explicit",
            "compares_only": True,
        }
    if comparison_type:
        # Map type to default module sets
        from comparative_intelligence.dimensions import modules_for_comparison_type

        return {
            "intent": "explicit_type",
            "comparison_type": comparison_type,
            "modules": list(modules_for_comparison_type(comparison_type)),
            "question": q or None,
            "matched_rule": "explicit_comparison_type",
            "compares_only": True,
        }

    if not q:
        return {
            "intent": "default_institutional",
            "comparison_type": "Institutional Comparison",
            "modules": list(DEFAULT_COMPARE_MODULES),
            "question": None,
            "matched_rule": "default",
            "compares_only": True,
        }

    for pat, ctype, mods in _ROUTE_RULES:
        if pat.search(q):
            return {
                "intent": ctype.lower().replace(" ", "_"),
                "comparison_type": ctype,
                "modules": list(mods),
                "question": q,
                "matched_rule": pat.pattern,
                "compares_only": True,
            }

    return {
        "intent": "fallback_institutional",
        "comparison_type": "Institutional Comparison",
        "modules": list(DEFAULT_COMPARE_MODULES),
        "question": q,
        "matched_rule": "fallback",
        "compares_only": True,
    }
