"""Recommendation policy for Investment Intelligence — observations only."""

from __future__ import annotations

import re

# Hard ban: never emit these as investment recommendations.
_RECO_LEAK = re.compile(
    r"\b((?<!-)buy(?!back)|sell|overweight|underweight|accumulate|"
    r"strong buy|strong sell|initiate coverage|price target|"
    r"target price|we recommend (buying|selling))\b",
    re.I,
)


def strip_recommendation_language(text: str) -> str:
    """Neutralize accidental recommendation phrasing without inventing content."""
    if not text:
        return text
    # Replace common leaks with observational language.
    out = text
    replacements = (
        (r"\bwe recommend buying\b", "investors may monitor"),
        (r"\bwe recommend selling\b", "investors may monitor"),
        (r"\bstrong buy\b", "high relative quality signal"),
        (r"\bstrong sell\b", "elevated risk signal"),
        (r"\boverweight\b", "relative attractiveness (observational)"),
        (r"\bunderweight\b", "relative caution (observational)"),
        (r"\bprice target\b", "valuation driver"),
        (r"\btarget price\b", "valuation driver"),
        (r"\binitiate coverage\b", "structured evaluation"),
    )
    for pat, rep in replacements:
        out = re.sub(pat, rep, out, flags=re.I)
    return out


def has_recommendation_leak(text: str) -> bool:
    if not text:
        return False
    # Allow discussing the words in a policy / negation context.
    low = text.lower()
    if re.search(
        r"(no[_\s-]?buy|no[_\s-]?sell|not a buy|not .*buy\s*/\s*sell|buy\s*/\s*sell recommendation|"
        r"does not recommend|recommendation policy|observations[_\s-]?only|not a trade|"
        r"no recommendation is issued)",
        low,
    ):
        return False
    return bool(_RECO_LEAK.search(text))


def assert_no_recommendation(payload: dict) -> bool:
    """Return True if payload is clean of recommendation leakage."""
    if payload.get("recommendation") not in (None, "", "none", "NONE"):
        return False
    policy = str(payload.get("recommendation_policy") or "")
    if policy and "no_buy_sell" not in policy and "observations_only" not in policy:
        return False
    blob = " ".join(
        str(payload.get(k) or "")
        for k in ("executive_summary", "summary", "supporting_analysis")
    )
    if isinstance(payload.get("supporting_analysis"), list):
        blob += " " + " ".join(str(x) for x in payload["supporting_analysis"])
    return not has_recommendation_leak(blob)
