"""Currency detection — no FX conversion by default."""

from __future__ import annotations

import re
from typing import Any

_CURRENCY_MAP = {
    "inr": "INR",
    "rs": "INR",
    "₹": "INR",
    "usd": "USD",
    "$": "USD",
    "eur": "EUR",
    "€": "EUR",
    "gbp": "GBP",
    "£": "GBP",
    "jpy": "JPY",
    "¥": "JPY",
}


def detect_currency(text: str | None, default: str = "INR") -> str:
    if not text:
        return default
    s = str(text).lower()
    for key, code in _CURRENCY_MAP.items():
        if key in s:
            return code
    m = re.search(r"\b([A-Z]{3})\b", str(text).upper())
    if m:
        return m.group(1)
    return default


def normalize_currency(
    fields: dict[str, Any],
    *,
    hint: str | None = None,
    default: str = "INR",
) -> dict[str, Any]:
    original = detect_currency(hint, default)
    # No FX by default
    return {
        "original_currency": original,
        "canonical_currency": original,
        "fx_applied": False,
        "fx_timestamp": None,
        "fields": fields,
        "layer": "currency_detection",
    }
