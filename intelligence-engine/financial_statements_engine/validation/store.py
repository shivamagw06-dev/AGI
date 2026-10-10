"""Immutable persistence for validation reports and validated facts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import write_json_atomic


def _val_dir(ticker: str) -> Path:
    p = ensure_dirs() / "parsing" / "validation" / "reports" / ticker.upper().strip()
    p.mkdir(parents=True, exist_ok=True)
    return p


def store_report(report: dict[str, Any]) -> Path:
    ticker = str(report.get("ticker") or "UNKNOWN")
    vid = str(report["validation_id"])
    path = _val_dir(ticker) / f"{vid.replace(':', '_')}.json"
    if path.exists():
        raise FileExistsError(f"validation_report_immutable_violation: {vid}")
    write_json_atomic(path, report)
    write_json_atomic(
        _val_dir(ticker) / "latest.json",
        {
            "validation_id": vid,
            "draft_id": report.get("draft_id"),
            "approval_status": (report.get("approval") or {}).get("approval_status"),
            "path": str(path),
        },
    )
    return path


def load_report(ticker: str, validation_id: str) -> dict[str, Any] | None:
    path = _val_dir(ticker) / f"{validation_id.replace(':', '_')}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_reports(ticker: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    root = ensure_dirs() / "parsing" / "validation" / "reports"
    if not root.exists():
        return []
    paths: list[Path] = []
    if ticker:
        d = root / ticker.upper().strip()
        if d.exists():
            paths = sorted(d.glob("val_*.json"))
    else:
        paths = sorted(root.rglob("val_*.json"))
    rows = []
    for p in paths[-limit:]:
        try:
            rows.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return rows
