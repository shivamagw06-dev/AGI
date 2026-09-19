"""Tier A smoke prompts and Tier B helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

SMOKE_PROMPTS: List[Dict[str, Any]] = [
    {
        "id": "SMOKE-01",
        "prompt": "What is Reliance's business model?",
        "intent_family": "Company",
        "expected_entities": ["RELIANCE"],
        "forbid_entities": ["AAPL", "APPLE", "INFY", "INFOSYS"],
    },
    {
        "id": "SMOKE-02",
        "prompt": "Compare Infosys vs TCS valuation.",
        "intent_family": "Compare",
        "expected_entities": ["INFY", "TCS"],
        "forbid_entities": ["RELIANCE", "AAPL"],
    },
    {
        "id": "SMOKE-03",
        "prompt": "Explain price-to-book for banks.",
        "intent_family": "Education",
        "expected_entities": [],
        "forbid_entities": [],
        "concept_mode": True,
    },
    {
        "id": "SMOKE-04",
        "prompt": "What did Meta say in Q2 2026 about AI capex?",
        "intent_family": "Company",
        "expected_entities": ["META", "META PLATFORMS", "FACEBOOK"],
        "forbid_entities": ["AAPL", "APPLE", "MSFT"],
    },
    {
        "id": "SMOKE-05",
        "prompt": "Private market multiples for healthcare services.",
        "intent_family": "Private Markets",
        "expected_entities": [],
        "forbid_entities": [],
    },
    {
        "id": "SMOKE-06",
        "prompt": "Should I buy HDFC Bank tomorrow?",
        "intent_family": "Company",
        "expected_entities": ["HDFCBANK", "HDFC BANK"],
        "forbid_entities": [],
        "recommendation_bait": True,
    },
    {
        "id": "SMOKE-07",
        "prompt": "As of 2020-03-31, where was Nifty valuation?",
        "intent_family": "Historical",
        "expected_entities": ["NIFTY"],
        "forbid_entities": [],
        "as_of": "2020-03-31",
        "must_not_leak": ["2024", "2025", "2026 generative", "chatgpt"],
    },
    {
        "id": "SMOKE-08",
        "prompt": "Summarize India's mid-2026 equity outlook.",
        "intent_family": "Macro",
        "expected_entities": [],
        "forbid_entities": [],
    },
]

UNKNOWN_COMPANY_PROMPT = {
    "id": "REG-UNKNOWN",
    "prompt": "Explain XYZ Private Ltd founded yesterday.",
    "intent_family": "Company",
    "expected_entities": [],
    "forbid_entities": [],
    "expect_insufficient_evidence": True,
}

# Tier IKL — founder questions that prove persistent memory is used (after IKL deploy).
# Product-contract checks always apply. Memory-layer asserts are soft unless
# ASK_TEST_IKL_STRICT=1 (or inprocess with IKL local memory populated).
IKL_PROMPTS: List[Dict[str, Any]] = [
    {
        "id": "IKL-01",
        "prompt": "Explain Reliance Industries' business model.",
        "intent_family": "Company",
        "expected_entities": ["RELIANCE"],
        "forbid_entities": ["AAPL", "APPLE", "INFY"],
        "ikl_expect_layers": ["company_memory"],
        "ikl_primary_memory": True,
        "ticker": "RELIANCE",
    },
    {
        "id": "IKL-02",
        "prompt": "How has Meta's AI infrastructure strategy evolved over the last four quarters?",
        "intent_family": "Company",
        "expected_entities": ["META", "META PLATFORMS", "FACEBOOK"],
        "forbid_entities": ["AAPL", "APPLE", "MSFT"],
        "ikl_expect_layers": ["company_memory", "historical_timeline"],
        "ikl_expect_multi_document": True,
        "ticker": "META",
    },
    {
        "id": "IKL-03",
        "prompt": "Why are hospitals typically valued differently from pharmaceutical manufacturers?",
        "intent_family": "Industry",
        "expected_entities": [],
        "forbid_entities": [],
        "ikl_expect_layers": ["industry_memory"],
        "concept_mode": True,
    },
    {
        "id": "IKL-04",
        "prompt": "How would a sustained decline in crude oil prices affect Indian aviation, paints, and OMCs?",
        "intent_family": "Macro",
        "expected_entities": [],
        "forbid_entities": [],
        "ikl_expect_layers": ["macro_memory", "industry_memory", "knowledge_graph"],
    },
    {
        "id": "IKL-05",
        "prompt": "Explain XYZ Private Ltd founded yesterday.",
        "intent_family": "Company",
        "expected_entities": [],
        "forbid_entities": [],
        "expect_insufficient_evidence": True,
        "ikl_expect_knowledge_gap": True,
    },
]

CONTEXT_ISOLATION_SEQUENCE = [
    {
        "id": "CTX-01",
        "prompt": "What is Apple's latest valuation debate?",
        "expected_entities": ["AAPL", "APPLE"],
        "forbid_entities": ["RELIANCE", "HDFCBANK"],
    },
    {
        "id": "CTX-02",
        "prompt": "Explain Reliance Industries refining economics.",
        "expected_entities": ["RELIANCE"],
        "forbid_entities": ["AAPL", "APPLE", "INFY"],
    },
    {
        "id": "CTX-03",
        "prompt": "Explain price-to-book for banks.",
        "expected_entities": [],
        "forbid_entities": ["AAPL", "APPLE", "RELIANCE"],
        "concept_mode": True,
    },
]

DETERMINISM_PROMPT_IDS = ("CIO-Q05", "CIO-Q01")


def intent_family_from_gold(intents: Optional[List[str]], category: str = "") -> str:
    """Map CIO gold intents to founder-facing intent families."""
    raw = [str(i) for i in (intents or [])]
    joined = " ".join(raw + [category or ""]).lower()
    order = [
        ("HistoricalReplay", "Historical"),
        ("historical", "Historical"),
        ("Education", "Education"),
        ("Documents", "Documents"),
        ("Macro", "Macro"),
        ("Government", "Macro"),
        ("Compare", "Compare"),
        ("Industry", "Industry"),
        ("CrossDomain", "Macro"),
        ("Accounting", "Company"),
        ("Explain", "Explain"),
        ("Analyse", "Company"),
        ("company", "Company"),
        ("valuation", "Explain"),
        ("private", "Private Markets"),
    ]
    for needle, family in order:
        if needle.lower() in joined:
            return family
    return raw[0] if raw else "Unknown"
