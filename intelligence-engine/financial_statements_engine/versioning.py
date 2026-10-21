"""Version Control Layer — revisions, restatements, audit history."""

from __future__ import annotations

import json
from typing import Any

from financial_statements_engine.store import paths_for
from financial_statements_engine.util import now_iso, write_json_atomic


def _version_dir(ticker: str, statement_type: str, period_end: str):
    return paths_for(ticker)["versions"] / statement_type / period_end


def list_versions(ticker: str, statement_type: str, period_end: str) -> list[int]:
    d = _version_dir(ticker, statement_type, period_end)
    if not d.exists():
        return []
    versions: list[int] = []
    for p in d.glob("v*.json"):
        try:
            versions.append(int(p.stem[1:]))
        except ValueError:
            continue
    return sorted(versions)


def latest_version(ticker: str, statement_type: str, period_end: str) -> dict[str, Any] | None:
    vers = list_versions(ticker, statement_type, period_end)
    if not vers:
        return None
    path = _version_dir(ticker, statement_type, period_end) / f"v{vers[-1]}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def metric_diff(prev: dict[str, Any] | None, curr: dict[str, Any]) -> dict[str, Any]:
    prev_m = (prev or {}).get("metrics") or {}
    curr_m = curr.get("metrics") or {}
    keys = sorted(set(prev_m) | set(curr_m))
    changes: list[dict[str, Any]] = []
    for k in keys:
        pv = prev_m.get(k)
        cv = curr_m.get(k)
        pval = pv.get("value_inr") if isinstance(pv, dict) else pv
        cval = cv.get("value_inr") if isinstance(cv, dict) else cv
        if pval != cval:
            changes.append({"metric": k, "previous": pval, "current": cval})
    return {
        "change_count": len(changes),
        "changes": changes,
        "restatement": bool(changes) and prev is not None,
        "as_of": now_iso(),
    }


def commit_version(statement: dict[str, Any]) -> dict[str, Any]:
    """Persist a new immutable version; never overwrite prior files."""
    ticker = str(statement["ticker"]).upper()
    statement_type = str(statement["statement_type"])
    period_end = str(statement["period_end"])
    prev = latest_version(ticker, statement_type, period_end)
    next_v = (prev.get("version") if prev else 0) or 0
    next_v = int(next_v) + 1

    out = dict(statement)
    out["version"] = next_v
    out["statement_id"] = f"{ticker}:{statement.get('period_type')}:{period_end}:{statement_type}:v{next_v}"
    out["diff_vs_previous"] = metric_diff(prev, out)
    out["restatement"] = bool(out["diff_vs_previous"].get("restatement"))
    out["lifecycle"] = "versioned"

    path = _version_dir(ticker, statement_type, period_end) / f"v{next_v}.json"
    write_json_atomic(path, out)
    return out
