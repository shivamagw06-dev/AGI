"""Version engine — never overwrites; always allocates a new version number."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from financial_statements_engine.financial_warehouse.storage.roots import fact_path, warehouse_root
from financial_statements_engine.util import now_iso, write_json_atomic


def _version_index_path(company_id: str, fact_key: str) -> Path:
    d = warehouse_root() / "versions" / company_id.replace(":", "_")
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{fact_key.replace(':', '_')}.json"


def list_fact_versions(company_id: str, fact_key: str) -> list[dict[str, Any]]:
    path = _version_index_path(company_id, fact_key)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("versions") or [])


def next_version(company_id: str, fact_key: str) -> int:
    vers = list_fact_versions(company_id, fact_key)
    if not vers:
        return 1
    return int(max(int(v.get("version_number") or 0) for v in vers)) + 1


def register_version(
    *,
    company_id: str,
    fact_key: str,
    fact_id: str,
    version_number: int,
    published_timestamp: str,
    effective_date: str | None,
    reason_for_change: str | None,
    validator_version: str | None,
    schema_version: str | None,
    path: str,
) -> dict[str, Any]:
    idx_path = _version_index_path(company_id, fact_key)
    data: dict[str, Any] = {"company_id": company_id, "fact_key": fact_key, "versions": []}
    if idx_path.exists():
        data = json.loads(idx_path.read_text(encoding="utf-8"))
    entry = {
        "version_number": version_number,
        "fact_id": fact_id,
        "published_timestamp": published_timestamp,
        "effective_date": effective_date,
        "superseded_date": None,
        "reason_for_change": reason_for_change,
        "validator_version": validator_version,
        "schema_version": schema_version,
        "path": path,
    }
    data["versions"] = list(data.get("versions") or []) + [entry]
    data["latest_version"] = version_number
    write_json_atomic(idx_path, data)
    return entry


def supersede(
    company_id: str,
    fact_key: str,
    old_version: int,
    *,
    superseded_by_fact_id: str,
    superseded_date: str | None = None,
) -> None:
    idx_path = _version_index_path(company_id, fact_key)
    if not idx_path.exists():
        return
    data = json.loads(idx_path.read_text(encoding="utf-8"))
    when = superseded_date or now_iso()
    for v in data.get("versions") or []:
        if int(v.get("version_number") or 0) == int(old_version):
            v["superseded_date"] = when
            v["superseded_by"] = superseded_by_fact_id
    write_json_atomic(idx_path, data)

    # Mark prior fact record (does not edit value fields — only supersession pointer)
    # Load path from index
    for v in data.get("versions") or []:
        if int(v.get("version_number") or 0) == int(old_version):
            p = Path(v["path"])
            if p.exists():
                rec = json.loads(p.read_text(encoding="utf-8"))
                # Write companion supersession sidecar — never mutate fact body values
                side = p.with_suffix(".superseded.json")
                if not side.exists():
                    write_json_atomic(
                        side,
                        {
                            "fact_id": rec.get("fact_id"),
                            "version": old_version,
                            "superseded_by": superseded_by_fact_id,
                            "superseded_date": when,
                            "values_mutated": False,
                        },
                    )
            break
