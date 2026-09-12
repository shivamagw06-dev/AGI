"""Deterministic selection rules for reported financial statements.

Capital IQ workbook rows are AGI's audited long-term annual history. Live
providers remain useful, particularly for the most recent quarter, but must not
silently replace the selected annual record for a fiscal year.
"""

from __future__ import annotations

import re
from typing import Any, Iterable


def is_capiq_workbook(row: dict[str, Any]) -> bool:
    """True only for the controlled CapIQ workbook import."""
    return (
        str(row.get("statement_version") or "").lower().startswith("capiq_workbook_")
        or str(row.get("source") or "").lower() == "capital_iq_workbook"
    )


def fiscal_sort_key(value: Any) -> tuple[int, str]:
    text = str(value or "").strip().upper()
    years = re.findall(r"\d{2,4}", text)
    year = int(years[0]) if years else 0
    if year and year < 100:
        year += 2000
    return year, text


def _selection_rank(row: dict[str, Any], *, annual: bool) -> tuple[int, int, int, str]:
    from institutional_warehouse import statement_trust

    statement_type = str(row.get("statement_type") or "").upper()
    basis_rank = 0 if statement_type == "CONSOLIDATED" else 1
    # CapIQ is the canonical annual history. Quarterly data deliberately keeps
    # its provider order because CapIQ is not a live quarterly feed.
    source_rank = 0 if annual and is_capiq_workbook(row) else 1
    # A declared unit outranks a recent write. Without this the quarterly tie
    # break fell through to last_updated, so the feed that wrote most recently
    # won the period - which is how a row of unknown magnitude becomes the
    # answer over one whose feed said what unit it reports in.
    tab = "financials_annual" if annual else "financials_quarterly"
    trust_rank = 0 if statement_trust.is_trusted(tab, row) else 1
    updated = str(row.get("sys_updated_at") or row.get("last_updated") or "")
    return basis_rank, trust_rank, source_rank, updated


def canonical_statement_series(
    rows: Iterable[dict[str, Any]], *, period_key: str, annual: bool,
    include_unverified: bool = False,
) -> list[dict[str, Any]]:
    """Return one reported statement per fiscal period with clear lineage.

    The selection is consolidated-first, then declared-unit-first, then
    CapIQ-first for annual, then most recently updated.

    Trusted only by default. Ranking alone was not enough: it picks the best row
    for a period, and then returns it whatever its trust - so a period no
    declared feed covers still handed an unverified row to every caller
    automatically. On the quarterly tab that was 6,616 of 7,355 selections.

    Reading unverified rows now takes include_unverified, so it appears at the
    call site rather than in a default nobody revisits. Every returned row
    carries a `trust` label either way.
    """
    from institutional_warehouse import statement_trust

    tab_id = "financials_annual" if annual else "financials_quarterly"
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        period = str(row.get(period_key) or "").strip()
        if period:
            grouped.setdefault(period, []).append(row)
    selected = [min(candidates, key=lambda row: _selection_rank(row, annual=annual))
                for candidates in grouped.values()]
    labelled = statement_trust.label(tab_id, selected)
    if not include_unverified:
        labelled = [row for row in labelled
                    if row.get("trust") == statement_trust.TRUSTED]
    return sorted(labelled, key=lambda row: fiscal_sort_key(row.get(period_key)))
