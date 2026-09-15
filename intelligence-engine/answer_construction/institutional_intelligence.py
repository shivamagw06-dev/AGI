"""AGIB Institutional Intelligence — concise CIO voice for Ask AGI answers.

Soft presentation rules only. Never invent company-specific facts.
Recommendation actions are derived from existing house stance / scores,
or explicitly withheld when evidence is insufficient.
"""

from __future__ import annotations

import re
from typing import Any

VOICE_NAME = "AGIB Institutional Intelligence"
MAX_ANSWER_WORDS = 60
ARCHITECTURE_SOFT = True

try:
    from institutional_reasoning.prompt import TOP_RULE as _IRSP_TOP_RULE
except Exception:  # pragma: no cover
    _IRSP_TOP_RULE = (
        "Before producing any answer, ask yourself: "
        "'What evidence would I need to justify every sentence I am about to write?' "
        "If sufficient evidence is not available, reduce confidence or explicitly state "
        "the limitation instead of filling the gap."
    )

SYSTEM_RULES = f"""You are AGIB Institutional Intelligence.

TOP RULE
{_IRSP_TOP_RULE}

Your role is to provide concise, evidence-based institutional investment answers
that a hedge-fund CIO and a first-time investor can both understand.

Rules:
- Think like a senior equity research analyst speaking to a client.
- Answer the user's question first. Never bury the conclusion.
- Never answer like a retail investing blog or an AI summariser.
- Maximum answer length: 60 words unless explicitly asked for more.
- Be direct. Use plain English. One idea per sentence.
- Do not use unnecessary introductions, disclaimers, or corporate buzzwords.
- Avoid repeating information.
- When a finance term appears, explain it naturally in the same sentence.
- Every opinion needs a reason (Positive/Neutral/Monitoring are incomplete without “because…”).
- Never exaggerate certainty.
- If evidence is insufficient, explicitly state that — and why it matters.
- Never invent company-specific facts.
- Never answer from memory alone.
- Never jump to conclusions.
- Never guess.
- Prioritise: business quality, financial quality, valuation, risk, macro impact.
- Do not discuss all five unless necessary.
- Evidence creates conclusions. Conclusions create answers. Never reverse this order.
- Avoid unsupported phrases like “strong business”, “robust growth”, or “healthy fundamentals”
  unless you immediately explain why with AGIB evidence.

For stock recommendations always follow this structure:
Recommendation: Buy / Hold / Sell / Accumulate / Avoid
Reason: One concise sentence explaining the primary investment thesis (with because…).
Risk: State the single biggest risk and why it matters.
Investment Horizon: Short Term / Medium Term / Long Term.
"""

_RECO_QUERY = re.compile(
    r"\b("
    r"should\s+i\s+(buy|sell|accumulate|hold|avoid)|"
    r"buy\s+or\s+sell|"
    r"(buy|sell|accumulate|avoid)\s+(recommendation|rating|call)|"
    r"is\s+.+\s+a\s+(buy|sell)|"
    r"recommendation\s+on|"
    r"worth\s+buying|"
    r"good\s+buy|"
    r"(give\s+me\s+a\s+)?target\s+price|"
    r"price\s+target"
    r")\b",
    re.I,
)

_DETAILED_REQUEST = re.compile(
    r"\b(detailed|deep\s*dive|full\s+analysis|in[- ]depth|elaborate|more\s+detail|long[- ]form)\b",
    re.I,
)


# Asking what the sell side thinks is a market-data question, not a request
# for an AGI call — "consensus target price" must reach Consensus
# Intelligence rather than the no-recommendations refusal.
_CONSENSUS_DATA_QUERY = re.compile(
    r"\b(consensus|analysts?|brokers?|brokerages?|sell[- ]side|street)\b", re.I
)
_ASKS_AGI_FOR_A_CALL = re.compile(
    r"\b(should\s+i\b|buy\s+or\s+sell|is\s+.+\s+a\s+(buy|sell)|"
    r"give\s+me\s+a\s+target|your\s+(target|call|recommendation)|"
    r"do\s+you\s+recommend|worth\s+buying|good\s+buy)\b",
    re.I,
)

# A request can explicitly *exclude* recommendations while still asking for
# research.  For example, "Compare HDFC Bank vs ICICI Bank ... do not give a
# buy or sell recommendation" must reach the comparison workflow.  Treating
# that final safety instruction as recommendation bait discards the actual
# research question and produces a policy template instead of an answer.
_NEGATED_RECOMMENDATION_INSTRUCTION = re.compile(
    r"\b(?:do\s+not|don't|without|no|not)\s+"
    r"(?:give|provide|make|offer|include)?\s*"
    r"(?:me\s+)?(?:a\s+)?"
    r"(?:buy\s+or\s+sell|recommendation|rating|call|target\s+price)\b",
    re.I,
)


def is_recommendation_query(query: str | None) -> bool:
    q = str(query or "")
    if _CONSENSUS_DATA_QUERY.search(q) and not _ASKS_AGI_FOR_A_CALL.search(q):
        return False
    # Remove a user's no-recommendation constraint before classifying the
    # underlying question.  Do not suppress a genuine request elsewhere in
    # the same question (e.g. "Do not give a recommendation, but should I
    # buy?").
    question_without_constraint = _NEGATED_RECOMMENDATION_INSTRUCTION.sub("", q)
    return bool(_RECO_QUERY.search(question_without_constraint))


def wants_detailed_analysis(query: str | None) -> bool:
    return bool(_DETAILED_REQUEST.search(str(query or "")))


def word_count(text: str | None) -> int:
    return len([w for w in re.split(r"\s+", str(text or "").strip()) if w])


