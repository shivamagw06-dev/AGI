"""NSE IND-AS XBRL extraction adapter.

Wraps P2.1 ``earnings_intelligence`` — does not duplicate tag maps.
No business logic beyond structured field capture.
"""

from __future__ import annotations

from typing import Any


def extract_from_earnings_pack(pack: dict[str, Any]) -> dict[str, Any]:
    """Flatten a P2.1 financial pack into extractor-local field dicts per period.

    Output shape is Extraction Layer compatible (pre-normalization).
    """
    periods: list[dict[str, Any]] = []
    # earnings_intelligence uses quarter_history / annual_history;
    # FSE and older packs also use quarters / annuals.
    series_aliases = (
        (("quarters", "quarter_history", "quarterly", "q_history"), "quarterly"),
        (("annuals", "annual_history", "annual", "yearly"), "annual"),
    )
    stmts = pack.get("statements") if isinstance(pack.get("statements"), dict) else {}
    for aliases, period_type in series_aliases:
        rows: list[Any] = []
        for series_key in aliases:
            candidate = pack.get(series_key)
            if isinstance(candidate, list) and candidate:
                rows = candidate
                break
            nested = stmts.get(series_key)
            if isinstance(nested, list) and nested:
                rows = nested
                break
        if not isinstance(rows, list) or not rows:
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            fields: dict[str, Any] = {}
            for block in ("income_statement", "balance_sheet", "cash_flow", "income", "balance", "cashflow"):
                block_data = row.get(block)
                if isinstance(block_data, dict):
                    for k, v in block_data.items():
                        if isinstance(v, dict) and "value" in v:
                            fields[k] = v
                        else:
                            fields[k] = {"value": v, "unit_scale": row.get("unit_scale") or "crores"}
            # Also accept flat metrics
            for k, v in row.items():
                if k in (
                    "income_statement",
                    "balance_sheet",
                    "cash_flow",
                    "income",
                    "balance",
                    "cashflow",
                    "period_end",
                    "fiscal_year",
                    "fiscal_period",
                    "period_type",
                ):
                    continue
                if k not in fields and isinstance(v, (int, float)):
                    fields[k] = {"value": v, "unit_scale": row.get("unit_scale") or "crores"}

            periods.append(
                {
                    "extractor": "nse_indas_xbrl_v1",
                    "period_type": row.get("period_type") or period_type,
                    "period_end": row.get("period_end") or row.get("end_date"),
                    "fiscal_year": row.get("fiscal_year"),
                    "fiscal_period": row.get("fiscal_period") or row.get("period"),
                    "fields": fields,
                    "confidence": float(row.get("confidence") or pack.get("confidence") or 0.0),
                    "source_refs": row.get("source_refs") or row.get("evidence") or [],
                    "unknown_fields": row.get("unknown_fields") or [],
                    "errors": row.get("errors") or [],
                }
            )

    return {
        "extractor": "nse_indas_xbrl_v1",
        "adapter": "earnings_intelligence",
        "periods": periods,
        "layer": "extraction",
    }


def soft_build_pack(ticker: str, **kwargs: Any) -> dict[str, Any]:
    """Best-effort call into P2.1 pack builder (optional dependency at runtime)."""
    try:
        from earnings_intelligence.pack import build_financial_pack

        return build_financial_pack(ticker, **kwargs)
    except Exception as exc:  # pragma: no cover - soft fail
        return {"ok": False, "error": str(exc), "ticker": ticker}
