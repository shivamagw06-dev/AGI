"""Two explicit modes for quarterly statements: trusted, and unverified fallback.

Upstox is the only quarterly feed that declares its units. All 739 sampled
Upstox rows carry sys_unit_method "declared" with reported_unit "crore"; every
other feed lands "assumed_canonical" or nothing at all, and a census of 33,666
quarterly rows found 44.4% holding values impossible for INR million.

Blocking those feeds was the obvious response and the wrong one. Upstox reaches
145 of 776 companies, so refusing the rest would stop quarterly updates for
81.3% of the universe - trading bad numbers for no numbers. They keep writing,
clearly labelled, and are excluded from anything that treats a number as fact.

Trust is computed here, at read time, from the row's source and unit method
rather than read from a stored flag. Two reasons. The stored `is_canonical`
column is null on every quarterly row today because it is stamped at write time
and these rows predate it, so a flag-based rule would report nothing as trusted.
And deriving it on read means no historical row has to be written to make this
work.

    TRUSTED     Upstox, declared units. Valuations, rankings, factors and
                canonical analytics may read these.
    FALLBACK    Everything else. Visible, labelled, and excluded from the above
                unless a caller asks for it by name.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Tuple

#: Feeds whose quarterly rows may be treated as fact. Membership is not a
#: judgement about the vendor - it is whether the feed says what unit it
#: reports in.
TRUSTED_QUARTERLY_SOURCES = frozenset({"upstox", "upstox_fundamentals"})

#: Annual is governed separately: FY2017-FY2026 is owned by the Capital IQ
#: workbook and protected by ownership.check_protected_annual_slice. Nothing
#: here changes that.
TRUSTED_ANNUAL_SOURCES = frozenset({
    "capital_iq_workbook", "capital_iq", "capiq",
    "upstox", "upstox_fundamentals",
})

TRUSTED = "trusted"
FALLBACK = "unverified_fallback"

#: A declared unit is one the feed stated. "assumed_canonical" is the absence of
#: a unit wearing the name of one, and it is what put absolute rupees in a
#: column of INR million.
DECLARED_UNIT_METHODS = frozenset({"declared", "source_default"})


def _meta(row: Dict[str, Any]) -> Dict[str, Any]:
    meta = row.get("_meta")
    return meta if isinstance(meta, dict) else {}


def unit_method_of(row: Dict[str, Any]) -> str:
    return str(row.get("sys_unit_method") or _meta(row).get("unit_method") or "")


def trusted_sources(tab_id: str) -> frozenset:
    if tab_id == "financials_quarterly":
        return TRUSTED_QUARTERLY_SOURCES
    if tab_id == "financials_annual":
        return TRUSTED_ANNUAL_SOURCES
    return frozenset()


def is_trusted(tab_id: str, row: Dict[str, Any]) -> bool:
    """Whether this row may be read as fact.

    Both conditions, not either: a trusted feed that failed to declare a unit on
    a particular row is not trusted for that row. The source says who supplied
    it; the unit method says whether the magnitude was established.
    """
    source = str(row.get("source") or "").strip().lower()
    if source not in trusted_sources(tab_id):
        return False
    return unit_method_of(row).strip().lower() in DECLARED_UNIT_METHODS


def classify(tab_id: str, row: Dict[str, Any]) -> str:
    return TRUSTED if is_trusted(tab_id, row) else FALLBACK


def partition(tab_id: str, rows: Iterable[Dict[str, Any]]
              ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split rows into (trusted, fallback) without dropping either."""
    trusted: List[Dict[str, Any]] = []
    fallback: List[Dict[str, Any]] = []
    for row in rows or []:
        (trusted if is_trusted(tab_id, row) else fallback).append(row)
    return trusted, fallback


def select(tab_id: str, rows: Sequence[Dict[str, Any]], *,
           include_unverified: bool = False) -> List[Dict[str, Any]]:
    """Rows a reader may use. Trusted only, unless asked otherwise.

    The default is the point. A caller that does nothing special gets data whose
    magnitude was declared by the feed that supplied it. Reading unverified rows
    is possible and has to be spelled out, so it appears in the calling code
    rather than in a default nobody revisits.
    """
    trusted, fallback = partition(tab_id, rows)
    if not include_unverified:
        return trusted
    # Trusted first, so a caller taking the first row per period gets the
    # declared one wherever it exists.
    return trusted + [dict(row, trust=FALLBACK) for row in fallback]


def label(tab_id: str, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Every row, each carrying its own trust mode. Nothing filtered."""
    return [dict(row, trust=classify(tab_id, row)) for row in rows or []]


def coverage(tab_id: str, rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """What a reader actually gets, stated rather than implied."""
    trusted, fallback = partition(tab_id, rows)
    t_cos = {str(r.get("symbol")) for r in trusted}
    f_cos = {str(r.get("symbol")) for r in fallback}
    return {
        "tab": tab_id,
        "trusted_rows": len(trusted),
        "fallback_rows": len(fallback),
        "trusted_companies": len(t_cos),
        "fallback_only_companies": len(f_cos - t_cos),
        "trusted_sources": sorted(trusted_sources(tab_id)),
        "note": ("fallback rows are excluded from valuations, rankings, factors "
                 "and canonical analytics unless a caller passes "
                 "include_unverified"),
    }