def clamp_words(text: str | None, *, max_words: int = MAX_ANSWER_WORDS) -> str:
    words = [w for w in re.split(r"\s+", str(text or "").strip()) if w]
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(" ,;:") + "."


def _txt(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _first(*candidates: Any) -> str | None:
    for c in candidates:
        t = _txt(c)
        if t:
            return t
    return None


def map_action_from_stance(
    stance: str | None,
    *,
    blocked: bool = False,
    quality_score: float | None = None,
) -> tuple[str, str | None]:
    """Map analytical stance → institutional action + optional conviction.

    Does not invent facts; stance must already exist from AGIB stack.
    """
    if blocked:
        return "Withheld", None

    s = str(stance or "").strip().lower()
    if not s or "insufficient" in s:
        return "Withheld", None

    if any(k in s for k in ("strong buy", "strongly bull", "overweight", "highly constructive")):
        return "Buy", "High Conviction"
    if any(k in s for k in ("bull", "constructive", "positive", "accumulate")):
        if quality_score is not None and quality_score >= 75:
            return "Buy", "Medium Conviction"
        return "Accumulate", "Medium Conviction"
    if any(k in s for k in ("sell", "underweight", "strongly bear", "highly cautious")):
        return "Sell", "Medium Conviction"
    if any(k in s for k in ("bear", "avoid", "negative", "cautious")):
        return "Avoid", "Medium Conviction"
    if any(k in s for k in ("hold", "neutral", "mixed", "balanced")):
        return "Hold", None
    return "Hold", None


def infer_horizon(query: str | None = None, stance: str | None = None) -> str:
    q = str(query or "").lower()
    if any(k in q for k in ("short term", "near term", "trading", "weeks", "months")):
        return "Short Term"
    if any(k in q for k in ("long term", "multi-year", "3-5", "5 year", "compound")):
        return "Long Term"
    s = str(stance or "").lower()
    if "long" in s:
        return "Long Term"
    if "short" in s:
        return "Short Term"
    return "Medium Term"


def build_institutional_recommendation(
    *,
    query: str = "",
    company_name: str | None = None,
    stance: str | None = None,
    blocked: bool = False,
    reason_candidates: list[Any] | None = None,
    risk_candidates: list[Any] | None = None,
    quality_score: float | None = None,
    detailed: bool | None = None,
) -> dict[str, Any]:
    """Build the concise CIO recommendation card used as Ask AGI lead answer."""
    name = _txt(company_name) or "This issuer"
    action, conviction = map_action_from_stance(stance, blocked=blocked, quality_score=quality_score)
    horizon = infer_horizon(query, stance)
    allow_long = bool(detailed if detailed is not None else wants_detailed_analysis(query))
    max_words = 180 if allow_long else MAX_ANSWER_WORDS

    reason = _first(*(reason_candidates or []))
    risk = _first(*(risk_candidates or []))

    if action == "Withheld":
        reason = reason or (
            f"Validated coverage for {name} is insufficient for an institutional ownership call. "
            "This is not a negative view of the company."
        )
        risk = risk or "Acting without fuller financial and valuation evidence."
        body = (
            f"Investment Thesis: INCONCLUSIVE\n\n"
            f"Evidence is insufficient for an institutional recommendation on {name}. "
            f"This should not be read as a negative company view. "
            f"{clamp_words(reason, max_words=28)} "
            f"Watch items: {clamp_words(risk, max_words=16)} "
            f"Horizon: {horizon}."
        )
        text = clamp_words(body, max_words=max_words)
        return {
            "enabled": True,
            "voice": VOICE_NAME,
            "is_recommendation_query": True,
            "recommendation": "Withheld",
            "investment_thesis_status": "INCONCLUSIVE",
            "not_a_negative_view": True,
            "conviction": None,
            "reason": clamp_words(reason, max_words=28),
            "risk": clamp_words(risk, max_words=16),
            "horizon": horizon,
            "text": text,
            "word_count": word_count(text),
            "max_words": max_words,
            "evidence_insufficient": True,
            "never_invent_facts": True,
        }

    reason = reason or (
        f"{name} offers institutional-quality franchise characteristics, but ownership sizing should "
        "follow validated financial and valuation evidence."
    )
    risk = risk or "Thesis impairment from competitive intensity or earnings disappointment."

    reco_line = f"Recommendation: {action}"
    if conviction:
        reco_line += f" ({conviction})"

    # Compact card matching the user's examples (reason embedded, then risk + horizon).
    prose = (
        f"{reco_line}\n\n"
        f"{clamp_words(reason, max_words=28)} "
        f"{clamp_words(risk, max_words=18)} "
        f"Suitable for a {horizon.lower()} institutional horizon."
    )
    text = clamp_words(prose, max_words=max_words)

    return {
        "enabled": True,
        "voice": VOICE_NAME,
        "is_recommendation_query": True,
        "recommendation": action,
        "conviction": conviction,
        "reason": clamp_words(reason, max_words=28),
        "risk": clamp_words(risk, max_words=18),
        "horizon": horizon,
        "text": text,
        "word_count": word_count(text),
        "max_words": max_words,
        "evidence_insufficient": False,
        "never_invent_facts": True,
        "structured": {
            "Recommendation": f"{action}" + (f" ({conviction})" if conviction else ""),
            "Reason": clamp_words(reason, max_words=28),
            "Risk": clamp_words(risk, max_words=18),
            "Investment Horizon": horizon,
        },
    }


def apply_concise_voice(text: str | None, *, query: str = "", fallback: str | None = None) -> str:
    """Clamp general institutional answers to the 60-word CIO voice unless detail requested."""
    raw = _txt(text) or _txt(fallback) or ""
    if not raw:
        return ""
    if wants_detailed_analysis(query):
        return raw
    return clamp_words(raw, max_words=MAX_ANSWER_WORDS)
