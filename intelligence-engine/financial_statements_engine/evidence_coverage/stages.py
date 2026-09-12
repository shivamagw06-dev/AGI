"""Per-company stage detection across FSE + HD stores."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from financial_statements_engine.evidence_coverage.schema import (
    ANNUAL_FRESHNESS_DAYS,
    QUARTERLY_FRESHNESS_DAYS,
)
from financial_statements_engine.store import ensure_dirs, paths_for


def _hd_root() -> Path:
    raw = (os.environ.get("KF_HD_STORE_ROOT") or "").strip()
    if raw:
        return Path(raw)
    kip = (os.environ.get("KIP_DATA_DIR") or "").strip()
    if kip:
        return Path(kip) / "historical_depth"
    return Path(__file__).resolve().parents[2] / "data" / "knowledge_factory" / "historical"


def _parse_date(value: Any) -> datetime | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if s.upper().startswith("FY") and len(s) <= 6:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:10], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _days_ago(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0


def _hd_series(kind: str, ticker: str) -> dict[str, Any]:
    path = _hd_root() / kind / f"{ticker.upper()}.json"
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return obj if isinstance(obj, dict) else {"records": obj if isinstance(obj, list) else []}


def _latest_period_end(series: dict[str, Any]) -> tuple[str | None, datetime | None, str | None]:
    latest_end: datetime | None = None
    latest_period: str | None = None
    latest_source: str | None = None
    for r in series.get("records") or []:
        if not isinstance(r, dict):
            continue
        pe = _parse_date(r.get("period_end") or r.get("period"))
        if pe is None:
            continue
        if latest_end is None or pe > latest_end:
            latest_end = pe
            latest_period = str(r.get("period") or r.get("period_end") or "")
            latest_source = str(r.get("source") or "")
    return latest_period, latest_end, latest_source


def _has_fse_raw(ticker: str) -> bool:
    p = paths_for(ticker)["raw"]
    return p.is_dir() and any(p.iterdir())


def _has_parsed(ticker: str) -> bool:
    root = ensure_dirs()
    draft = root / "parsing" / "drafts" / ticker.upper() / "latest.json"
    if draft.exists():
        return True
    matrices = root / "parsing" / "coverage" / "matrices" / ticker.upper()
    if matrices.is_dir() and any(matrices.glob("*.json")):
        return True
    extracted = paths_for(ticker)["extracted"]
    return extracted.is_dir() and any(extracted.iterdir())


def _has_validated(ticker: str) -> bool:
    root = ensure_dirs()
    reports = root / "validation" / "reports" / ticker.upper()
    if reports.is_dir():
        for p in reports.glob("*.json"):
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            status = str(
                (obj.get("approval") or {}).get("approval_status")
                or obj.get("approval_status")
                or ""
            )
            if status in ("APPROVED", "APPROVED_WITH_WARNINGS") or obj.get("publishable") is True:
                return True
    validated = paths_for(ticker)["validated"]
    if validated.is_dir() and any(validated.glob("*.json")):
        return True
    pub = paths_for(ticker)["published"]
    return pub.is_dir() and any(pub.glob("*.json"))


def _has_published(ticker: str) -> bool:
    try:
        from financial_statements_engine.financial_warehouse.production import get_latest

        latest = get_latest(ticker)
        if int(latest.get("n") or 0) > 0:
            return True
    except Exception:
        pass
    pub = paths_for(ticker)["published"]
    return pub.is_dir() and any(pub.glob("*.json"))


def _has_derived(ticker: str) -> bool:
    try:
        from financial_statements_engine.derived_metrics.store.versions import list_company_metrics

        if list_company_metrics(f"nse:{ticker.upper()}"):
            return True
    except Exception:
        pass
    derived = paths_for(ticker)["derived"]
    return derived.is_dir() and any(derived.glob("*.json"))


def assess_company(ticker: str, *, in_universe: bool = True) -> dict[str, Any]:
    """Return boolean stage map + evidence notes for one company."""
    t = ticker.upper().strip()
    annual = _hd_series("financials_annual", t)
    quarterly = _hd_series("financials_quarterly", t)
    a_period, a_end, a_source = _latest_period_end(annual)
    q_period, q_end, q_source = _latest_period_end(quarterly)
    a_age = _days_ago(a_end)
    q_age = _days_ago(q_end)

    has_any_hd = bool(annual.get("records") or quarterly.get("records"))
    discovered = bool(in_universe or has_any_hd or _has_fse_raw(t))
    latest_annual = bool(a_end is not None and a_age is not None and a_age <= ANNUAL_FRESHNESS_DAYS)
    latest_quarterly = bool(q_end is not None and q_age is not None and q_age <= QUARTERLY_FRESHNESS_DAYS)
    parsed = _has_parsed(t)
    validated = _has_validated(t)
    published = _has_published(t)
    derived = _has_derived(t)

    stages = {
        "discovered": discovered,
        "latest_annual_filing": latest_annual,
        "latest_quarterly_filing": latest_quarterly,
        "parsed": parsed,
        "validated": validated,
        "published": published,
        "derived_metrics": derived,
    }
    gap = next((k for k, v in stages.items() if not v), None)
    return {
        "ticker": t,
        "stages": stages,
        "first_gap": gap,
        "complete": gap is None,
        "evidence": {
            "annual_periods": len(annual.get("records") or []),
            "annual_latest_period": a_period,
            "annual_latest_period_end": a_end.date().isoformat() if a_end else None,
            "annual_age_days": round(a_age, 1) if a_age is not None else None,
            "annual_source": a_source,
            "annual_live": bool(a_source and "fixture" not in a_source.lower()),
            "quarterly_periods": len(quarterly.get("records") or []),
            "quarterly_latest_period": q_period,
            "quarterly_latest_period_end": q_end.date().isoformat() if q_end else None,
            "quarterly_age_days": round(q_age, 1) if q_age is not None else None,
            "quarterly_source": q_source,
            "quarterly_live": bool(q_source and "fixture" not in q_source.lower()),
            "fse_raw": _has_fse_raw(t),
        },
    }
