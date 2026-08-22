"""What makes a fundamentals row fit to be read, rather than merely stored.

The warehouse holds RELIANCE's June 2026 quarter four times, in three different
magnitudes. Upstox reported it in crores and it was rescaled to INR million;
another importer sent absolute rupees and declared no unit at all, so
:func:`units.resolve_unit` fell through to "assume it is already canonical" and
stored 1,660,130,000,000 as though it were millions. The two numbers differ by a
factor of about half a million and sit in the same column of the same table.

Nothing was overwritten and no check failed. Each writer was correct about its
own payload; what was missing was a statement of which row a reader should
believe.

The rule
--------
A row becomes canonical only when four things about it are known and normalised:

* **period** - the label parses to a period key, so it can be compared
* **statement type** - consolidated or standalone, never UNKNOWN, because the
  two are different facts and a row filed under neither cannot be compared with
  its own sibling
* **source** - a source this tab actually trusts for this data
* **units** - a declared or source-known unit, never "assumed canonical", which
  is the assumption that put rupees in a millions column

Anything failing one of those stays stored, keeps its history, and is readable
as evidence. It just does not answer the question "what is revenue".

That last part matters more than it looks. A non-canonical source is not a
disposable one: it is sometimes the only holder of a period, and dropping it
because it is untrusted would delete data nothing else covers.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from institutional_warehouse import derived_units, period_identity, units

#: Sources whose fundamentals rows may be read as the answer, per tab.
#:
#: Upstox is the live feed for recent periods; it returns four annual periods
#: and the current quarters, in crores, with the unit declared. Capital IQ is
#: the decade of history behind them, exported in INR million. Everything else
#: writing these tabs - Yahoo, the financial connector, the formula engine -
#: predates that contract and is kept as evidence rather than as an answer.
CANONICAL_SOURCES: dict[str, frozenset[str]] = {
    "financials_annual": frozenset({
        "upstox", "upstox_fundamentals",
        "capital_iq", "capital_iq_workbook", "capiq",
    }),
    "financials_quarterly": frozenset({
        "upstox", "upstox_fundamentals",
        "capital_iq", "capital_iq_workbook", "capiq",
    }),
}

#: Statement types that identify a real filing. UNKNOWN does not.
KNOWN_STATEMENT_TYPES: frozenset[str] = frozenset({"CONSOLIDATED", "STANDALONE"})

# Blocker codes. Named so a dry run can count them without parsing prose.
PERIOD_UNPARSEABLE = "period_unparseable"
STATEMENT_TYPE_UNKNOWN = "statement_type_unknown"
SOURCE_NOT_CANONICAL = "source_not_canonical"
UNITS_UNKNOWN = "units_unknown"


def is_fundamental(tab_id: str) -> bool:
    return tab_id in period_identity.FUNDAMENTAL_TABS


def canonical_sources(tab_id: str) -> frozenset[str]:
    return CANONICAL_SOURCES.get(tab_id, frozenset())


def source_is_canonical(tab_id: str, source: Any) -> bool:
    return str(source or "").strip().lower() in canonical_sources(tab_id)


def blockers(tab_id: str, row: dict[str, Any], *, source: Any) -> tuple[str, ...]:
    """Every reason this row may not be read as the answer. Empty means it may."""
    found: list[str] = []

    field = period_identity.PERIOD_FIELD.get(tab_id)
    key = row.get("period_key") or (period_identity.period_key(row.get(field)) if field else None)
    if not key:
        found.append(PERIOD_UNPARSEABLE)

    if str(row.get("statement_type") or "").strip().upper() not in KNOWN_STATEMENT_TYPES:
        found.append(STATEMENT_TYPE_UNKNOWN)

    if not source_is_canonical(tab_id, source):
        found.append(SOURCE_NOT_CANONICAL)

    # "assumed_canonical" is not a known unit. It is the absence of one, and it
    # is what silently stored absolute rupees as INR million.
    if str(row.get("sys_unit_method") or "") in ("", units.METHOD_ASSUMED):
        found.append(UNITS_UNKNOWN)

    return tuple(found)


def stamp(tab_id: str, rows: Sequence[dict[str, Any]], *, source: Any) -> list[dict[str, Any]]:
    """Mark each row canonical or not, and say why not.

    Runs after unit normalisation, because whether the unit is known is one of
    the four conditions and is only decided there.
    """
    if not is_fundamental(tab_id):
        return list(rows or [])
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        new_row = dict(row)
        # A derived-only write makes no claim about whether the row may be read
        # as the answer - it adds computed columns to a row that has already
        # been judged. Stamping it here would recompute that judgement from the
        # formula engine's own source and overwrite it, turning a trusted row
        # non-canonical for the crime of receiving a free_cash_flow.
        if derived_units.is_derived_only(new_row):
            out.append(new_row)
            continue
        why = blockers(tab_id, new_row, source=source)
        new_row["is_canonical"] = not why
        new_row["canonical_blockers"] = ", ".join(why)
        out.append(new_row)
    return out


def summarise(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Counts for the write result: how many rows are readable, and what stopped the rest."""
    canonical = 0
    reasons: dict[str, int] = {}
    total = 0
    for row in rows or []:
        if not isinstance(row, dict) or "is_canonical" not in row:
            continue
        total += 1
        if row.get("is_canonical"):
            canonical += 1
            continue
        for code in str(row.get("canonical_blockers") or "").split(", "):
            if code:
                reasons[code] = reasons.get(code, 0) + 1
    return {"rows": total, "canonical": canonical,
            "non_canonical": total - canonical, "blockers": reasons}


