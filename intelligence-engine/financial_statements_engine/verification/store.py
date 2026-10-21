"""Persist immutable verification reports and provenance pages."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso, write_json_atomic

_LOCK = threading.Lock()


def verification_root() -> Path:
    root = ensure_dirs() / "verification"
    for name in ("reports", "provenance", "runs"):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def report_path(workflow_id: str) -> Path:
    safe = str(workflow_id).replace(":", "_")
    return verification_root() / "reports" / f"{safe}.json"


def provenance_path(workflow_id: str) -> Path:
    safe = str(workflow_id).replace(":", "_")
    return verification_root() / "provenance" / f"{safe}.json"


def save_report(report: dict[str, Any]) -> Path:
    wid = str(report["workflow_id"])
    path = report_path(wid)
    with _LOCK:
        # Immutable: do not overwrite an existing completed report with a different body
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing.get("final_status") == "COMPLETED" and report.get("final_status") == "COMPLETED":
                if existing.get("document_hash") == report.get("document_hash"):
                    return path
        payload = dict(report)
        payload["persisted_at"] = now_iso()
        payload["immutable"] = True
        write_json_atomic(path, payload)
        _index_report(payload)
    return path


def load_report(workflow_id: str) -> dict[str, Any] | None:
    path = report_path(workflow_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_provenance(page: dict[str, Any]) -> Path:
    wid = str(page["workflow_id"])
    path = provenance_path(wid)
    with _LOCK:
        payload = dict(page)
        payload["persisted_at"] = now_iso()
        write_json_atomic(path, payload)
    return path


def load_provenance(workflow_id: str) -> dict[str, Any] | None:
    path = provenance_path(workflow_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _index_report(report: dict[str, Any]) -> None:
    idx = verification_root() / "runs" / "index.jsonl"
    with idx.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "workflow_id": report.get("workflow_id"),
                    "company": report.get("company"),
                    "final_status": report.get("final_status"),
                    "overall_duration_ms": report.get("overall_duration_ms"),
                    "ts": now_iso(),
                },
                sort_keys=True,
                default=str,
            )
            + "\n"
        )


def list_reports(limit: int = 200) -> list[dict[str, Any]]:
    d = verification_root() / "reports"
    rows: list[dict[str, Any]] = []
    for p in sorted(d.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            rows.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
        if len(rows) >= limit:
            break
    return rows
