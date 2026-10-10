"""Unknown metric review queue — never discard unknown labels."""

from __future__ import annotations

import json
import uuid
from typing import Any

from financial_statements_engine.collection.event_bus import publish
from financial_statements_engine.parsing.quality.schema import UNKNOWN_STATUSES
from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso, write_json_atomic


def _queue_path():
    p = ensure_dirs() / "parsing" / "unknown_metrics" / "queue.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def enqueue_unknown(
    *,
    label: str,
    ticker: str,
    evidence_id: str,
    manifest_id: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rec = {
        "queue_id": f"umq:{uuid.uuid4().hex[:16]}",
        "label": label,
        "ticker": ticker.upper().strip(),
        "evidence_id": evidence_id,
        "manifest_id": manifest_id,
        "context": context or {},
        "status": "open",
        "proposed_canonical": None,
        "reviewed_at": None,
        "created_at": now_iso(),
        "workflow": [
            "unknown_metric",
            "review_queue",
            "engineering_approval",
            "metric_registry_update",
            "schema_version_increment",
            "future_automatic_recognition",
        ],
    }
    with _queue_path().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
    publish("unknown_metric.queued.v1", {"queue_id": rec["queue_id"], "label": label, "ticker": ticker})
    return rec


def enqueue_many(
    labels: list[str],
    *,
    ticker: str,
    evidence_id: str,
    manifest_id: str,
    context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [
        enqueue_unknown(
            label=lab,
            ticker=ticker,
            evidence_id=evidence_id,
            manifest_id=manifest_id,
            context=context,
        )
        for lab in labels
    ]


def list_queue(*, status: str | None = "open") -> list[dict[str, Any]]:
    path = _queue_path()
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if status and rec.get("status") != status:
            continue
        rows.append(rec)
    return rows


def approve(queue_id: str, proposed_canonical: str) -> dict[str, Any]:
    """Mark approved (registry update is a separate engineering step / PR)."""
    rows = list_queue(status=None)
    updated = None
    out_lines = []
    for rec in rows:
        if rec.get("queue_id") == queue_id:
            rec = dict(rec)
            rec["status"] = "approved"
            rec["proposed_canonical"] = proposed_canonical
            rec["reviewed_at"] = now_iso()
            updated = rec
        out_lines.append(json.dumps(rec, sort_keys=True, default=str))
    # rewrite queue file from all statuses — reload full file
    path = _queue_path()
    all_rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("queue_id") == queue_id:
                rec["status"] = "approved"
                rec["proposed_canonical"] = proposed_canonical
                rec["reviewed_at"] = now_iso()
                updated = rec
            all_rows.append(rec)
    path.write_text("\n".join(json.dumps(r, sort_keys=True, default=str) for r in all_rows) + ("\n" if all_rows else ""), encoding="utf-8")
    if updated:
        publish(
            "schema.updated.v1",
            {
                "note": "approval_recorded_registry_update_pending",
                "queue_id": queue_id,
                "proposed_canonical": proposed_canonical,
            },
        )
    return updated or {"ok": False, "error": "not_found"}
