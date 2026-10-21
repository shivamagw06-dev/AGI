"""Question validator — incomplete, broad, narrow, multi, contradictory."""

from __future__ import annotations

import re
from typing import Any

_GROUP_WORDS = ("tata", "adani", "birla", "mahindra", "bajaj", "reliance group")
_VAGUE = ("analyse", "analyze", "research", "look at", "tell me about", "thoughts on")


def validate_question(question: str) -> dict[str, Any]:
    q = (question or "").strip()
    ql = q.lower()
    issues: list[str] = []
    score = 1.0

    if not q or len(q) < 3:
        return {
            "status": "invalid",
            "score": 0.0,
            "issues": ["incomplete"],
            "label": "Incomplete question",
        }

    # Multiple questions
    if q.count("?") > 1 or re.search(r"\band\b.+\b(also|additionally)\b", ql):
        if q.count("?") > 1:
            issues.append("multiple_questions")
            score -= 0.25

    # Too broad / conglomerate without specificity
    for group in _GROUP_WORDS:
        if re.search(rf"\b{re.escape(group)}\b", ql) and not any(
            x in ql for x in ("bank", "motors", "power", "steel", "consultancy", "tcs", "titan", "infosys")
        ):
            if any(v in ql for v in _VAGUE) or "should i buy" in ql or ql.strip() in {group, f"analyse {group}", f"analyze {group}"}:
                issues.append("too_many_entities")
                score -= 0.55
                break

    # Compare without second target
    if re.search(r"\bcompare\b", ql):
        if " vs " not in ql and " versus " not in ql and " with " not in ql and " against " not in ql:
            # "Compare Infosys" style
            issues.append("missing_comparison_target")
            score -= 0.5

    # Portfolio without capital / horizon / risk
    if "portfolio" in ql or "build a portfolio" in ql or "allocate" in ql:
        has_capital = bool(re.search(r"(₹|rs\.?|inr|\$|\d{4,}|\blakh\b|\bcrore\b)", ql))
        has_horizon = bool(re.search(r"(year|yr|month|horizon|long.?term|short.?term)", ql))
        has_risk = bool(re.search(r"(risk|conservative|aggressive|moderate)", ql))
        missing = []
        if not has_capital:
            missing.append("capital")
        if not has_horizon:
            missing.append("time_horizon")
        if not has_risk:
            missing.append("risk_tolerance")
        if len(missing) >= 2:
            issues.append("missing_portfolio_context")
            score -= 0.2 * len(missing)

    # Bare verbs
    if ql in {"compare", "analyse", "analyze", "buy", "sell", "forecast", "explain"}:
        issues.append("incomplete")
        score = 0.05

    # Contradictory
    if ("buy" in ql and "sell" in ql) or ("bullish" in ql and "bearish" in ql and "or" not in ql):
        issues.append("contradictory")
        score -= 0.35

    # Too narrow / ticker only without intent
    if re.fullmatch(r"[A-Z]{2,12}", q.strip()):
        issues.append("missing_intent")
        score -= 0.3

    score = max(0.0, min(1.0, score))
    if score < 0.45 or "incomplete" in issues or "too_many_entities" in issues or "missing_comparison_target" in issues:
        status = "invalid" if score < 0.35 else "weak"
    elif issues:
        status = "warning"
    else:
        status = "valid"

    return {
        "status": status,
        "score": round(score, 4),
        "issues": issues,
        "label": "Question quality",
    }
