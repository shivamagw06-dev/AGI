"""Warehouse query capabilities — storage/retrieval only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from financial_statements_engine.financial_warehouse.indexing.engine import lookup
from financial_statements_engine.financial_warehouse.versioning.engine import list_fact_versions


def _load_path(path: str) -> dict[str, Any] | None:
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def latest_financials(ticker: str, *, statement_type: str | None = None) -> dict[str, Any]:
    t = ticker.upper().strip()
    entries = lookup("by_ticker", t)
    # Keep highest version per fact_key
    best: dict[str, dict[str, Any]] = {}
    for e in entries:
        if statement_type and e.get("statement_type") != statement_type:
            continue
        fk = str(e.get("fact_key") or e.get("fact_id"))
        prev = best.get(fk)
        if prev is None or int(e.get("version") or 0) > int(prev.get("version") or 0):
            best[fk] = e
    facts = []
    for e in best.values():
        company_id = str(e["company_id"])
        vers = list_fact_versions(company_id, str(e.get("fact_key")))
        match = next((v for v in vers if int(v["version_number"]) == int(e["version"])), None)
        if match:
            rec = _load_path(match["path"])
            if rec and not Path(match["path"]).with_suffix(".superseded.json").exists():
                # still include latest even if superseded sidecar — latest version won't have sidecar on itself
                facts.append(rec)
            elif rec:
                facts.append(rec)
    # Prefer non-superseded: if sidecar exists on this version, skip unless it's still latest index
    facts = [f for f in facts if f.get("superseded_by") is None]
    return {
        "ok": True,
        "ticker": t,
        "view": "latest",
        "n": len(facts),
        "facts": sorted(facts, key=lambda r: (str(r.get("statement_type")), str(r.get("metric")))),
        "issues_recommendations": False,
    }


def metric_history(ticker: str, metric: str) -> dict[str, Any]:
    t = ticker.upper().strip()
    entries = [e for e in lookup("by_ticker", t) if e.get("metric") == metric]
    rows = []
    for e in sorted(entries, key=lambda x: (str(x.get("reporting_period")), int(x.get("version") or 0))):
        vers = list_fact_versions(str(e["company_id"]), str(e.get("fact_key")))
        match = next((v for v in vers if int(v["version_number"]) == int(e["version"])), None)
        if not match:
            continue
        rec = _load_path(match["path"])
        if rec:
            rows.append(rec)
    return {"ok": True, "ticker": t, "metric": metric, "n": len(rows), "history": rows}


def version_history(company_id: str, fact_key: str) -> dict[str, Any]:
    vers = list_fact_versions(company_id, fact_key)
    rows = []
    for v in vers:
        rec = _load_path(v["path"])
        rows.append({"version_meta": v, "fact": rec})
    return {"ok": True, "company_id": company_id, "fact_key": fact_key, "n": len(rows), "versions": rows}


def company_timeline(ticker: str) -> dict[str, Any]:
    t = ticker.upper().strip()
    entries = lookup("by_ticker", t)
    periods = sorted({str(e.get("reporting_period")) for e in entries if e.get("reporting_period")})
    return {
        "ok": True,
        "ticker": t,
        "periods": periods,
        "publication_events": sorted(
            entries,
            key=lambda e: str(e.get("published_timestamp") or ""),
        ),
    }
