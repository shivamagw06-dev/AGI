"""Per-company evidence-class coverage matrix (why a company isn't ICC yet).

Primary signal: ICF `score_evidence_classes` (real evidence-class presence).
Fallback (ICF unreachable): IKT structured-table presence — still real,
never fabricated; simply narrower.
"""

from __future__ import annotations

from typing import Any

COVERAGE_MATRIX_VERSION = "coverage-matrix-v1"

# Coverage-matrix column → ICF evidence_class ids that satisfy it
_COLUMN_TO_ICF_CLASSES: dict[str, tuple[str, ...]] = {
    "financials": ("financial_statements", "quarterly_results"),
    "annual_reports": ("annual_reports",),
    "presentations": ("earnings_presentations",),
    "transcripts": ("earnings_call_transcripts",),
    "shareholding": ("shareholding",),
    "corporate_actions": ("corporate_actions",),
}

# Coverage-matrix column → IKT table used as a fallback presence check
_COLUMN_TO_IKT_TABLE: dict[str, str] = {
    "financials": "financial_statements",
    "annual_reports": "annual_reports",
    "presentations": "investor_presentations",
    "transcripts": "earnings_call_transcripts",
    "shareholding": "shareholding",
    "corporate_actions": "corporate_actions",
}

COLUMNS = ("financials", "annual_reports", "presentations", "transcripts", "shareholding", "corporate_actions")


def _from_icf(ticker: str) -> dict[str, Any] | None:
    try:
        from institutional_coverage_factory.scorer.score import score_evidence_classes
        from institutional_coverage_factory.validator.icc import icc_status_for

        scored = score_evidence_classes(ticker) or {}
        if not scored.get("ok", True) and not scored.get("classes"):
            return None
        classes = scored.get("classes") or {}
        row: dict[str, Any] = {}
        for col, icf_ids in _COLUMN_TO_ICF_CLASSES.items():
            row[col] = any(bool((classes.get(cid) or {}).get("present")) for cid in icf_ids)
        icc = icc_status_for(ticker) or {}
        row["research_ready"] = bool(icc.get("institutional_coverage_complete"))
        row["coverage_pct"] = scored.get("coverage_pct")
        row["missing_classes"] = scored.get("missing_classes")
        row["source"] = "institutional_coverage_factory"
        return row
    except Exception:
        return None


def _from_ikt(ticker: str) -> dict[str, Any]:
    from institutional_knowledge_tables.store import get_table

    row: dict[str, Any] = {}
    for col, table in _COLUMN_TO_IKT_TABLE.items():
        try:
            t = get_table(ticker, table)
            populated = bool(t.get("populated_fields")) or bool(t.get("rows"))
            row[col] = populated
        except Exception:
            row[col] = False
    row["research_ready"] = False
    row["coverage_pct"] = None
    row["missing_classes"] = [c for c in COLUMNS if not row.get(c)]
    row["source"] = "institutional_knowledge_tables_fallback"
    return row


def matrix_for_company(ticker: str) -> dict[str, Any]:
    t = str(ticker or "").strip().upper()
    row = _from_icf(t)
    if row is None:
        row = _from_ikt(t)
    return {"ok": True, "version": COVERAGE_MATRIX_VERSION, "ticker": t, **row}


def matrix_for_universe(*, scope: str = "nifty500", limit: int = 20) -> dict[str, Any]:
    """Bounded scan — evidence scoring is per-company work, not free.

    scope: nifty50 | nifty500 | all (all uses the full NSE trading book order)
    """
    from knowledge_factory.historical_depth.universe_priority import prioritised_universe

    universe = prioritised_universe()
    s = (scope or "nifty500").strip().lower()
    if s == "nifty50":
        from knowledge_factory.historical_depth.universe_priority import nifty_50

        universe = [t for t in universe if t in set(nifty_50())]
    elif s == "nifty500":
        from knowledge_factory.historical_depth.universe_priority import nifty_500

        universe = [t for t in universe if t in set(nifty_500())]
    # "all" keeps the full prioritised order

    lim = max(1, min(int(limit), 200))
    tickers = universe[:lim]
    rows = [matrix_for_company(t) for t in tickers]
    return {
        "ok": True,
        "version": COVERAGE_MATRIX_VERSION,
        "scope": s,
        "scanned": len(rows),
        "universe_size": len(universe),
        "truncated": len(universe) > lim,
        "columns": list(COLUMNS) + ["research_ready"],
        "rows": rows,
    }
