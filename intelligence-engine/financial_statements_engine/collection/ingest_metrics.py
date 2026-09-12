"""FSE-02.1 Mission Control — ingestion metrics (append-only JSONL)."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso


def _path() -> Path:
    root = ensure_dirs()
    path = root / "collection" / "ingest_metrics.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def record_ingest_metric(row: dict[str, Any]) -> None:
    entry = {"ts": now_iso(), **row}
    line = json.dumps(entry, sort_keys=True, default=str)
    with _path().open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def summarize_ingest_metrics(*, limit: int = 5000) -> dict[str, Any]:
    path = _path()
    if not path.exists():
        return {
            "collected_today": 0,
            "duplicate_filings": 0,
            "failed_downloads": 0,
            "stored_evidence": 0,
            "event_emissions": 0,
            "average_ingest_latency_ms": None,
            "source_distribution": {},
            "latest_filing_time": None,
            "rows": 0,
            "as_of": now_iso(),
        }

    today = datetime.now(timezone.utc).date().isoformat()
    collected_today = 0
    duplicates = 0
    failed = 0
    stored = 0
    events = 0
    latencies: list[float] = []
    sources: Counter[str] = Counter()
    latest: datetime | None = None

    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines[-max(1, int(limit)) :]:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = _parse_ts(row.get("ts"))
        if ts and (latest is None or ts > latest):
            latest = ts
        if ts and ts.date().isoformat() == today:
            collected_today += 1
        action = str(row.get("action") or "")
        if action == "duplicate_skipped":
            duplicates += 1
        elif action in {"stored", "restatement_candidate"}:
            stored += 1
        elif action in {"failed", "download_failed"}:
            failed += 1
        if row.get("event_emitted"):
            events += 1
        lat = row.get("latency_ms")
        if isinstance(lat, (int, float)):
            latencies.append(float(lat))
        src = str(row.get("source") or "unknown")
        sources[src] += 1

    avg = round(sum(latencies) / len(latencies), 2) if latencies else None
    return {
        "collected_today": collected_today,
        "duplicate_filings": duplicates,
        "failed_downloads": failed,
        "stored_evidence": stored,
        "event_emissions": events,
        "average_ingest_latency_ms": avg,
        "source_distribution": dict(sources.most_common()),
        "latest_filing_time": latest.isoformat() if latest else None,
        "rows": len(lines),
        "as_of": now_iso(),
    }
