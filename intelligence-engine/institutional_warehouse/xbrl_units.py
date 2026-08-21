"""Resolve the unit an XBRL fact declares. Pure functions, wired into nothing.

Added alongside the existing parser rather than inside it: no current behaviour
changes, and every caller keeps its outputs until a migration step deliberately
switches one over.

decimals is precision, never scale
----------------------------------
The single most important rule here. ``decimals`` asserts how many digits are
reliable; it does not say what a number must be multiplied by. A real filing on
disk reports Reliance's quarterly revenue as::

    unitRef="INR" decimals="-7"  2407150000000.00

The value is already full scale. ``decimals="-7"`` says the last seven digits
are not significant. Multiplying by 1e-7 gives 240,715, which reads as an
ordinary figure in crore and is silently wrong by ten million. This module
therefore records ``decimals`` and has no arithmetic path that reads it - a test
asserts that changing it cannot change a converted value.

Scale comes from ``ix:nonFraction/@scale``, an Inline XBRL attribute. All 113
NSE filings surveyed are plain XBRL and carry none, so scale is detected and
failed closed rather than guessed.
"""

from __future__ import annotations

import re
from typing import Any, Optional

CURRENCY = "currency"
SHARES = "shares"
PURE = "pure"
COMPOUND = "compound"
UNKNOWN = "unknown"

#: What a resolved currency means as a multiplier into INR million. XBRL money
#: facts are absolute units of the currency, so INR facts are absolute rupees.
RUPEES_TO_MILLION = 1e-6

_UNIT_RE = re.compile(r"<(?:\w+:)?unit[^>]*id=\"([^\"]+)\"[^>]*>(.*?)</(?:\w+:)?unit>", re.S)
_MEASURE_RE = re.compile(r"<(?:\w+:)?measure>([^<]+)</(?:\w+:)?measure>")
_DIVIDE_RE = re.compile(r"<(?:\w+:)?divide", re.S)


def parse_units(document: str) -> dict[str, dict[str, Any]]:
    """Map every declared unit id to what it measures."""
    out: dict[str, dict[str, Any]] = {}
    for match in _UNIT_RE.finditer(document or ""):
        unit_id, body = match.group(1), match.group(2)
        measures = _MEASURE_RE.findall(body)
        if _DIVIDE_RE.search(body):
            kind = COMPOUND
        elif len(measures) == 1 and measures[0].startswith("iso4217:"):
            kind = CURRENCY
        elif measures == ["xbrli:shares"]:
            kind = SHARES
        elif measures == ["xbrli:pure"]:
            kind = PURE
        else:
            kind = UNKNOWN
        out[unit_id] = {
            "kind": kind,
            "measures": measures,
            "currency": (measures[0].split(":", 1)[1]
                         if kind == CURRENCY and ":" in measures[0] else None),
        }
    return out


def is_inline_xbrl(document: str) -> bool:
    """Inline XBRL carries scale on the fact and is not handled yet."""
    return "ix:nonFraction" in (document or "")


def resolve(fact: dict[str, Any], units: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """What this fact's value means, or why it cannot be established.

    Never raises and never guesses. An unresolved fact is returned as unknown
    with a reason, because the fallback that treats unknown as canonical is what
    put absolute rupees in a column of INR million.
    """
    unit_ref = fact.get("unitRef")
    raw = fact.get("raw_value")
    result: dict[str, Any] = {
        "unit_ref": unit_ref,
        "raw_value": raw,
        # Carried for the record. Nothing below reads it.
        "decimals": fact.get("decimals"),
        "usable_as_money": False,
        "kind": UNKNOWN,
        "currency": None,
        "normalised_value": None,
        "scale_factor": None,
        "transform": [],
        "reason": None,
    }

    if fact.get("scale") not in (None, ""):
        result["reason"] = "inline_xbrl_scale_not_supported"
        return result
    if not unit_ref:
        result["reason"] = "missing_unitRef"
        return result
    unit = units.get(str(unit_ref))
    if not unit:
        result["reason"] = f"unitRef_not_declared:{unit_ref}"
        return result

    result["kind"] = unit["kind"]
    result["currency"] = unit.get("currency")
    if unit["kind"] == COMPOUND:
        # INRPerShare carries EPS in every money filing surveyed. Read as INR it
        # would put a per-share figure in an aggregate column.
        result["reason"] = "compound_unit_is_not_an_aggregate"
        return result
    if unit["kind"] in (SHARES, PURE):
        result["reason"] = f"{unit['kind']}_is_not_money"
        return result
    if unit["kind"] != CURRENCY:
        result["reason"] = "unit_not_recognised"
        return result
    if unit.get("currency") != "INR":
        result["reason"] = f"currency_not_supported:{unit.get('currency')}"
        return result

    value = _num(raw)
    if value is None:
        result["reason"] = "value_not_numeric"
        return result

    result["usable_as_money"] = True
    result["scale_factor"] = RUPEES_TO_MILLION
    result["normalised_value"] = value * RUPEES_TO_MILLION
    result["transform"] = [
        {"step": "unit_resolved", "from": "iso4217:INR", "basis": "unitRef"},
        {"step": "to_inr_million", "factor": RUPEES_TO_MILLION},
    ]
    result["reason"] = "declared"
    return result


def _num(raw: Any) -> Optional[float]:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return None if value != value else value
