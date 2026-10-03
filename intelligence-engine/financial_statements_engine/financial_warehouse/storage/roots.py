"""Write-once fact storage. Never overwrites published fact files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import write_json_atomic


def warehouse_root() -> Path:
    p = ensure_dirs() / "warehouse"
    for name in ("facts", "versions", "history", "indexes", "restatements", "lineage", "contracts"):
        (p / name).mkdir(parents=True, exist_ok=True)
    return p


def index_root() -> Path:
    return warehouse_root() / "indexes"


def fact_path(company_id: str, fact_id: str, version: int) -> Path:
    safe_co = company_id.replace(":", "_")
    safe_fid = fact_id.replace(":", "_")
    d = warehouse_root() / "facts" / safe_co
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{safe_fid}_v{version}.json"


def store_fact_record(record: dict[str, Any]) -> Path:
    path = fact_path(str(record["company_id"]), str(record["fact_id"]), int(record["version"]))
    if path.exists():
        raise FileExistsError(f"warehouse_immutable_violation: {path.name}")
    write_json_atomic(path, record)
    # history append-only log
    hist = warehouse_root() / "history" / f"{str(record['company_id']).replace(':', '_')}.jsonl"
    with hist.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"fact_id": record["fact_id"], "version": record["version"], "path": str(path)}, sort_keys=True) + "\n")
    return path


def load_fact_record(company_id: str, fact_id: str, version: int) -> dict[str, Any] | None:
    path = fact_path(company_id, fact_id, version)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
