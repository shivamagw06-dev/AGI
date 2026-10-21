"""Safe one-time repair for annual Upstox data that was labelled as quarterly Q4."""

from __future__ import annotations

from institutional_warehouse import store


def repair_annual_as_quarterly(
    *, actor: str = "system", apply: bool = False, row_ids: list[str] | None = None
) -> dict:
    """Review legacy Q4 records and retire only explicitly approved source rows."""
    annual = store.all_rows("financials_annual", limit=50000)
    quarterly = store.all_rows("financials_quarterly", limit=50000)
    index = {
        (r.get("symbol"), r.get("fiscal_year"), r.get("statement_type")): r
        for r in annual
        if str(r.get("source") or "").lower() == "upstox"
    }
    exact_candidates: list[str] = []
    q4_suspects: list[dict] = []
    for row in quarterly:
        if (
            str(row.get("source") or "").lower() != "upstox"
            or not str(row.get("fiscal_period") or "").upper().endswith("Q4")
        ):
            continue
        row_id = str(row.get("row_id") or "")
        if not row_id:
            continue
        q4_suspects.append({
            "row_id": row_id,
            "symbol": row.get("symbol"),
            "fiscal_period": row.get("fiscal_period"),
            "fiscal_year": row.get("fiscal_year"),
            "statement_type": row.get("statement_type"),
            "revenue": row.get("revenue"),
            "pbt": row.get("pbt"),
            "pat": row.get("pat"),
            "eps": row.get("eps"),
            "created_at": (row.get("_meta") or {}).get("created_at"),
        })
        annual_row = index.get((row.get("symbol"), row.get("fiscal_year"), row.get("statement_type")))
        if annual_row:
            fields = ("revenue", "pbt", "pat", "eps")
            shared = [field for field in fields if row.get(field) is not None and annual_row.get(field) is not None]
            if shared and all(float(row[field]) == float(annual_row[field]) for field in shared):
                exact_candidates.append(row_id)
    suspect_ids = {row["row_id"] for row in q4_suspects}
    requested = {str(row_id) for row_id in (row_ids or []) if str(row_id)}
    selected = sorted(requested & suspect_ids) if requested else exact_candidates
    result = {
        "ok": True,
        "exact_duplicate_candidates": len(exact_candidates),
        "legacy_q4_suspects": len(q4_suspects),
        "suspects": q4_suspects[:100],
        "selected": len(selected),
        "row_ids": selected[:100],
        "rejected_row_ids": sorted(requested - suspect_ids)[:100],
        "applied": False,
        "rule": "Upstox Q4 records are review candidates; apply requires their exact row IDs, unless an annual/Q4 duplicate is proven automatically",
    }
    if apply and selected:
        result.update(store.retire_rows(
            "financials_quarterly",
            selected,
            actor=actor,
            reason="upstox annual full_statement mislabelled as quarterly Q4",
        ))
        result["applied"] = True
    return result
