"""Unit normalisation — one scale for aggregate money, before anything compares.

Vendors report the same fact in different magnitudes. Upstox returns crores,
Yahoo returns rupees, Capital IQ exports vary by sheet. The warehouse stores
aggregate money in **INR million**, so a comparison between two sources is a
comparison of the fact rather than of the vendor's presentation.

Why this has to run before conflict detection
---------------------------------------------
``conflicts.TOLERANCE_PCT`` is 2%. Crores against rupees differ by 10,000,000%,
so without this step every single watched field on every row would be recorded
as a disagreement and the conflict log would carry no signal at all.

What is rescaled
----------------
Only columns declared ``unit=UNIT_INR_MILLION`` in the schema. Prices, per-share
values, share counts, ratios and percentages pass through untouched. A column
nobody has classified is never rescaled, so the failure mode of forgetting to
classify is "not normalised", never "silently corrupted".

Provenance
----------
Each row records what the vendor reported and how it got here:

    sys_reported_unit   the vendor unit as declared or inferred ("crore")
    sys_unit_scale      the multiplier applied to reach INR million (crore -> 10)
    sys_unit_method     "declared" | "source_default" | "assumed_canonical"

The raw value is recoverable as ``stored / scale``, and the version history in
``versions`` keeps the full prior row, so nothing is lost by rescaling in place.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional, Sequence

from institutional_warehouse import db
from institutional_warehouse.schema import Tab, find_tab
from institutional_warehouse.values import to_number

CANONICAL_UNIT = "inr_million"

#: Rupees in one INR million. Derived metrics that divide an aggregate by a
#: share count, or add an aggregate to a market capitalisation, have to bring
#: both sides onto the same scale first — a book value of equity-in-millions
#: over a raw share count is wrong by exactly this factor.
MILLION = 1_000_000.0


def to_rupees(value: Any) -> Optional[float]:
    """An aggregate stored in INR million, expressed in rupees.

    Use wherever a statement aggregate meets a price, a share count or a market
    capitalisation, all of which are held in rupees.
    """
    number = to_number(value)
    return None if number is None else number * MILLION


def to_million(value: Any) -> Optional[float]:
    """Rupees expressed in INR million — the inverse of :func:`to_rupees`."""
    number = to_number(value)
    return None if number is None else number / MILLION

#: Multiplier that converts one unit of money into INR million.
SCALE_TO_MILLION: dict[str, float] = {
    "inr_million": 1.0,
    "million": 1.0,
    "mn": 1.0,
    "inr_mn": 1.0,
    "crore": 10.0,
    "cr": 10.0,
    "inr_crore": 10.0,
    "lakh": 0.1,
    "lac": 0.1,
    "inr_lakh": 0.1,
    "billion": 1000.0,
    "bn": 1000.0,
    "thousand": 0.001,
    "k": 0.001,
    "rupee": 1e-6,
    "rupees": 1e-6,
    "inr": 1e-6,
    "absolute": 1e-6,
    "unit": 1e-6,
}

#: What a source reports in when it does not say. Yahoo's statement API returns
#: absolute rupees; Upstox fundamentals return crores but also send `units_in`,
#: which takes precedence over this table whenever it is present.
SOURCE_DEFAULT_UNIT: dict[str, str] = {
    "yahoo_finance_statements": "rupee",
    "yahoo": "rupee",
    "upstox_fundamentals": "crore",
    "upstox": "crore",
    "capital_iq": "inr_million",
    "capiq": "inr_million",
}

METHOD_DECLARED = "declared"
METHOD_SOURCE_DEFAULT = "source_default"
METHOD_ASSUMED = "assumed_canonical"


def canonical_unit_name(raw: Any) -> Optional[str]:
    """Map a vendor unit label onto a key in SCALE_TO_MILLION."""
    if raw is None:
        return None
    text = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
    if not text:
        return None
    text = text.removeprefix("in_").removeprefix("inr_").removesuffix("s")
    for candidate in (text, f"inr_{text}"):
        if candidate in SCALE_TO_MILLION:
            return candidate
    # "rs_crore", "figures_in_crore" and friends.
    for known in SCALE_TO_MILLION:
        if known != "unit" and known in text:
            return known
    return None


def resolve_unit(*, reported_unit: Any = None, source: str = "") -> tuple[str, float, str]:
    """Decide the unit for a payload: what was declared, else what the source uses."""
    declared = canonical_unit_name(reported_unit)
    if declared:
        return declared, SCALE_TO_MILLION[declared], METHOD_DECLARED

    fallback = SOURCE_DEFAULT_UNIT.get(str(source or "").strip().lower())
    if fallback:
        return fallback, SCALE_TO_MILLION[fallback], METHOD_SOURCE_DEFAULT

    # Nothing known: treat the value as already canonical rather than guessing a
    # scale. Being wrong by a factor of ten million is far worse than being flat.
    return CANONICAL_UNIT, 1.0, METHOD_ASSUMED


def rescaled_columns(tab: Tab) -> list[str]:
    return [c.key for c in tab.columns if c.rescaled]


def normalise_rows(
    tab_id: str,
    rows: Sequence[dict[str, Any]],
    *,
    source: str = "",
    reported_unit: Any = None,
) -> dict[str, Any]:
    """Rescale aggregate money columns to INR million and stamp provenance.

    Rows may carry their own ``units_in`` (as Upstox statements do), which wins
    over the source default for that row.
    """
    tab = find_tab(tab_id)
    if not tab:
        return {"rows": list(rows), "converted": 0, "unit": None, "scale": 1.0}

    targets = rescaled_columns(tab)
    if not targets:
        return {"rows": list(rows), "converted": 0, "unit": None, "scale": 1.0}

    converted = 0
    out: list[dict[str, Any]] = []
    units_seen: set[str] = set()

    for row in rows:
        row_unit = row.get("units_in") or row.get("unit") or reported_unit
        unit, scale, method = resolve_unit(reported_unit=row_unit, source=source)
        units_seen.add(unit)

        new_row = {k: v for k, v in row.items() if k not in ("units_in", "unit")}
        if scale != 1.0:
            for key in targets:
                value = to_number(new_row.get(key))
                if value is None:
                    continue
                new_row[key] = value * scale
                converted += 1

        new_row["sys_reported_unit"] = unit
        new_row["sys_unit_scale"] = scale
        new_row["sys_unit_method"] = method
        out.append(new_row)

    return {
        "rows": out,
        "converted": converted,
        "unit": sorted(units_seen)[0] if len(units_seen) == 1 else None,
        "units_seen": sorted(units_seen),
        "canonical": CANONICAL_UNIT,
    }


# --------------------------------------------------------------------------
# Back-normalisation of rows written before the normaliser existed
# --------------------------------------------------------------------------


def _tabs_with_money(tab_ids: Optional[Iterable[str]] = None) -> list[Tab]:
    from institutional_warehouse.schema import TABS

    wanted = set(tab_ids) if tab_ids else None
    return [t for t in TABS if rescaled_columns(t) and (wanted is None or t.id in wanted)]


def unstamped_summary(tab_ids: Optional[Iterable[str]] = None) -> dict[str, Any]:
    """How many stored rows predate unit stamping, per tab."""
    out: dict[str, Any] = {}
    total = 0
    for tab in _tabs_with_money(tab_ids):
        table = db.physical_table(tab.id)
        try:
            rows = db.count(table, "sys_reported_unit IS NULL")
            stamped = db.count(table, "sys_reported_unit IS NOT NULL")
        except Exception:
            continue
        out[tab.id] = {"unstamped": rows, "stamped": stamped,
                       "money_columns": rescaled_columns(tab)}
        total += rows
    return {"ok": True, "canonical": CANONICAL_UNIT, "unstamped_total": total, "by_tab": out}


def backfill_units(
    *,
    source_units: Optional[dict[str, str]] = None,
    tab_ids: Optional[Iterable[str]] = None,
    dry_run: bool = True,
    actor: str = "system",
) -> dict[str, Any]:
    """Convert and stamp rows written before unit normalisation existed.

    Grouped by the row's own ``source`` so each vendor is converted with its own
    scale. Only rows with no ``sys_reported_unit`` are touched, which makes the
    migration idempotent — running it twice cannot double-scale a row.
    """
    from institutional_warehouse import audit

    units = {k.lower(): v for k, v in (source_units or SOURCE_DEFAULT_UNIT).items()}
    detail: list[dict[str, Any]] = []
    rows_changed = 0
    values_changed = 0

    for tab in _tabs_with_money(tab_ids):
        table = db.physical_table(tab.id)
        targets = rescaled_columns(tab)
        try:
            groups = db.query(
                f"SELECT source, COUNT(*) AS n FROM {table}"
                f" WHERE sys_reported_unit IS NULL GROUP BY source"
            )
        except Exception:
            continue

        for group in groups:
            source = str(group.get("source") or "")
            count = int(group.get("n") or 0)
            if not count:
                continue
            unit, scale, method = resolve_unit(
                reported_unit=units.get(source.lower()), source=source
            )
            entry = {
                "tab": tab.id,
                "source": source or "(unset)",
                "rows": count,
                "unit": unit,
                "scale": scale,
                "method": method,
                "columns_rescaled": targets if scale != 1.0 else [],
            }
            detail.append(entry)
            rows_changed += count
            if scale != 1.0:
                values_changed += count * len(targets)

            if dry_run:
                continue

            sets = [f'"{key}" = "{key}" * ?' for key in targets] if scale != 1.0 else []
            params: list[Any] = [scale] * len(sets)
            sets += ["sys_reported_unit = ?", "sys_unit_scale = ?", "sys_unit_method = ?"]
            params += [unit, scale, method]
            where = "sys_reported_unit IS NULL AND source " + ("= ?" if source else "IS NULL")
            if source:
                params.append(source)
            db.execute(f'UPDATE {table} SET {", ".join(sets)} WHERE {where}', tuple(params))

    if rows_changed and not dry_run:
        audit.record("recalculate", actor=actor,
                     detail={"migration": "unit_back_normalisation",
                             "rows": rows_changed, "canonical": CANONICAL_UNIT})

    return {
        "ok": True,
        "dry_run": dry_run,
        "canonical": CANONICAL_UNIT,
        "rows_stamped": rows_changed,
        "values_rescaled": values_changed,
        "detail": sorted(detail, key=lambda d: -d["rows"]),
    }
