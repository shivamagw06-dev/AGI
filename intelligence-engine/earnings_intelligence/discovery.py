"""NSE filing discovery — integrated (primary) + corporates-financial-results (secondary)."""

from __future__ import annotations

import json
from typing import Any
from urllib.request import Request

from ownership_intelligence.dates import fiscal_quarter_label, parse_nse_date

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

CORP_RESULTS = (
    "https://www.nseindia.com/api/corporates-financial-results"
    "?index=equities&period={period}&symbol={symbol}"
)
TOP_CORP = "https://www.nseindia.com/api/top-corp-info?symbol={symbol}&market=equities"


def _opener():
    from live_data.collectors.base import nse_session_opener

    return nse_session_opener()


def _get_json(url: str, *, opener=None, referer: str | None = None) -> Any:
    op = opener or _opener()
    req = Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json",
            "Referer": referer or "https://www.nseindia.com/",
        },
    )
    with op.open(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _is_consolidated(value: Any) -> bool | None:
    s = str(value or "").strip().lower()
    if not s:
        return None
    if "non" in s and "consol" in s:
        return False
    if "consol" in s:
        return True
    return None


def _norm_corp_row(row: dict[str, Any], *, entity: str, source: str) -> dict[str, Any]:
    period_end = parse_nse_date(row.get("toDate") or row.get("to_date"))
    period_start = parse_nse_date(row.get("fromDate") or row.get("from_date"))
    filing = parse_nse_date(row.get("filingDate") or row.get("re_broadcast_timestamp") or row.get("broadCastDate"))
    period_type = str(row.get("period") or "").strip() or None
    relating = str(row.get("relatingTo") or "").strip() or None
    # Infer annual vs quarterly
    freq = "annual"
    if period_type and "quarter" in period_type.lower():
        freq = "quarterly"
    elif relating and "quarter" in relating.lower():
        freq = "quarterly"
    elif period_type and period_type.lower() in {"annual", "yearly"}:
        freq = "annual"
    return {
        "entity": entity.upper(),
        "frequency": freq,
        "period_start": period_start,
        "period_end": period_end,
        "quarter_label": fiscal_quarter_label(period_end) if freq == "quarterly" else None,
        "fiscal_year_label": _fy_label(period_end) if freq == "annual" else None,
        "filing_date": filing,
        "broadcast_date": row.get("broadCastDate") or row.get("re_broadcast_timestamp"),
        "consolidated": _is_consolidated(row.get("consolidated")),
        "audited": row.get("audited"),
        "ind_as": row.get("indAs") or row.get("ind_as"),
        "relating_to": relating,
        "period_type": period_type,
        "financial_year": row.get("financialYear"),
        "xbrl_url": row.get("xbrl") or row.get("xbrl_attachment"),
        "company_name": row.get("companyName"),
        "isin": row.get("isin"),
        "seq_number": row.get("seqNumber"),
        "params": row.get("params"),
        "source": source,
        "priority": 2 if source.startswith("nse_corp") else 1,
        "raw_summary": {
            "income": row.get("income"),
            "proLossAftTax": row.get("proLossAftTax"),
            "reProLossBefTax": row.get("reProLossBefTax"),
            "reDilEPS": row.get("reDilEPS"),
        },
        "raw": {k: row.get(k) for k in row.keys() if k != "raw"},
    }


def _fy_label(iso_date: str | None) -> str | None:
    if not iso_date:
        return None
    try:
        from datetime import datetime

        dt = datetime.strptime(iso_date[:10], "%Y-%m-%d")
    except ValueError:
        return None
    # FY label by March year-end
    fy = dt.year if dt.month <= 3 else dt.year + 1
    return f"FY{str(fy)[2:]}"


def _norm_integrated_row(row: dict[str, Any], *, entity: str) -> dict[str, Any]:
    period_end = parse_nse_date(row.get("to_date") or row.get("toDate"))
    filing = parse_nse_date(row.get("re_broadcast_timestamp"))
    # Integrated feed is typically quarterly result prints
    freq = "quarterly"
    return {
        "entity": entity.upper(),
        "frequency": freq,
        "period_start": parse_nse_date(row.get("from_date")),
        "period_end": period_end,
        "quarter_label": fiscal_quarter_label(period_end),
        "fiscal_year_label": None,
        "filing_date": filing,
        "broadcast_date": row.get("re_broadcast_timestamp"),
        "consolidated": _is_consolidated(row.get("consolidated")),
        "audited": row.get("audited"),
        "ind_as": "Integrated Filing IND-AS",
        "relating_to": None,
        "period_type": "Quarterly",
        "financial_year": None,
        "xbrl_url": row.get("xbrl_attachment") or row.get("xbrl"),
        "company_name": None,
        "isin": None,
        "seq_number": None,
        "params": None,
        "source": "nse_integrated",
        "priority": 1,
        "raw_summary": {
            "income": row.get("income"),
            "proLossAftTax": row.get("proLossAftTax"),
            "reProLossBefTax": row.get("reProLossBefTax"),
            "reDilEPS": row.get("reDilEPS"),
        },
        "raw": dict(row),
    }


def _dedupe_key(row: dict[str, Any]) -> tuple:
    return (
        row.get("period_end"),
        row.get("frequency"),
        row.get("consolidated"),
        (row.get("xbrl_url") or "")[-40:],
    )


def discover_filings(
    symbol: str,
    *,
    opener=None,
    injected_integrated: list[dict[str, Any]] | None = None,
    injected_quarterly: list[dict[str, Any]] | None = None,
    injected_annual: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build unified filing index. Integrated feed takes precedence when fresher/overlapping."""
    key = (symbol or "").upper()
    op = opener
    errors: list[str] = []
    integrated: list[dict[str, Any]] = []
    quarterly: list[dict[str, Any]] = []
    annual: list[dict[str, Any]] = []

    if injected_integrated is not None:
        integrated = [_norm_integrated_row(r, entity=key) for r in injected_integrated]
    else:
        try:
            top = _get_json(TOP_CORP.format(symbol=key), opener=op, referer=f"https://www.nseindia.com/get-quotes/equity?symbol={key}")
            rows = ((top.get("financial_results") or {}).get("data") or []) if isinstance(top, dict) else []
            integrated = [_norm_integrated_row(r, entity=key) for r in rows if isinstance(r, dict)]
        except Exception as exc:  # noqa: BLE001
            errors.append(f"integrated:{type(exc).__name__}:{str(exc)[:120]}")

    if injected_quarterly is not None:
        quarterly = [_norm_corp_row(r, entity=key, source="nse_corp_quarterly") for r in injected_quarterly]
    else:
        try:
            rows = _get_json(
                CORP_RESULTS.format(period="Quarterly", symbol=key),
                opener=op,
                referer=f"https://www.nseindia.com/get-quotes/equity?symbol={key}",
            )
            quarterly = [
                _norm_corp_row(r, entity=key, source="nse_corp_quarterly")
                for r in (rows if isinstance(rows, list) else [])
                if isinstance(r, dict)
            ]
        except Exception as exc:  # noqa: BLE001
            errors.append(f"corp_q:{type(exc).__name__}:{str(exc)[:120]}")

    if injected_annual is not None:
        annual = [_norm_corp_row(r, entity=key, source="nse_corp_annual") for r in injected_annual]
    else:
        try:
            rows = _get_json(
                CORP_RESULTS.format(period="Annual", symbol=key),
                opener=op,
                referer=f"https://www.nseindia.com/get-quotes/equity?symbol={key}",
            )
            annual = [
                _norm_corp_row(r, entity=key, source="nse_corp_annual")
                for r in (rows if isinstance(rows, list) else [])
                if isinstance(r, dict)
            ]
        except Exception as exc:  # noqa: BLE001
            errors.append(f"corp_a:{type(exc).__name__}:{str(exc)[:120]}")

    # Prefer consolidated when both exist for same period
    def prefer(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_end: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            pe = r.get("period_end") or ""
            by_end.setdefault(pe, []).append(r)
        out = []
        for pe, group in by_end.items():
            cons = [g for g in group if g.get("consolidated") is True]
            non = [g for g in group if g.get("consolidated") is False]
            unk = [g for g in group if g.get("consolidated") is None]
            chosen = (cons or unk or non or group)[0]
            # lowest priority number wins among same consolidation
            group_sorted = sorted(
                cons or unk or non or group,
                key=lambda x: (x.get("priority") or 9, x.get("source") != "nse_integrated"),
            )
            chosen = group_sorted[0]
            out.append(chosen)
        out.sort(key=lambda r: r.get("period_end") or "", reverse=True)
        return out

    # Merge integrated into quarterly (integrated preferred)
    q_merged = prefer(list(integrated) + list(quarterly))
    a_merged = prefer(list(annual))

    latest_q = q_merged[0] if q_merged else None
    latest_a = a_merged[0] if a_merged else None

    return {
        "ok": bool(q_merged or a_merged),
        "entity": key,
        "quarterly": q_merged,
        "annual": a_merged,
        "quarterly_count": len(q_merged),
        "annual_count": len(a_merged),
        "latest_quarter": latest_q,
        "latest_annual": latest_a,
        "errors": errors,
        "sources_used": sorted(
            {
                *(r.get("source") for r in q_merged if r.get("source")),
                *(r.get("source") for r in a_merged if r.get("source")),
            }
        ),
    }
