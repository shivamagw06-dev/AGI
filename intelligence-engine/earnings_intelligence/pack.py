"""Financial Statements Pack builder — discovery + XBRL + TTM + earnings intelligence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from earnings_intelligence.analytics import (
    build_ttm,
    earnings_intelligence,
    growth_vs_prior,
    statement_metrics,
)
from earnings_intelligence.discovery import discover_filings
from earnings_intelligence.schema import (
    DEFAULT_ANNUAL_XBRL,
    DEFAULT_QUARTERLY_XBRL,
    ENGINE_CODE,
    FRESHNESS_SLA_DAYS,
    VERSION,
)
from earnings_intelligence.xbrl import enrich_filing_with_xbrl


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _age_days(iso_date: str | None) -> float | None:
    if not iso_date:
        return None
    try:
        dt = datetime.strptime(iso_date[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0)
    except ValueError:
        return None


def _find_yoy(rows: list[dict[str, Any]], current: dict[str, Any] | None) -> dict[str, Any] | None:
    if not current or not current.get("period_end"):
        return None
    try:
        cur = datetime.strptime(current["period_end"][:10], "%Y-%m-%d")
    except ValueError:
        return None
    target_year = cur.year - 1
    for r in rows:
        pe = r.get("period_end")
        if not pe:
            continue
        try:
            dt = datetime.strptime(pe[:10], "%Y-%m-%d")
        except ValueError:
            continue
        if dt.year == target_year and dt.month == cur.month:
            return r
    return None


def _slim_filing(row: dict[str, Any]) -> dict[str, Any]:
    st = row.get("statements") or {}
    return {
        "period_end": row.get("period_end"),
        "period_start": row.get("period_start"),
        "quarter_label": row.get("quarter_label"),
        "fiscal_year_label": row.get("fiscal_year_label"),
        "filing_date": row.get("filing_date"),
        "frequency": row.get("frequency"),
        "consolidated": row.get("consolidated"),
        "source": row.get("source"),
        "xbrl_url": row.get("xbrl_url"),
        "xbrl_ok": row.get("xbrl_ok"),
        "has_income": row.get("has_income"),
        "has_balance": row.get("has_balance"),
        "has_cash_flow": row.get("has_cash_flow"),
        "has_segments": row.get("has_segments"),
        "income_statement": st.get("income_statement"),
        "balance_sheet": st.get("balance_sheet"),
        "cash_flow": st.get("cash_flow"),
        "segments": st.get("segments") or [],
        "income_ytd": st.get("income_ytd"),
        # FSE-02.1 dual-path markers (kept small; no raw bytes)
        "fse_xbrl_ingested": bool(row.get("fse_xbrl_ingested")),
        "fse_ingest": row.get("fse_ingest"),
    }


def build_financial_pack(
    symbol: str,
    *,
    force: bool = False,
    quarterly_xbrl: int = DEFAULT_QUARTERLY_XBRL,
    annual_xbrl: int = DEFAULT_ANNUAL_XBRL,
    opener=None,
    injected_integrated: list[dict[str, Any]] | None = None,
    injected_quarterly: list[dict[str, Any]] | None = None,
    injected_annual: list[dict[str, Any]] | None = None,
    injected_xbrl_by_url: dict[str, bytes | str] | None = None,
    skip_xbrl: bool = False,
) -> dict[str, Any]:
    key = (symbol or "").upper()
    t0 = datetime.now(timezone.utc)
    index = discover_filings(
        key,
        opener=opener,
        injected_integrated=injected_integrated,
        injected_quarterly=injected_quarterly,
        injected_annual=injected_annual,
    )
    errors = list(index.get("errors") or [])
    q_rows = list(index.get("quarterly") or [])
    a_rows = list(index.get("annual") or [])
    xmap = injected_xbrl_by_url or {}

    def enrich_list(rows: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
        out = []
        for i, r in enumerate(rows):
            if skip_xbrl or i >= max(0, int(n)):
                out.append(dict(r))
                continue
            url = str(r.get("xbrl_url") or "")
            try:
                row = dict(r)
                row.setdefault("ticker", key)
                row.setdefault("symbol", key)
                out.append(enrich_filing_with_xbrl(row, opener=opener, injected_xbrl=xmap.get(url)))
            except Exception as exc:  # noqa: BLE001
                row = dict(r)
                row["xbrl_error"] = f"{type(exc).__name__}:{str(exc)[:120]}"
                out.append(row)
                errors.append(f"xbrl:{r.get('period_end')}:{exc}")
        return out

    q_enriched = enrich_list(q_rows, quarterly_xbrl)
    a_enriched = enrich_list(a_rows, annual_xbrl)

    latest_q = next((r for r in q_enriched if r.get("has_income") or r.get("statements")), q_enriched[0] if q_enriched else None)
    prior_q = q_enriched[1] if len(q_enriched) > 1 else None
    yoy_q = _find_yoy(q_enriched, latest_q)
    latest_a = next(
        (r for r in a_enriched if r.get("has_income") or r.get("has_balance") or r.get("statements")),
        a_enriched[0] if a_enriched else None,
    )
    prior_a = a_enriched[1] if len(a_enriched) > 1 else None

    ttm = build_ttm(q_enriched)
    intel = earnings_intelligence(
        latest_q=latest_q,
        prior_q=prior_q,
        yoy_q=yoy_q,
        latest_a=latest_a,
        prior_a=prior_a,
        ttm=ttm,
    )

    # Freshness from latest filing date / period end
    fresh_as_of = (latest_q or {}).get("filing_date") or (latest_q or {}).get("period_end")
    age = _age_days(fresh_as_of)
    stale = age is not None and age > float(FRESHNESS_SLA_DAYS)
    # Integrated often fresher — note source
    primary_source = (latest_q or {}).get("source") or (latest_a or {}).get("source") or "nse"

    income_q = ((latest_q or {}).get("statements") or {}).get("income_statement") or {}
    bal_a = ((latest_a or {}).get("statements") or {}).get("balance_sheet") or {}
    cf_a = ((latest_a or {}).get("statements") or {}).get("cash_flow") or {}
    segs = ((latest_q or {}).get("statements") or {}).get("segments") or []

    parsed_q = sum(1 for r in q_enriched if r.get("xbrl_ok"))
    parsed_a = sum(1 for r in a_enriched if r.get("xbrl_ok"))
    coverage_parts = [
        bool(income_q.get("revenue_from_operations") or income_q.get("pat")),
        bool(index.get("quarterly_count")),
        bool(index.get("annual_count")),
        bool(bal_a.get("total_assets") or bal_a.get("total_equity")),
        bool(cf_a.get("operating_cash_flow")),
        bool(ttm and ttm.get("available")),
    ]
    coverage_pct = round(100.0 * sum(1 for x in coverage_parts if x) / len(coverage_parts), 1)

    ok = bool(
        (income_q.get("revenue_from_operations") is not None or income_q.get("pat") is not None)
        or (latest_a and (latest_a.get("has_income") or latest_a.get("has_balance")))
        or index.get("quarterly_count")
        or index.get("annual_count")
    )

    evidence = []
    if latest_q:
        evidence.append(
            f"Latest quarter {latest_q.get('quarter_label') or latest_q.get('period_end')} "
            f"revenue={income_q.get('revenue_from_operations')} pat={income_q.get('pat_owners') or income_q.get('pat')} "
            f"source={latest_q.get('source')}"
        )
    if latest_a:
        evidence.append(
            f"Latest annual {latest_a.get('fiscal_year_label') or latest_a.get('period_end')} "
            f"BS={bool(latest_a.get('has_balance'))} CF={bool(latest_a.get('has_cash_flow'))}"
        )
    for o in (intel.get("observations") or [])[:4]:
        evidence.append(o)

    lineage = [
        {"source": "nse_integrated_top_corp_info", "ref": "financial_results"},
        {"source": "nse_corporates_financial_results", "quarterly": index.get("quarterly_count"), "annual": index.get("annual_count")},
    ]
    if latest_q and latest_q.get("xbrl_url"):
        lineage.append({"source": "nse_financial_xbrl", "ref": latest_q.get("xbrl_url")})

    latency_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    fse_xbrl_ingested = any(r.get("fse_xbrl_ingested") for r in q_enriched + a_enriched)

    return {
        "ok": ok,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "ticker": key,
        "fse_xbrl_ingested": fse_xbrl_ingested,
        "missing": not ok,
        "fabricated": False,
        "coverage_pct": coverage_pct,
        "financial_coverage_pct": coverage_pct,
        "latest_quarter": _slim_filing(latest_q) if latest_q else None,
        "latest_annual": _slim_filing(latest_a) if latest_a else None,
        "quarter_history": [_slim_filing(r) for r in q_enriched if r.get("statements") or r.get("period_end")],
        "annual_history": [_slim_filing(r) for r in a_enriched if r.get("statements") or r.get("period_end")],
        "historical_quarters_indexed": int(index.get("quarterly_count") or 0),
        "historical_annuals_indexed": int(index.get("annual_count") or 0),
        "historical_quarters_parsed": parsed_q,
        "historical_annuals_parsed": parsed_a,
        "ttm": ttm,
        "ttm_available": bool(ttm and ttm.get("available")),
        "segment_data": bool(segs),
        "segments": segs,
        "cash_flow_available": bool(cf_a.get("operating_cash_flow")),
        "balance_sheet_available": bool(bal_a.get("total_assets") or bal_a.get("total_equity")),
        "income_available": bool(income_q.get("revenue_from_operations") or income_q.get("pat")),
        "metrics": {
            "latest_quarter": statement_metrics(
                income_q,
                ((latest_q or {}).get("statements") or {}).get("balance_sheet"),
                ((latest_q or {}).get("statements") or {}).get("cash_flow"),
            ),
            "latest_annual": statement_metrics(
                ((latest_a or {}).get("statements") or {}).get("income_statement"),
                bal_a,
                cf_a,
            ),
            "qoq_growth": growth_vs_prior(latest_q, prior_q),
            "yoy_growth": growth_vs_prior(latest_q, yoy_q),
        },
        "intelligence": intel,
        "score": intel.get("forecast_confidence"),
        "evidence": evidence,
        "confidence": round(min(0.95, 0.35 + coverage_pct / 200.0), 3),
        "freshness": {
            "as_of": fresh_as_of,
            "latest_quarter": (latest_q or {}).get("period_end"),
            "latest_quarter_label": (latest_q or {}).get("quarter_label"),
            "latest_annual": (latest_a or {}).get("period_end"),
            "latest_annual_label": (latest_a or {}).get("fiscal_year_label"),
            "age_days": round(age, 1) if age is not None else None,
            "sla_days": FRESHNESS_SLA_DAYS,
            "stale": stale,
            "within_sla": age is not None and not stale,
            "source": primary_source,
        },
        "lineage": lineage,
        "source": {
            "primary": "nse_integrated",
            "secondary": "nse_corporates_financial_results",
            "detail": "nse_indas_xbrl",
            "used": index.get("sources_used"),
        },
        "cid_summary": {
            "financial_coverage_pct": coverage_pct,
            "latest_quarter": (latest_q or {}).get("quarter_label") or (latest_q or {}).get("period_end"),
            "latest_annual": (latest_a or {}).get("fiscal_year_label") or (latest_a or {}).get("period_end"),
            "historical_quarters": int(index.get("quarterly_count") or 0),
            "historical_annuals": int(index.get("annual_count") or 0),
            "ttm_available": bool(ttm and ttm.get("available")),
            "segment_data": bool(segs),
            "cash_flow": bool(cf_a.get("operating_cash_flow")),
            "freshness_days": round(age, 1) if age is not None else None,
            "source": primary_source,
        },
        "errors": errors,
        "force": bool(force),
        "skip_xbrl": bool(skip_xbrl),
        "latency_ms": latency_ms,
        "generated_at": _now(),
    }
