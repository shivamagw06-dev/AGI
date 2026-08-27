"""Observability — stage metrics for Mission Control surfaces."""

from __future__ import annotations

import json
from typing import Any

from financial_statements_engine.schema import QUALITY_TARGETS
from financial_statements_engine.store import ensure_dirs, store_root
from financial_statements_engine.util import now_iso


def record_event(event: dict[str, Any]) -> None:
    root = ensure_dirs()
    path = root / "observability" / "metrics.jsonl"
    row = {"ts": now_iso(), **event}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def dashboard() -> dict[str, Any]:
    root = store_root()
    published = root / "published"
    companies = sorted([p.name for p in published.iterdir()]) if published.exists() else []
    metrics_path = root / "observability" / "metrics.jsonl"
    events = 0
    if metrics_path.exists():
        events = sum(1 for _ in metrics_path.open(encoding="utf-8"))

    return {
        "engine": "financial_statements_engine",
        "coverage": {
            "published_companies": len(companies),
            "tickers_sample": companies[:20],
        },
        "quality_targets": QUALITY_TARGETS,
        "observability": {
            "events_recorded": events,
            "metrics_path": str(metrics_path),
        },
        "layers": {
            "raw_evidence": True,
            "extraction": True,
            "normalization": True,
            "canonical": True,
            "validation": True,
            "version_control": True,
            "warehouse": True,
            "derived_metrics": True,
        },
        "as_of": now_iso(),
    }
