"""Module 9 — Knowledge Compiler V2.

Books compile into decision rules / mental models / applicability —
not paragraphs. Soft compilation layer over Academy concepts.
"""

from __future__ import annotations

from typing import Any

COMPILER_VERSION = "knowledge-compiler-v2.0.0"

# Seed compiled rules (executable). Later: derive from Academy books.
_COMPILED: list[dict[str, Any]] = [
    {
        "book": "The Intelligent Investor",
        "author": "Graham",
        "concept": "margin_of_safety",
        "framework": "margin_of_safety",
        "decision_rule": "IF price embeds insufficient MoS THEN reject",
        "mental_model": "asset_earnings_floor",
        "applicability": "profitable companies with tangible earnings history",
        "exceptions": ["franchise compounders with durable ROIC"],
        "failure_conditions": ["speculative growth", "no earnings floor"],
    },
    {
        "book": "Damodaran on Valuation",
        "author": "Damodaran",
        "concept": "relative_valuation",
        "framework": "rel_val_damodaran",
        "decision_rule": "IF peer multiple exists THEN compute premium/discount",
        "mental_model": "growth_relative",
        "applicability": "companies and indices with peer universes",
        "exceptions": ["financial institutions for operating DCF"],
        "failure_conditions": ["peer_pe missing"],
    },
    {
        "book": "Damodaran on Valuation",
        "author": "Damodaran",
        "concept": "dcf",
        "framework": "dcf_fcff",
        "decision_rule": "IF forecastable FCFF THEN DCF else insufficient",
        "mental_model": "growth_dcf",
        "applicability": "non-financial operating companies",
        "exceptions": [],
        "failure_conditions": ["bank", "insurance", "index", "missing cash flows"],
    },
    {
        "book": "Buffett Letters / Wonderful Businesses",
        "author": "Buffett",
        "concept": "wonderful_business",
        "framework": "buffett_quality",
        "decision_rule": "IF ROIC>20 AND durable margins THEN raise quality score",
        "mental_model": "wonderful_business",
        "applicability": "compounding franchises",
        "exceptions": [],
        "failure_conditions": ["pre_profit_growth", "consumer_internet without moat"],
    },
    {
        "book": "Bank Valuation Notes",
        "author": "Institutional",
        "concept": "residual_income",
        "framework": "residual_income",
        "decision_rule": "IF financial institution THEN prefer residual income over DCF",
        "mental_model": "fi_residual_income",
        "applicability": "banks, insurance, NBFCs",
        "exceptions": [],
        "failure_conditions": ["missing book value / ROE"],
    },
]


def compile_library() -> dict[str, Any]:
    return {
        "compiler_version": COMPILER_VERSION,
        "n_rules": len(_COMPILED),
        "rules": list(_COMPILED),
        "note": "Executable compilation — not paragraph retrieval.",
    }


def rules_for_author(author: str) -> list[dict[str, Any]]:
    a = str(author or "").lower()
    return [r for r in _COMPILED if a in str(r.get("author") or "").lower()]


def rules_for_framework(framework_id: str) -> list[dict[str, Any]]:
    return [r for r in _COMPILED if r.get("framework") == framework_id]
