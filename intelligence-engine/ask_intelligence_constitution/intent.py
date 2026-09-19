"""Intent detection — answer investment intent, not surface words."""

from __future__ import annotations

import re
from typing import Any

from ask_intelligence_constitution.schema import (
    IRL_TO_CONSTITUTION,
    METHODOLOGY,
    REAL_INTENT_PATTERNS,
    REQUIRED_INTELLIGENCE,
)


def resolve_investment_intent(
    question: str,
    *,
    irl_intent: str | None = None,
) -> dict[str, Any]:
    """Map surface question → constitution primary intent + real intent prose."""
    q = (question or "").strip()
    q_lower = q.lower()

    primary = IRL_TO_CONSTITUTION.get(irl_intent or "", "EDUCATION")
    real_intent = _default_real_intent(primary)
    matched_pattern = None

    for pattern, intent, real in REAL_INTENT_PATTERNS:
        if re.search(pattern, q_lower):
            primary = intent
            real_intent = real
            matched_pattern = pattern
            break

    # IRL override only when no strong pattern match
    if not matched_pattern and irl_intent:
        primary = IRL_TO_CONSTITUTION.get(irl_intent, primary)

    methodology = list(METHODOLOGY.get(primary) or METHODOLOGY.get("EDUCATION", ()))
    required_intel = list(
        REQUIRED_INTELLIGENCE.get(primary) or REQUIRED_INTELLIGENCE.get("EDUCATION", ())
    )

    return {
        "primary_intent": primary,
        "real_intent": real_intent,
        "surface_question": q[:500] if q else None,
        "irl_intent": irl_intent,
        "methodology": methodology,
        "required_intelligence": required_intel,
        "matched_pattern": matched_pattern,
    }


def _default_real_intent(primary: str) -> str:
    defaults = {
        "INVESTMENT_ASSESSMENT": "Help determine whether this company deserves investment consideration",
        "VALUATION": "Evaluate current valuation versus history and expectations",
        "EARNINGS_ANALYSIS": "Determine whether earnings changed the investment thesis",
        "PEER_COMPARISON": "Compare companies on quality, growth, and valuation",
        "PORTFOLIO_ANALYSIS": "Evaluate position within portfolio context",
        "EDUCATION": "Explain institutional concepts for better investment judgement",
        "MACRO_ANALYSIS": "Assess macro transmission to sectors and companies",
        "MARKET_OVERVIEW": "Understand current market state and research focus",
    }
    return defaults.get(primary, "Support institutional research decision-making")
