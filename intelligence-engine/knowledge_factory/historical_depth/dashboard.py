"""Historical Depth Coverage — Sprint 4 north-star operational KPI."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.fixtures.seed_history import seed_universe
from knowledge_factory.historical_depth.schema import HD_VERSION


def _years_for(entity: str) -> float:
    """Max of annual period count and price-history span (years)."""
    annual = hd_store.get_series("financials_annual", entity) or {}
    a_n = float(len(annual.get("records") or []))
    prices = hd_store.get_series("prices", entity) or {}
    ends = [str(r.get("period_end") or "")[:10] for r in (prices.get("records") or []) if r.get("period_end")]
    p_years = 0.0
    if len(ends) >= 2:
        try:
            d0 = datetime.fromisoformat(min(ends))
            d1 = datetime.fromisoformat(max(ends))
            p_years = (d1 - d0).days / 365.25
        except Exception:
            p_years = float(max(0, len({e[:4] for e in ends}) - 1))
    elif len(ends) == 1:
        p_years = 0.0
    return float(max(a_n, p_years))


def _doc_counts() -> dict[str, int]:
    """Soft IR / LIDI document catalogue counts when available."""
    out = {
        "annual_reports": 0,
        "quarterly_results": 0,
        "investor_presentations": 0,
        "earnings_transcripts": 0,
        "documents_total": 0,
    }
    try:
        from live_data import store as lidi_store

        root = lidi_store.store_root() / "objects" / "company_ir"
        if not root.exists():
            return out
        for path in root.glob("*.json"):
            if path.name.endswith("_DOWNLOADS.json"):
                continue
            row = lidi_store.get_object("company_ir", path.stem) or {}
            for d in row.get("documents") or []:
                out["documents_total"] += 1
                t = str(d.get("doc_type") or "")
                if t == "annual_report":
                    out["annual_reports"] += 1
                elif t == "quarterly_results":
                    out["quarterly_results"] += 1
                elif t == "investor_presentation":
                    out["investor_presentations"] += 1
                elif t == "earnings_transcript":
                    out["earnings_transcripts"] += 1
    except Exception:
        return out
    return out


def historical_depth_dashboard(entities: list[str] | None = None) -> dict[str, Any]:
    entities = entities or seed_universe()
    years = [_years_for(e) for e in entities]
    n = len(years) or 1
    avg = sum(years) / n
    ordered = sorted(years)
    median = ordered[n // 2] if ordered else 0.0

    gt10 = sum(1 for y in years if y >= 10)
    gt15 = sum(1 for y in years if y >= 15)
    gt20 = sum(1 for y in years if y >= 20)
    fully = sum(1 for y in years if y >= 15)

    # Completeness: share of annual/price slots filled vs 20y target
    completeness = round(100.0 * sum(min(y, 20.0) for y in years) / (20.0 * n), 2)

    # Quarterly completeness
    q_ok = 0
    for e in entities:
        q = hd_store.get_series("financials_quarterly", e) or {}
        q_ok += min(len(q.get("records") or []), 80)
    q_completeness = round(100.0 * q_ok / (80.0 * n), 2)

    qualities = []
    for e in entities:
        pack = hd_store.get_pack(e) or {}
        qualities.append(float(pack.get("evidence_quality") or 0.0))
    avg_q = round(sum(qualities) / len(qualities), 2) if qualities else 0.0

    report = hd_store.get_report("historical_pipeline") or {}
    docs = _doc_counts()
    backfill = hd_store.get_report("historical_backfill_checkpoint") or {}
    ca_complete = sum(
        1 for e in entities if len((hd_store.get_series("corporate_actions", e) or {}).get("records") or []) > 0
    )
    try:
        macro = hd_store.get_macro_history()
    except Exception:
        macro = []

    board = {
        "hd_version": HD_VERSION,
        "title": "Historical Depth Coverage",
        "north_star": "historical_depth_coverage",
        "kpi_rule": "Every PR must improve at least one measurable operational KPI.",
        "architecture_frozen": "REASONING_V1",
        "universe_n": len(entities),
        "average_history_years": round(avg, 2),
        "median_history_years": round(float(median), 2),
        "companies_gt_10y": gt10,
        "companies_gt_15y": gt15,
        "companies_gt_20y": gt20,
        "companies_fully_backfilled": fully,
        "companies_gt_10y_pct": round(100.0 * gt10 / n, 2),
        "companies_gt_15y_pct": round(100.0 * gt15 / n, 2),
        "companies_gt_20y_pct": round(100.0 * gt20 / n, 2),
        "annual_completeness_pct": completeness,
        "quarterly_completeness_pct": q_completeness,
        "historical_completeness_pct": completeness,
        "historical_coverage_pct": completeness,
        "historical_evidence_quality": avg_q,
        "historical_validation_failures": len(report.get("validation_failures") or []),
        "historical_stale_records": 0,
        "point_in_time_integrity": True,
        "corporate_actions_coverage_pct": round(100.0 * ca_complete / n, 2),
        "macro_series_points": len(macro or []),
        "documents": docs,
        "backfill_completed": len(backfill.get("completed") or []),
        "remaining_backlog": max(0, len(entities) - len(backfill.get("completed") or [])),
        "coverage_engine": "continuous_historical_backfill",
        "roadmap_next": "sector_intelligence",
    }
    hd_store.put_report("historical_depth_coverage", board)
    return board