# --------------------------------------------------------------------------
# Protecting what is already canonical
# --------------------------------------------------------------------------

def unit_is_known(row: dict[str, Any]) -> bool:
    """Whether this row's magnitude is established rather than assumed.

    A known unit means the normaliser rescaled the row into INR million, so it
    is on the same scale as every other known row - the input scale differing
    (crore against inr_million) is what normalisation is *for* and is not an
    incompatibility. An assumed unit means nothing was rescaled and the vendor's
    raw magnitude was stored as though it were already canonical. That is the
    row that is on a different scale from everything around it.
    """
    return str(row.get("sys_unit_method") or "") not in ("", units.METHOD_ASSUMED)


def _prior_is_trusted(tab_id: str, prior: dict[str, Any]) -> bool:
    """Whether the stored row may be read as fact.

    is_canonical is stamped on write, so every row written before that column
    existed carries NULL - which is every quarterly row in production today. A
    guard that trusts the flag alone therefore protects none of them: a feed
    with a known-but-undeclared unit overwrites a declared Upstox row and no
    refusal is recorded, because NULL is falsy.

    So the flag is used when it was set, and otherwise the same source and unit
    test the read path applies is computed here. A row is not less protected for
    having been written before the column existed.
    """
    from institutional_warehouse import statement_trust

    flag = prior.get("is_canonical")
    if flag is not None:
        return bool(flag)
    return statement_trust.is_trusted(tab_id, prior)


def _row_is_trusted(tab_id: str, row: dict[str, Any]) -> bool:
    from institutional_warehouse import statement_trust

    flag = row.get("is_canonical")
    if flag is not None:
        return bool(flag)
    return statement_trust.is_trusted(tab_id, row)


def guard(tab_id: str, rows: Sequence[dict[str, Any]], existing: dict[str, dict[str, Any]],
          *, key_of: Any) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Stop a write that would corrupt a row already fit to be read.

    Two refusals, both for things that have happened here:

    * a non-canonical row overwriting a canonical one - the untrusted vendor
      wins simply by arriving later, which is how a good number becomes a bad
      one with nobody choosing it
    * a row whose unit is unknown overwriting one whose unit is known - the
      stored value is in INR million and the incoming one is in whatever the
      vendor sent, so this is not an update but a corruption. Going the other
      way is an upgrade and is allowed: replacing an assumed magnitude with an
      established one is the fix, not the failure.

    Refused rows are dropped from the write, not silently merged. The counts
    come back so the caller can report them rather than swallow them.
    """
    if not is_fundamental(tab_id):
        return list(rows or []), {}

    kept: list[dict[str, Any]] = []
    refused_downgrade = 0
    refused_units = 0
    for row in rows or []:
        prior = existing.get(key_of(row)) or {}
        if not prior:
            kept.append(row)
            continue

        # A derived-only write asserts no unit and claims no provenance. It
        # carries computed columns onto a row that already has both, so judging
        # it on a unit it never claimed refused free_cash_flow onto every
        # declared row while allowing it onto assumed_canonical ones - exactly
        # backwards. It cannot promote the row either: the payload has no
        # reported value and store.upsert leaves source untouched on update.
        if derived_units.is_derived_only(row):
            kept.append(row)
            continue

        if _prior_is_trusted(tab_id, prior) and not _row_is_trusted(tab_id, row):
            refused_downgrade += 1
            continue

        if unit_is_known(prior) and not unit_is_known(row):
            refused_units += 1
            continue

        kept.append(row)

    counts: dict[str, int] = {}
    if refused_downgrade:
        counts["refused_downgrade"] = refused_downgrade
    if refused_units:
        counts["refused_unknown_units"] = refused_units
    return kept, counts
