"""Live vs historical scheduling (FSE-02 §9)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.collection.jobs import make_job
from financial_statements_engine.collection.schema import HISTORICAL_PRIORITY_ORDER
from financial_statements_engine.collection.sources import source_rank


def priority_for_mode(mode: str, *, period_type: str | None, source: str, depth_bucket: str | None = None) -> int:
    """Lower number = run sooner."""
    base = source_rank(source)
    if mode == "live":
        return 10 + base // 10
    # historical: coverage before depth
    bucket = depth_bucket or ("latest_annual" if period_type == "annual" else "latest_quarter")
    try:
        depth_rank = HISTORICAL_PRIORITY_ORDER.index(bucket)  # type: ignore[arg-type]
    except ValueError:
        depth_rank = len(HISTORICAL_PRIORITY_ORDER)
    return 100 + depth_rank * 100 + base // 10


def plan_jobs(
    ticker: str,
    discoveries: list[dict[str, Any]],
    *,
    mode: str = "live",
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for disc in discoveries:
        meta = disc.get("metadata") if isinstance(disc.get("metadata"), dict) else disc
        period_type = str(meta.get("period_type") or "unknown")
        source = str(meta.get("source") or "nse_integrated_filing")
        depth = None
        if mode == "historical":
            depth = "latest_annual" if period_type == "annual" else "latest_quarter"
        job = make_job(
            ticker=ticker,
            source=source,
            document_type=str(meta.get("document_type") or "xbrl"),
            period_type=period_type,
            period_end=meta.get("period_end"),
            mode=mode,
            priority=priority_for_mode(mode, period_type=period_type, source=source, depth_bucket=depth),
            entity=meta.get("entity"),
            discovery_ref=disc.get("discovery_id"),
            url=meta.get("source_url"),
        )
        jobs.append(job)
    jobs.sort(key=lambda j: (int(j.get("priority") or 999), str(j.get("period_end") or "")))
    return jobs
