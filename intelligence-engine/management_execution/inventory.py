"""Read-only inputs — FIRE-03 facts, warehouse series, optional FIRE-04 (injectable)."""

from __future__ import annotations

from typing import Any

from management_execution.schema import EXECUTION_METRICS


def load_execution_inputs(
    ticker: str,
    *,
    series_map: dict[str, list[dict[str, Any]]] | None = None,
    fire03_facts: list[dict[str, Any]] | None = None,
    fire03_documents: list[dict[str, Any]] | None = None,
    fire04_findings: list[dict[str, Any]] | None = None,
    coverage_pct: float | None = None,
) -> dict[str, Any]:
    t = ticker.upper().strip()
    notes: list[str] = []

    series: dict[str, list[dict[str, Any]]]
    cov = coverage_pct
    if series_map is not None:
        series = {m: list(series_map.get(m) or []) for m in EXECUTION_METRICS}
        for k, v in series_map.items():
            if k not in series:
                series[k] = list(v or [])
        notes.append("injected_series")
    else:
        series = {m: [] for m in EXECUTION_METRICS}
        try:
            from financial_intelligence.inventory import load_metric_series

            inv = load_metric_series(t, metrics=EXECUTION_METRICS)
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

    fusion: list[dict[str, Any]]
    if fire04_findings is not None:
        fusion = list(fire04_findings)
        notes.append("injected_fire04")
    else:
        fusion = []
        try:
            from evidence_fusion.production import company as fire04_company

            pack = fire04_company(
                t,
                series_map=series,
                fire03_facts=facts,
                coverage_pct=cov,
            )
            fusion = list(pack.get("findings") or [])
            notes.append("fire04_live")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"fire04_unavailable:{type(exc).__name__}")

    return {
        "ticker": t,
        "series": series,
        "fire03_facts": facts,
        "fire03_sources": sources,
        "fire04_findings": fusion,
        "coverage_pct": cov,
        "notes": notes,
        "read_only": True,
        "mutated_warehouse": False,
    }
