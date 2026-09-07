"""Institutional tone targets — Goldman / MS / JPM / Bloomberg / McKinsey / Bridgewater."""

from __future__ import annotations

import re
from typing import Any

_SENSATIONAL = re.compile(
    r"\b(amazing|incredible|unbelievable|must[- ]buy|guaranteed|skyrocket|crushing it|"
    r"huge win|game[- ]changer|explosive|to the moon)\b",
    re.I,
)
_CONVERSATIONAL = re.compile(
    r"\b(gonna|wanna|kinda|sorta|folks|hey|wow|btw|tbh|imo|let'?s dive|check this out)\b",
    re.I,
)
_PROMOTIONAL = re.compile(
    r"\b(act now|don'?t miss|limited time|best ever|sure thing|can'?t go wrong)\b",
    re.I,
)


def apply_tone(text: Any, *, limit: int = 900) -> str:
    s = str(text or "").strip()
    if not s:
        return ""
    s = _SENSATIONAL.sub("", s)
    s = _CONVERSATIONAL.sub("", s)
    s = _PROMOTIONAL.sub("", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" ,;")
    # Prefer measured institutional cadence — no exclamation
    s = s.replace("!", ".")
    return s[:limit]


def tone_report(text: str) -> dict[str, Any]:
    return {
        "sensational": bool(_SENSATIONAL.search(text or "")),
        "conversational": bool(_CONVERSATIONAL.search(text or "")),
        "promotional": bool(_PROMOTIONAL.search(text or "")),
        "institutional": not (
            bool(_SENSATIONAL.search(text or ""))
            or bool(_CONVERSATIONAL.search(text or ""))
            or bool(_PROMOTIONAL.search(text or ""))
        ),
    }
