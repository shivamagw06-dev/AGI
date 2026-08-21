"""Find aggregate money stored on the wrong scale. Read-only.

A value wrong by a factor of a million is the most dangerous defect this
warehouse can hold, because it is not obviously wrong anywhere downstream: it
flows into ratios, valuations and rankings as an ordinary number.

Plausibility is validation evidence, not proof of provenance
-------------------------------------------------------------
A row that looks right may still have come from the wrong feed, and a row that
looks wrong is a row to examine, not a row to delete. Nothing here changes,
retires or quarantines anything. It reports row ids.

Signals are kept apart rather than merged into one score, because they are not
equally good and a reader has to know which one fired.

``ratio``      Two rows for the same company and period hold the same field a
               million or ten million fold apart. The strongest signal: no
               business difference between consolidated and standalone, or
               between two vendors, is ever exactly a million-fold, so the
               window is deliberately tight (0.9e6-1.1e6). Requires a peer.
``magnitude``  The stored number cannot be what the column says under any
               reading. India's largest company books about 1e7 INR million, so
               1e8 is ten times that and roughly ten times national GDP.
               Weakest signal, and the only one available where a company has no
               correctly scaled peer row - which is most of the quarterly tab.
``source``     The row's own feed has a documented unit in SOURCE_DEFAULT_UNIT
               and the stored magnitude contradicts it.

Confidence follows from agreement: a row carrying both ``ratio`` and
``magnitude`` has two independent reasons, and one carrying only ``magnitude``
has a heuristic and no witness.
"""

from __future__ import annotations

import collections
import re
from typing import Any, Iterable, Optional

from institutional_warehouse import db, units

#: Aggregate money, stored in INR million. Per-share and ratio columns are
#: excluded: a scale test is meaningless on eps, book_value or a share count.
MONEY_FIELDS = (
    "revenue", "gross_profit", "ebitda", "ebit", "pbt", "pat", "assets",
    "equity", "debt", "cash", "current_assets", "current_liabilities",
    "inventory", "working_capital", "capex", "cfo", "cfi", "cff",
    "free_cash_flow",
)

#: Ten times the largest revenue any Indian company books, and about ten times
#: national GDP. Nothing real reaches it.
IMPOSSIBLE_MILLION = 1e8

#: Only gaps that cannot be a business difference. 10x is excluded on purpose -
#: a consolidated figure really can be ten times its standalone counterpart.
SCALE_GAPS = ((0.9e6, 1.1e6, "rupees stored as INR million"),
              (0.9e7, 1.1e7, "crore stored as rupees"))

#: A company-period group holds a handful of rows. The cap keeps the pairwise
#: comparison from becoming quadratic if a pathological group ever appears, and
#: is reported when it bites rather than silently truncating.
MAX_PEERS_COMPARED = 24

TABS = ("financials_annual", "financials_quarterly")
_PERIOD_FIELD = {"financials_annual": "fiscal_year",
                 "financials_quarterly": "fiscal_period"}


