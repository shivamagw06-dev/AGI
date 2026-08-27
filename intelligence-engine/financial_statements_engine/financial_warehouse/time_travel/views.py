"""Time-travel views — reproducible historical queries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from financial_statements_engine.financial_warehouse.indexing.engine import lookup
from financial_statements_engine.financial_warehouse.query.api import latest_financials
from financial_statements_engine.financial_warehouse.restatements.engine import restatement_history
from financial_statements_engine.financial_warehouse.schema import VIEWS
from financial_statements_engine.financial_warehouse.versioning.engine import list_fact_versions


def _load(path: str) -> dict[str, Any] | None:
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def query_as_of(ticker: str, as_of: str) -> dict[str, Any]:
    """Facts whose published_timestamp <= as_of, latest version per fact_key."""
    t = ticker.upper().strip()
    entries = lookup("by_ticker", t)
    best: dict[str, dict[str, Any]] = {}
    for e in entries:
        ts = str(e.get("published_timestamp") or "")
        if ts and ts > as_of:
            continue
        fk = str(e.get("fact_key"))
        prev = best.get(fk)
        if prev is None or int(e.get("version") or 0) > int(prev.get("version") or 0):
            best[fk] = e
    facts = []
    for e in best.values():
        vers = list_fact_versions(str(e["company_id"]), str(e["fact_key"]))
        match = next((v for v in vers if int(v["version_number"]) == int(e["version"])), None)
        if match:
            rec = _load(match["path"])
            if rec:
                facts.append(rec)
    return {
        "ok": True,
        "view": "as_of_date",
        "as_of": as_of,
        "ticker": t,
        "n": len(facts),
        "facts": facts,
        "reproducible": True,
    }


def query_view(ticker: str, view: str, *, as_of: str | None = None) -> dict[str, Any]:
    if view not in VIEWS:
        return {"ok": False, "error": "unknown_view", "supported": list(VIEWS)}
    if view in ("latest", "as_published", "as_validated"):
        return {**latest_financials(ticker), "view": view}
    if view == "as_of_date":
        if not as_of:
            return {"ok": False, "error": "as_of_required"}
        return query_as_of(ticker, as_of)
    if view in ("original", "as_originally_filed", "as_reported"):
        # version 1 per fact_key
        t = ticker.upper().strip()
        entries = lookup("by_ticker", t)
        keys = {str(e.get("fact_key")): str(e.get("company_id")) for e in entries}
        facts = []
        for fk, cid in keys.items():
            vers = list_fact_versions(cid, fk)
            if not vers:
                continue
            first = min(vers, key=lambda v: int(v["version_number"]))
            rec = _load(first["path"])
            if rec:
                facts.append(rec)
        return {"ok": True, "view": view, "ticker": t, "n": len(facts), "facts": facts, "reproducible": True}
    if view == "as_restated":
        # latest that are restatements, else latest
        base = latest_financials(ticker)
        restated = [f for f in base.get("facts") or [] if f.get("is_restatement")]
        hist = restatement_history()
        return {
            "ok": True,
            "view": view,
            "ticker": ticker.upper().strip(),
            "n": len(restated) if restated else base.get("n"),
            "facts": restated if restated else base.get("facts"),
            "restatement_history": [h for h in hist if h.get("ticker") == ticker.upper().strip()],
            "reproducible": True,
        }
    return {"ok": False, "error": "view_not_implemented", "view": view}
