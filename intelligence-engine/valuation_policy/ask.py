"""Ask AGI helpers that speak valuation policy, not raw multiples."""

from __future__ import annotations

import re
from typing import Any, Optional

from valuation_policy.engine import evaluate
from valuation_policy.models import ENGINE_CODE, VERSION

_HOW_VALUE = re.compile(
    r"\b(how\s+should|how\s+do\s+(we|you|i)|what\s+valuation|valued\s+using|"
    r"valuation\s+(model|framework|method)|primary\s+valuation)\b",
    re.I,
)
_WHY_NO_PE = re.compile(
    r"\b(why\s+(doesn'?t|does\s+not|no|missing)|where\s+is|what\s+happened\s+to).{0,40}\bP\s*/?\s*E\b|"
    r"\bP\s*/?\s*E\b.{0,40}\b(missing|unavailable|not\s+shown|hidden|n/?a)\b",
    re.I,
)


def is_valuation_policy_question(question: str) -> bool:
    text = str(question or "").strip()
    if not text:
        return False
    return bool(_HOW_VALUE.search(text) or _WHY_NO_PE.search(text) or "valuation model" in text.lower())


def answer_for(
    symbol: str,
    question: str = "",
    *,
    record: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Structured Ask answer grounded in VPAE."""
    policy = evaluate(symbol, record=record)
    if not policy.get("ok"):
        return {
            "ok": False,
            "symbol": str(symbol or "").upper(),
            "error": policy.get("error") or "policy_unavailable",
            "engine": ENGINE_CODE,
        }

    name = (policy.get("company") or {}).get("name") or policy["symbol"]
    q = str(question or "")
    if _WHY_NO_PE.search(q) or (
        "pe" in (policy.get("hidden_metrics") or []) and "p/e" in q.lower()
    ):
        pe_entry = (policy.get("metrics") or {}).get("pe") or {}
        prose = (
            f"{name} is not shown on a Price-to-Earnings multiple.\n\n"
            f"Primary Valuation Model: {policy['primary_model']}\n"
            f"Reason: {pe_entry.get('reason') or policy['reason']}\n"
        )
        if policy.get("supporting_models"):
            prose += "Supporting Metrics: " + ", ".join(policy["supporting_models"]) + "\n"
        prose += f"Confidence: {policy['confidence']}"
    else:
        prose = (
            f"Primary Valuation Model: {policy['primary_model']}\n\n"
            f"Why?\n{policy['reason']}\n\n"
        )
        if policy.get("supporting_models"):
            prose += "Supporting Metrics:\n- " + "\n- ".join(policy["supporting_models"]) + "\n\n"
        if policy.get("hidden_models"):
            prose += "Hidden Metrics:\n"
            for m in policy.get("hidden_metrics") or []:
                entry = (policy.get("metrics") or {}).get(m) or {}
                prose += f"- {entry.get('model', m)} — {entry.get('reason')}\n"
            prose += "\n"
        prose += f"Confidence: {policy['confidence']}\nStatus: {policy['status']}"

    return {
        "ok": True,
        "symbol": policy["symbol"],
        "engine": ENGINE_CODE,
        "version": VERSION,
        "question": question,
        "answer": prose,
        "policy": {
            "primary_model": policy["primary_model"],
            "supporting_models": policy["supporting_models"],
            "hidden_models": policy["hidden_models"],
            "status": policy["status"],
            "confidence": policy["confidence"],
            "reason": policy["reason"],
        },
    }