def _num(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if out != out or out == 0 else out


def fold_period(tab_id: str, label: Any) -> Optional[str]:
    """Fold the spellings of one period together.

    Needed because the natural key excludes source, so the only place two feeds
    hold the same fact is across rows whose period label or statement type
    differs. Without folding there is nothing to compare and the ratio signal
    reports zero - which is exactly what it did before this existed.
    """
    text = str(label or "").upper().replace(" ", "")
    if not text:
        return None
    if tab_id == "financials_annual":
        match = re.search(r"(\d{4})", text)
        if match:
            return "FY" + match.group(1)
        match = re.search(r"FY(\d{2})$", text)
        return "FY20" + match.group(1) if match else None
    match = re.search(r"(\d{4}).*?Q([1-4])", text) or re.search(r"Q([1-4]).*?(\d{4})", text)
    if match:
        first, second = match.groups()
        year, quarter = (first, second) if len(first) == 4 else (second, first)
        return f"FY{year}Q{quarter}"
    match = re.search(r"FY(\d{2})Q([1-4])", text)
    return f"FY20{match.group(1)}Q{match.group(2)}" if match else None


def _documented_unit(source: Any) -> Optional[str]:
    return units.SOURCE_DEFAULT_UNIT.get(str(source or "").strip().lower())


def census(tab_id: str, *, symbols: Optional[Iterable[str]] = None,
           sample_rows: int = 25) -> dict[str, Any]:
    """Every row in the tab, classified. Writes nothing."""
    if tab_id not in TABS:
        return {"ok": False, "error": f"tab_not_eligible:{tab_id}"}

    db.init()
    table = db.physical_table(tab_id)
    period_field = _PERIOD_FIELD[tab_id]
    wanted = {str(s).upper() for s in symbols} if symbols else None

    if wanted is not None:
        # The API caps this set before calling us. Do not enumerate the whole
        # table and filter afterward: that would make a bounded response hide an
        # unbounded database scan.
        all_symbols = sorted(s for s in wanted if s)
    else:
        # Offline census path. This is intentionally unrestricted and is not
        # exposed by the HTTP endpoint.
        all_symbols = [str(r.get("symbol") or "") for r in db.query(
            f"SELECT DISTINCT symbol FROM {table} WHERE sys_published = 1 ORDER BY symbol")]
        all_symbols = [s for s in all_symbols if s]

    ratio_hits: dict[str, set[str]] = {}
    magnitude_hits: dict[str, set[str]] = {}
    source_hits: dict[str, set[str]] = {}
    meta: dict[str, dict[str, Any]] = {}
    by_writer: collections.Counter = collections.Counter()
    writer_totals: collections.Counter = collections.Counter()
    by_field: collections.Counter = collections.Counter()
    by_period: collections.Counter = collections.Counter()
    by_company: collections.Counter = collections.Counter()
    total_rows = 0

    # Per company, so the whole tab is never held at once - these tabs are
    # 69,156 and 33,666 rows of seventy columns.
    for symbol in all_symbols:
        rows = db.query(
            f"SELECT * FROM {table} WHERE sys_published = 1 AND symbol = ?", (symbol,))
        total_rows += len(rows)
        facts: dict[tuple, list[tuple[float, dict]]] = collections.defaultdict(list)
        for row in rows:
            rid = str(row.get("row_id"))
            writer = (str(row.get("source") or "?"),
                      str(row.get("sys_unit_method") or "NEVER_NORMALISED"))
            writer_totals[writer] += 1
            meta[rid] = {"symbol": symbol, "period": row.get(period_field),
                         "source": row.get("source"),
                         "unit_method": row.get("sys_unit_method") or "NEVER_NORMALISED",
                         "reported_unit": row.get("sys_reported_unit"),
                         "statement_type": row.get("statement_type")}
            folded = fold_period(tab_id, row.get(period_field))
            declared = _documented_unit(row.get("source"))
            for field in MONEY_FIELDS:
                value = _num(row.get(field))
                if value is None:
                    continue
                if folded:
                    facts[(folded, field)].append((abs(value), row))
                if abs(value) > IMPOSSIBLE_MILLION:
                    magnitude_hits.setdefault(rid, set()).add(field)
                    # A feed that documents rupees storing a number this large
                    # means the conversion never ran, which is a stronger claim
                    # than the size alone.
                    if declared == "rupee":
                        source_hits.setdefault(rid, set()).add(field)

        for (_folded, field), values in facts.items():
            if len(values) < 2:
                continue
            # Pairwise, not every-value-against-the-smallest. With three or more
            # peers a 1e6 pair can sit entirely among non-minimum values - a row
            # in rupees next to another in rupees and one in millions - and
            # comparing only to the minimum misses it. Bounded because a period
            # group is a handful of rows, not a tab.
            if len(values) > MAX_PEERS_COMPARED:
                values = sorted(values, key=lambda vr: vr[0])[:MAX_PEERS_COMPARED]
            for i, (left, left_row) in enumerate(values):
                for right, right_row in values[i + 1:]:
                    low_v, high_v = (left, right) if left <= right else (right, left)
                    if not low_v:
                        continue
                    gap = high_v / low_v
                    if any(low <= gap <= high for low, high, _ in SCALE_GAPS):
                        # The larger side is the one holding an unconverted value.
                        bigger = left_row if left >= right else right_row
                        ratio_hits.setdefault(str(bigger.get("row_id")), set()).add(field)

    suspect = set(ratio_hits) | set(magnitude_hits)
    for rid in suspect:
        info = meta.get(rid, {})
        by_writer[(info.get("source"), info.get("unit_method"))] += 1
        by_company[info.get("symbol")] += 1
        by_period[fold_period(tab_id, info.get("period")) or "UNPARSED"] += 1
        for field in (ratio_hits.get(rid, set()) | magnitude_hits.get(rid, set())):
            by_field[field] += 1

    both = set(ratio_hits) & set(magnitude_hits)
    return {
        "ok": True,
        "read_only": True,
        "tab": tab_id,
        "rows": total_rows,
        "totals": {
            "rows_to_examine": len(suspect),
            "ratio_corroborated": len(ratio_hits),
            "magnitude_impossible": len(magnitude_hits),
            "contradicts_documented_unit": len(source_hits),
            "two_signals_agree": len(both),
            "ratio_only": len(set(ratio_hits) - set(magnitude_hits)),
            "magnitude_only": len(set(magnitude_hits) - set(ratio_hits)),
        },
        "by_writer": {f"{s}|{m}": {"suspect": n, "of": writer_totals[(s, m)]}
                      for (s, m), n in by_writer.most_common()},
        "by_field": dict(by_field.most_common()),
        "by_period": dict(by_period.most_common(20)),
        "by_company": dict(by_company.most_common(20)),
        "sample": [
            {"row_id": rid, **meta.get(rid, {}),
             "confidence": ("two_signals" if rid in both
                            else "ratio" if rid in ratio_hits else "magnitude_only"),
             "fields": sorted(ratio_hits.get(rid, set()) | magnitude_hits.get(rid, set()))}
            for rid in sorted(suspect)[:sample_rows]],
    }


def manifest(tab_id: str) -> dict[str, Any]:
    """Every suspect row id with its evidence, for review and remediation.

    Returned rather than written anywhere. A remediation that cannot name the
    exact rows it touched cannot be reversed, and this is the list it names.
    """
    report = census(tab_id, sample_rows=10 ** 9)
    return {"ok": True, "read_only": True, "tab": tab_id,
            "rows_to_examine": report["totals"]["rows_to_examine"],
            "rows": report["sample"]}
