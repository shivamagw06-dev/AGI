"""Read-oriented indexes — never mutate fact bodies."""

from __future__ import annotations

import json
from typing import Any

from financial_statements_engine.financial_warehouse.storage.roots import index_root
from financial_statements_engine.util import write_json_atomic


def _append_index(name: str, key: str, entry: dict[str, Any]) -> None:
    root = index_root() / name
    root.mkdir(parents=True, exist_ok=True)
    safe = str(key).replace(":", "_").replace("/", "_") or "_unknown"
    path = root / f"{safe}.json"
    data: dict[str, Any] = {"key": key, "entries": []}
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    entries = list(data.get("entries") or [])
    # de-dupe by fact_id+version
    sig = (entry.get("fact_id"), entry.get("version"))
    entries = [e for e in entries if (e.get("fact_id"), e.get("version")) != sig]
    entries.append(entry)
    data["entries"] = entries
    write_json_atomic(path, data)


def index_fact(record: dict[str, Any]) -> None:
    entry = {
        "fact_id": record["fact_id"],
        "version": record["version"],
        "company_id": record["company_id"],
        "ticker": record.get("ticker"),
        "metric": record.get("metric"),
        "statement_type": record.get("statement_type"),
        "reporting_period": record.get("reporting_period"),
        "fiscal_year": record.get("fiscal_year"),
        "quarter": record.get("quarter"),
        "validation_status": record.get("validation_status"),
        "quality_score": record.get("quality_score"),
        "published_timestamp": record.get("published_timestamp"),
        "fact_key": record.get("fact_key"),
    }
    _append_index("by_company", str(record["company_id"]), entry)
    _append_index("by_ticker", str(record.get("ticker") or ""), entry)
    _append_index("by_metric", str(record.get("metric") or ""), entry)
    _append_index("by_statement", str(record.get("statement_type") or ""), entry)
    _append_index("by_period", str(record.get("reporting_period") or ""), entry)
    if record.get("fiscal_year"):
        _append_index("by_fiscal_year", str(record["fiscal_year"]), entry)
    _append_index("by_validation_status", str(record.get("validation_status") or ""), entry)


def lookup(index_name: str, key: str) -> list[dict[str, Any]]:
    safe = str(key).replace(":", "_").replace("/", "_") or "_unknown"
    path = index_root() / index_name / f"{safe}.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("entries") or [])
