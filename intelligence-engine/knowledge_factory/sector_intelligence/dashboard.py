"""Institutional Sector Intelligence Coverage — Sprint 5 north-star KPI."""

from __future__ import annotations

from typing import Any

from knowledge_factory.sector_intelligence import store as isi_store
from knowledge_factory.sector_intelligence.dna.catalog import sector_dna
from knowledge_factory.sector_intelligence.schema import ISI_VERSION, SECTOR_UNIVERSE


def sector_intelligence_dashboard(sectors: list[str] | None = None) -> dict[str, Any]:
    sectors = list(sectors or SECTOR_UNIVERSE)
    n = len(sectors) or 1
    objects = 0
    dna_scores = []
    hist_years = []
    macro_ok = 0
    cycle_ok = 0
    framework_ok = 0
    leadership_ok = 0
    qualities = []
    playbooks = 0

    for s in sectors:
        obj = isi_store.get_object(s)
        dna = sector_dna(s)
        dna_scores.append(float(dna.get("dna_completeness") or 0))
        if not obj:
            continue
        objects += 1
        cov = obj.get("coverage") or {}
        hist_years.append(float(cov.get("history_years") or 0))
        if obj.get("macro_relationships"):
            macro_ok += 1
        if (obj.get("historical_cycles") or {}).get("current_cycle") not in {None, "unknown"}:
            cycle_ok += 1
        if obj.get("valuation_framework_mapping"):
            framework_ok += 1
        if not (obj.get("historical_leadership") or {}).get("insufficient"):
            leadership_ok += 1
        qualities.append(float(obj.get("evidence_quality") or 0))
        if obj.get("sector_playbook"):
            playbooks += 1

    report = isi_store.get_report("sector_pipeline") or {}
    board = {
        "isi_version": ISI_VERSION,
        "title": "Institutional Sector Intelligence Coverage",
        "north_star": "institutional_sector_intelligence_coverage",
        "kpi_rule": "Every PR must improve at least one measurable operational KPI.",
        "architecture_frozen": "REASONING_V1",
        "sector_coverage": objects,
        "sector_declared": len(sectors),
        "sector_coverage_pct": round(100.0 * objects / n, 2),
        "sector_dna_completeness": round(sum(dna_scores) / len(dna_scores), 2) if dna_scores else 0.0,
        "historical_completeness_pct": round(
            100.0 * sum(1 for y in hist_years if y >= 10) / n, 2
        ),
        "average_history_years": round(sum(hist_years) / len(hist_years), 2) if hist_years else 0.0,
        "macro_relationship_coverage_pct": round(100.0 * macro_ok / n, 2),
        "cycle_coverage_pct": round(100.0 * cycle_ok / n, 2),
        "framework_coverage_pct": round(100.0 * framework_ok / n, 2),
        "leadership_coverage_pct": round(100.0 * leadership_ok / n, 2),
        "playbook_coverage_pct": round(100.0 * playbooks / n, 2),
        "average_evidence_quality": round(sum(qualities) / len(qualities), 2) if qualities else 0.0,
        "validation_failures": len(report.get("validation_failures") or []),
        "roadmap_next": "macro_intelligence",
    }
    isi_store.put_report("sector_intelligence_coverage", board)
    return board
