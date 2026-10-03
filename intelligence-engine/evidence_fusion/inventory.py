"""Read-only inventory — warehouse/DME + FIRE-01/02/03 (injectable for tests)."""

from __future__ import annotations

from typing import Any

from evidence_fusion.schema import FUSION_METRICS


def load_fusion_inputs(
    ticker: str,
    *,
    series_map: dict[str, list[dict[str, Any]]] | None = None,
    fire01_findings: list[dict[str, Any]] | None = None,
    fire02_relationships: list[dict[str, Any]] | None = None,
    fire03_facts: list[dict[str, Any]] | None = None,
    coverage_pct: float | None = None,
    fire03_documents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    t = ticker.upper().strip()
    notes: list[str] = []

    # --- Metric series ---
    series: dict[str, list[dict[str, Any]]]
    cov = coverage_pct
    if series_map is not None:
        series = {m: list(series_map.get(m) or []) for m in FUSION_METRICS}
        for k, v in series_map.items():
            if k not in series:
                series[k] = list(v or [])
        notes.append("injected_series")
    else:
        series = {m: [] for m in FUSION_METRICS}
        try:
            from financial_intelligence.inventory import load_metric_series

            inv = load_metric_series(t, metrics=FUSION_METRICS)
            series = inv.get("series") or series
            if cov is None:
                raw = inv.get("coverage") or {}
                for key in ("overall_completeness_pct", "coverage_pct", "average_coverage_pct"):
                    if isinstance(raw.get(key), (int, float)):
                        cov = float(raw[key])
                        break
            notes.append("warehouse_dme")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"warehouse_unavailable:{type(exc).__name__}")

    # --- FIRE-01 ---
    findings: list[dict[str, Any]]
    if fire01_findings is not None:
        findings = list(fire01_findings)
        notes.append("injected_fire01")
    else:
        findings = []
        try:
            from financial_intelligence.findings import findings_from_series

            findings = findings_from_series(series, coverage_pct=cov, ticker=t)
            notes.append("fire01_from_series")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"fire01_unavailable:{type(exc).__name__}")

    # --- FIRE-02 ---
    relationships: list[dict[str, Any]]
    if fire02_relationships is not None:
        relationships = list(fire02_relationships)
        notes.append("injected_fire02")
    else:
        relationships = []
        try:
            from financial_intelligence.drivers.production import relationships as fire02_rels

            pack = fire02_rels(t, series_map=series)
            relationships = list(pack.get("relationships") or [])
            notes.append("fire02_live")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"fire02_unavailable:{type(exc).__name__}")

    # --- FIRE-03 ---
    facts: list[dict[str, Any]]
    sources: list[dict[str, Any]] = []
    if fire03_facts is not None:
        facts = list(fire03_facts)
        notes.append("injected_fire03")
    else:
        facts = []
        try:
            from business_intelligence.production import company as fire03_company

            kwargs: dict[str, Any] = {}
            if fire03_documents is not None:
                kwargs["documents"] = fire03_documents
            pack = fire03_company(t, **kwargs)
            facts = list(pack.get("facts") or [])
            sources = list(pack.get("sources") or [])
            notes.append("fire03_live")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"fire03_unavailable:{type(exc).__name__}")

    return {
        "ticker": t,
        "series": series,
        "fire01_findings": findings,
        "fire02_relationships": relationships,
        "fire03_facts": facts,
        "fire03_sources": sources,
        "coverage_pct": cov,
        "notes": notes,
        "read_only": True,
        "mutated_warehouse": False,
    }
