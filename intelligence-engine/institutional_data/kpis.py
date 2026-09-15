"""Operational readiness KPIs for institutional historical data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def production_kpis() -> dict[str, Any]:
    from continuous_gather_learn.ops_observability import (
        backfill_throughput,
        collector_health_rows,
        coverage_heat_map,
    )
    from institutional_data.connectors.registry import get_connector
    from institutional_data.persistence.resume import ResumeManager
    from institutional_data.reliability.scores import reliability_dashboard
    from knowledge_factory.historical_depth import queue as bf_queue

    collectors = collector_health_rows()
    ok_n = sum(1 for c in collectors if c.get("success") == "ok")
    heat = {r["dataset"]: r["coverage_pct"] for r in coverage_heat_map()}
    fin = get_connector("financial_statements").coverage()
    sh = get_connector("shareholding").coverage()
    ir = get_connector("company_ir").coverage()
    thr = backfill_throughput()
    stats = bf_queue.backlog_stats()
    resume = ResumeManager().status()
    rel = reliability_dashboard()

    # Extracts / embeddings
    extracts = embeddings = 0
    try:
        from continuous_gather_learn import persist as cgl_persist
        from pathlib import Path

        root = cgl_persist.store_root()
        extracts = len(list((root / "knowledge").glob("*.json"))) if (root / "knowledge").exists() else 0
        embeddings = len(list((root / "embeddings").glob("*.json"))) if (root / "embeddings").exists() else 0
    except Exception:
        pass

    return {
        "kpi_version": "institutional-data-kpis-v1.0.0",
        "generated_at": _now(),
        "collector_success_rate": round(100.0 * ok_n / max(1, len(collectors)), 1),
        "financial_coverage_pct": fin.get("coverage_pct"),
        "shareholding_coverage_pct": sh.get("coverage_pct"),
        "ir_coverage_pct": ir.get("coverage_pct"),
        "ohlcv_coverage_pct": heat.get("OHLCV"),
        "average_historical_years": stats.get("average_years"),
        "repair_queue_size": len((ResumeManager().ck.load("coverage_repair_queue") or {}).get("items") or []),
        "knowledge_extracts": extracts,
        "embeddings": embeddings,
        "storage_growth": resume.get("storage"),
        "backfill_speed_companies_today": thr.get("companies_completed_today"),
        "queue_drain_rate": thr.get("companies_completed_today"),
        "historical_completeness_pct": stats.get("coverage_pct"),
        "remaining_backlog": stats.get("remaining"),
        "source_reliability": rel,
        "north_star": "production_grade_institutional_historical_data",
    }
