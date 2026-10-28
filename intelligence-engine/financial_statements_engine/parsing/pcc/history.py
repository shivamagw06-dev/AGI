"""Permanent certification history — never deleted."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import write_json_atomic


def _history_root() -> Path:
    p = ensure_dirs() / "parsing" / "pcc" / "certifications"
    p.mkdir(parents=True, exist_ok=True)
    return p


def store_certification(report: dict[str, Any]) -> Path:
    cid = str(report["certification_id"])
    path = _history_root() / f"{cid.replace(':', '_')}.json"
    if path.exists():
        raise FileExistsError(f"pcc_certification_immutable_violation: {cid}")
    write_json_atomic(path, report)
    # latest pointer (mutable)
    write_json_atomic(
        _history_root() / "latest.json",
        {
            "certification_id": cid,
            "passed": report.get("passed"),
            "production_eligible": report.get("production_eligible"),
            "path": str(path),
            "as_of": report.get("execution_timestamp"),
        },
    )
    # append index
    idx = _history_root() / "index.jsonl"
    with idx.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "certification_id": cid,
                    "passed": report.get("passed"),
                    "production_eligible": report.get("production_eligible"),
                    "parser_version": report.get("parser_version"),
                    "execution_timestamp": report.get("execution_timestamp"),
                    "path": str(path),
                },
                sort_keys=True,
                default=str,
            )
            + "\n"
        )
    return path


def list_certifications(limit: int = 100) -> list[dict[str, Any]]:
    idx = _history_root() / "index.jsonl"
    if not idx.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in idx.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def load_certification(certification_id: str) -> dict[str, Any] | None:
    path = _history_root() / f"{certification_id.replace(':', '_')}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def latest_certification() -> dict[str, Any] | None:
    ptr = _history_root() / "latest.json"
    if not ptr.exists():
        # fall back to last index entry
        rows = list_certifications(limit=1)
        if not rows:
            return None
        return load_certification(str(rows[-1]["certification_id"]))
    meta = json.loads(ptr.read_text(encoding="utf-8"))
    return load_certification(str(meta["certification_id"]))


def prior_certification(current_id: str | None = None) -> dict[str, Any] | None:
    rows = list_certifications(limit=500)
    if not rows:
        return None
    if current_id is None:
        if len(rows) < 2:
            return load_certification(str(rows[-1]["certification_id"])) if rows else None
        return load_certification(str(rows[-2]["certification_id"]))
    ids = [str(r["certification_id"]) for r in rows]
    if current_id not in ids:
        return load_certification(str(rows[-1]["certification_id"]))
    i = ids.index(current_id)
    if i == 0:
        return None
    return load_certification(ids[i - 1])
