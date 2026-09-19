"""Persist parsed financial statement series into historical_depth when available.

FSE-02.1: keep HD dual-write; when no XBRL was ingested upstream, also submit the
pack as structured raw evidence through FSE-02 canonical ingest.
"""

from __future__ import annotations

from typing import Any


def _write_hd(pack: dict[str, Any]) -> dict[str, Any]:
    ticker = str(pack.get("ticker") or "").upper()
    if not ticker or not pack.get("ok"):
        return {"written": 0, "ticker": ticker, "skipped": True}
    try:
        from knowledge_factory.historical_depth import store as hd_store
        from knowledge_factory.historical_depth.schema import pit_record
    except Exception as exc:  # pragma: no cover
        return {"written": 0, "ticker": ticker, "error": str(exc)[:160]}

    pits = []
    for row in list(pack.get("quarter_history") or []) + list(pack.get("annual_history") or []):
        pe = row.get("period_end")
        if not pe:
            continue
        inc = row.get("income_statement") or {}
        bal = row.get("balance_sheet") or {}
        cf = row.get("cash_flow") or {}
        freq = row.get("frequency") or "quarterly"
        pits.append(
            pit_record(
                entity=ticker,
                kind="financials_quarterly" if freq == "quarterly" else "financials_annual",
                period=str(row.get("quarter_label") or row.get("fiscal_year_label") or pe),
                period_end=str(pe)[:10],
                available_from=str(row.get("filing_date") or pe)[:10],
                payload={
                    "statement": "mixed",
                    "frequency": freq,
                    "revenue": inc.get("revenue_from_operations"),
                    "ebitda": inc.get("ebitda"),
                    "ebit": inc.get("ebit"),
                    "net_income": inc.get("pat_owners") or inc.get("pat"),
                    "eps": inc.get("eps_basic"),
                    "ocf": cf.get("operating_cash_flow"),
                    "fcf": cf.get("free_cash_flow"),
                    "cash": bal.get("cash"),
                    "total_debt": bal.get("total_debt"),
                    "equity": bal.get("total_equity"),
                    "source": "earnings_intelligence_p21",
                    "units_in": row.get("units_in"),
                    "provider": row.get("provider"),
                    "parser_path": row.get("parser_path"),
                    "source_document": row.get("xbrl_url"),
                    "unit_resolution": row.get("unit_resolution"),
                    "scaled_from_integrated_lakhs": bool(
                        row.get("scaled_from_integrated_lakhs")
                    ),
                },
                source="earnings_intelligence_p21",
                confidence=float(pack.get("confidence") or 0.9),
            )
        )
    # Store under both series names used by HD
    q_pits = [p for p in pits if (p.get("payload") or {}).get("frequency") == "quarterly"]
    a_pits = [p for p in pits if (p.get("payload") or {}).get("frequency") == "annual"]
    written = 0
    if q_pits:
        hd_store.put_series("financials_quarterly", ticker, q_pits)
        written += len(q_pits)
    if a_pits:
        hd_store.put_series("financials_annual", ticker, a_pits)
        written += len(a_pits)
    return {"written": written, "ticker": ticker, "skipped": False}


def _any_fse_xbrl_ingested(pack: dict[str, Any]) -> bool:
    for row in list(pack.get("quarter_history") or []) + list(pack.get("annual_history") or []):
        if row.get("fse_xbrl_ingested") or (row.get("fse_ingest") or {}).get("evidence_id"):
            return True
    return bool(pack.get("fse_xbrl_ingested"))


def persist_pack(pack: dict[str, Any]) -> dict[str, Any]:
    """Dual-write path: HD always (migration rule); FSE-02 when no XBRL ingest ran."""
    hd_result = _write_hd(pack)
    fse_result: dict[str, Any] | None = None
    try:
        from financial_statements_engine.collection.flags import (
            canonical_ingest_enabled,
            dual_write_hd_enabled,
        )
        from financial_statements_engine.collection.ingest import ingest_structured_json
    except Exception:  # pragma: no cover
        return {**hd_result, "dual_write_hd": True, "fse_ingest": None}

    # HD writers stay enabled this phase regardless of flag (fail-safe).
    _ = dual_write_hd_enabled()

    if canonical_ingest_enabled() and not _any_fse_xbrl_ingested(pack) and not hd_result.get("skipped"):
        ticker = str(pack.get("ticker") or "").upper()
        period_end = None
        period_type = "annual"
        for row in list(pack.get("annual_history") or []) + list(pack.get("quarter_history") or []):
            if row.get("period_end"):
                period_end = str(row.get("period_end"))[:10]
                period_type = "annual" if (row.get("frequency") or "") == "annual" else "quarterly"
                break
        # Lightweight evidence payload — not a second parse path.
        evidence_payload = {
            "ticker": ticker,
            "source": "earnings_intelligence_p21",
            "confidence": pack.get("confidence"),
            "annual_n": len(pack.get("annual_history") or []),
            "quarterly_n": len(pack.get("quarter_history") or []),
            "period_end": period_end,
        }
        fse_result = ingest_structured_json(
            ticker=ticker,
            payload=evidence_payload,
            source="earnings_intelligence_p21",
            document_type="structured_financials",
            period_type=period_type,
            period_end=period_end,
            collector="earnings_intelligence",
            filing_type=period_type,
        )

    return {
        **hd_result,
        "dual_write_hd": True,
        "fse_ingest": fse_result,
        "fse_xbrl_already_ingested": _any_fse_xbrl_ingested(pack),
    }
