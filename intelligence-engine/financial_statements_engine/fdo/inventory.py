"""Read-only inventory of raw evidence + optional HD periods (FDO)."""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from financial_statements_engine.fdo.calendar import parse_period_end
from financial_statements_engine.store import ensure_dirs, paths_for, store_root


def _hd_root() -> Path:
    raw = (os.environ.get("KF_HD_STORE_ROOT") or "").strip()
    if raw:
        return Path(raw)
    kip = (os.environ.get("KIP_DATA_DIR") or "").strip()
    if kip:
        return Path(kip) / "historical_depth"
    return Path(__file__).resolve().parents[2] / "data" / "knowledge_factory" / "historical"


def list_raw_meta(ticker: str) -> list[dict[str, Any]]:
    meta_dir = paths_for(ticker)["raw_meta"]
    if not meta_dir.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for p in sorted(meta_dir.glob("*.json")):
        try:
            rows.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return rows


def _hd_period_ends(kind: str, ticker: str) -> list[date]:
    path = _hd_root() / kind / f"{ticker.upper()}.json"
    if not path.exists():
        return []
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    records = obj.get("records") if isinstance(obj, dict) else obj
    out: list[date] = []
    for r in records or []:
        if not isinstance(r, dict):
            continue
        pe = parse_period_end(r.get("period_end") or r.get("period"))
        if pe:
            out.append(pe)
    return out


def _include_hd() -> bool:
    """FDO coverage is Raw-Evidence-first; HD is opt-in (FDO_INCLUDE_HD=1)."""
    return (os.environ.get("FDO_INCLUDE_HD") or "").strip().lower() in {"1", "true", "yes", "on"}


def company_periods(ticker: str, *, include_hd: bool | None = None) -> dict[str, Any]:
    """FSE raw meta periods; optionally union HD financial series when enabled."""
    t = ticker.upper().strip()
    annual: set[date] = set()
    quarterly: set[date] = set()
    raw_rows = list_raw_meta(t)
    for m in raw_rows:
        pe = parse_period_end(m.get("period_end") or m.get("reporting_period"))
        if not pe:
            continue
        pt = str(m.get("period_type") or m.get("filing_type") or "").lower()
        if "annual" in pt or pt in {"yearly", "year", "annual_report"}:
            annual.add(pe)
        elif "quarter" in pt or pt in {"q", "qtr", "quarterly_results"}:
            quarterly.add(pe)
        else:
            # infer: March ends often annual
            if pe.month == 3 and pe.day >= 28:
                annual.add(pe)
            else:
                quarterly.add(pe)

    use_hd = _include_hd() if include_hd is None else include_hd
    if use_hd:
        for pe in _hd_period_ends("financials_annual", t):
            annual.add(pe)
        for pe in _hd_period_ends("financials_quarterly", t):
            quarterly.add(pe)

    return {
        "ticker": t,
        "annual_period_ends": sorted(annual),
        "quarterly_period_ends": sorted(quarterly),
        "raw_evidence_n": len(raw_rows),
        "include_hd": use_hd,
        "raw_meta": raw_rows,
    }


def raw_evidence_growth(*, limit_companies: int = 5000) -> dict[str, Any]:
    """Scan FSE raw store for growth / composition metrics."""
    root = ensure_dirs()
    raw_root = root / "raw"
    files = 0
    total_bytes = 0
    by_ext: dict[str, int] = {}
    by_company: dict[str, int] = {}
    by_year: dict[str, int] = {}
    annual = 0
    quarterly = 0
    if raw_root.is_dir():
        for company_dir in list(raw_root.iterdir())[:limit_companies]:
            if not company_dir.is_dir():
                continue
            ticker = company_dir.name.upper()
            n = 0
            for f in company_dir.iterdir():
                if not f.is_file():
                    continue
                files += 1
                n += 1
                try:
                    total_bytes += f.stat().st_size
                except OSError:
                    pass
                ext = f.suffix.lstrip(".").lower() or "unknown"
                by_ext[ext] = by_ext.get(ext, 0) + 1
            by_company[ticker] = n
            for m in list_raw_meta(ticker):
                pe = parse_period_end(m.get("period_end"))
                if pe:
                    by_year[str(pe.year)] = by_year.get(str(pe.year), 0) + 1
                pt = str(m.get("period_type") or "").lower()
                if "annual" in pt:
                    annual += 1
                elif "quarter" in pt:
                    quarterly += 1

    # growth/day from ingest metrics if available
    growth_day = None
    try:
        from financial_statements_engine.collection.ingest_metrics import summarize_ingest_metrics

        growth_day = summarize_ingest_metrics().get("stored_evidence")
    except Exception:
        pass

    return {
        "raw_evidence_files": files,
        "total_storage_bytes": total_bytes,
        "total_storage_mb": round(total_bytes / (1024 * 1024), 3) if total_bytes else 0.0,
        "growth_stored_today_proxy": growth_day,
        "annual_filings": annual,
        "quarterly_filings": quarterly,
        "by_document_type": by_ext,
        "xbrl": by_ext.get("xbrl", 0),
        "pdf": by_ext.get("pdf", 0),
        "by_company": dict(sorted(by_company.items(), key=lambda kv: -kv[1])[:50]),
        "by_year": dict(sorted(by_year.items())),
        "store_root": str(store_root()),
    }
