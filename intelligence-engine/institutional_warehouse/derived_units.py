"""What unit each derived field is in, and what that means for a write.

The formula engine does not report facts - it computes them from rows already
stored in the warehouse's canonical units. So a derived value's unit follows
from its formula, not from the feed that happened to run the calculation.

    free_cash_flow   INR million       CFO - |capex|, both already normalised
    book_value       INR per share     equity converted to rupees / share count
    ratios           none              margins, turnover, coverage, percentages

That is three different units among one engine's outputs, which is why giving
formula_engine a single declared unit is the wrong fix. It would state that
book_value is in INR million, and it is not.

Why this exists
---------------
gateway.write normalises units from the *writing* source. formula_engine has no
entry in SOURCE_DEFAULT_UNIT, so its writes resolve to assumed_canonical - and
the guard then refuses an unknown-unit row from overwriting a known-unit one.
The effect is backwards: a trusted Upstox row with declared units cannot receive
free_cash_flow, while a 44%-suspect assumed_canonical row can.

A derived-only write asserts no unit. It carries computed columns onto a row
that already has one, so it should neither be re-normalised nor judged on a unit
it never claimed - and it must leave the parent row's source, unit metadata and
trust exactly as they were.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Set

INR_MILLION = "inr_million"
INR_PER_SHARE = "inr_per_share"
UNITLESS = None

#: Unit of each field the formula engine computes. A field absent from this map
#: is not a derived field and is treated as reported data.
DERIVED_FIELD_UNITS: Dict[str, Optional[str]] = {
    # aggregate money, in the same unit as the inputs it was computed from
    "free_cash_flow": INR_MILLION,
    # per share: equity in rupees divided by a plain count
    "book_value": INR_PER_SHARE,
    # ratios and percentages carry no unit at all
    "gross_margin": UNITLESS, "operating_margin": UNITLESS, "net_margin": UNITLESS,
    "ebitda_margin": UNITLESS, "fcf_margin": UNITLESS,
    "roe": UNITLESS, "roa": UNITLESS, "roce": UNITLESS, "roic": UNITLESS,
    "asset_turnover": UNITLESS, "interest_coverage": UNITLESS,
    "current_ratio": UNITLESS, "quick_ratio": UNITLESS, "debt_equity": UNITLESS,
}

#: Columns that address a row rather than assert a value about it.
#:
#: The sys_ columns and canonical markers matter as much as the keys. By the
#: time the guard sees a row the gateway has already attached sys_reported_unit,
#: sys_unit_method, sys_unit_scale, is_canonical and canonical_blockers - so a
#: check that only ignored the natural key concluded a derived payload was
#: asserting reported data, and refused it.
KEY_FIELDS: Set[str] = {
    "symbol", "statement_type", "statement_frequency", "fiscal_year",
    "fiscal_period", "quarter", "source", "row_id",
    "period_key", "is_canonical", "canonical_blockers",
}


def _is_metadata(field: str) -> bool:
    return field in KEY_FIELDS or field.startswith("sys_")

DERIVED_FIELDS: Set[str] = set(DERIVED_FIELD_UNITS)

#: Who is allowed to write derived columns. The exemption skips the unit guard,
#: the unit stamp and the canonical stamp, so it cannot rest on payload shape
#: alone - any feed could then send a row containing only free_cash_flow and
#: reach a trusted row that its reported writes are refused from. Shape says
#: what a payload is; this says who is entitled to send it.
DERIVED_WRITERS: Set[str] = {"formula_engine"}

# Gateway-only proof of which stored row a calculation came from. The gateway
# removes this before validation and persistence; it is never warehouse data.
PARENT_ROW_ID = "_derived_parent_row_id"


def is_derived_writer(source: Any) -> bool:
    return str(source or "").strip().lower() in DERIVED_WRITERS


def unit_of(field: str) -> Optional[str]:
    return DERIVED_FIELD_UNITS.get(field)


def is_derived_field(field: str) -> bool:
    return field in DERIVED_FIELD_UNITS


def carries_money(row: Dict[str, Any]) -> bool:
    """Whether this payload asserts an aggregate-money value.

    Only aggregate money needs a declared unit to be trusted. A payload of
    ratios and per-share figures asserts nothing the unit guard is protecting.
    """
    for field, value in (row or {}).items():
        if value is None or _is_metadata(field):
            continue
        if not is_derived_field(field):
            return True
        if unit_of(field) == INR_MILLION:
            return True
    return False


def is_derived_only(row: Dict[str, Any]) -> bool:
    """Whether this payload carries computed columns and nothing reported.

    Shape only. Callers granting the exemption must also check the writer with
    :func:`is_derived_write` - a row that looks derived is not the same as one
    the formula engine sent.
    """
    fields = {field for field, value in (row or {}).items()
              if value is not None and not _is_metadata(field)}
    if not fields:
        return False
    return fields <= DERIVED_FIELDS


def is_derived_write(row: Dict[str, Any], source: Any) -> bool:
    """Whether this write may take the derived-only exemption.

    Both halves: the payload carries nothing but computed columns, and the
    writer is one entitled to compute them. Either alone is not enough - a
    reported write from the formula engine is still a reported write, and a
    derived-shaped payload from a vendor feed is a vendor feed writing to a row
    it is otherwise refused from.
    """
    return is_derived_writer(source) and is_derived_only(row)


def split(rows: Iterable[Dict[str, Any]]) -> tuple[list, list]:
    """Partition a batch into (derived-only, reported) rows."""
    derived, reported = [], []
    for row in rows or []:
        (derived if is_derived_only(row) else reported).append(row)
    return derived, reported
