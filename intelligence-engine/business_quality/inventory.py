"""Read-only inventory — warehouse + FIRE-01…05 (injectable for tests)."""

from __future__ import annotations

from typing import Any

from business_quality.schema import QUALITY_METRICS


def load_quality_inputs(
    ticker: str,
    *,
    series_map: dict[str, list[dict[str, Any]]] | None = None,
    fire01_findings: list[dict[str, Any]] | None = None,
    fire02_relationships: list[dict[str, Any]] | None = None,
    fire03_facts: list[dict[str, Any]] | None = None,
    fire04_findings: list[dict[str, Any]] | None = None,
    fire05_score: dict[str, Any] | None = None,
    fire05_findings: list[dict[str, Any]] | None = None,
    coverage_pct: float | None = None,
) -> dict[str, Any]:
    t = ticker.upper().strip()
    notes: list[str] = []
    cov = coverage_pct

    if series_map is not None:
        series = {m: list(series_map.get(m) or []) for m in QUALITY_METRICS}
        for k, v in series_map.items():
            if k not in series:
                series[k] = list(v or [])
        notes.append("injected_series")
    else:
        series = {m: [] for m in QUALITY_METRICS}
        try:
            from financial_intelligence.inventory import load_metric_series

            inv = load_metric_series(t, metrics=QUALITY_METRICS)
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

    def _fire01() -> list[dict[str, Any]]:
        if fire01_findings is not None:
            notes.append("injected_fire01")
            return list(fire01_findings)
        try:
            from financial_intelligence.findings import findings_from_series

            notes.append("fire01_from_series")
            return findings_from_series(series, coverage_pct=cov, ticker=t)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"fire01_unavailable:{type(exc).__name__}")
            return []

    def _fire02() -> list[dict[str, Any]]:
        if fire02_relationships is not None:
            notes.append("injected_fire02")
            return list(fire02_relationships)
        try:
            from financial_intelligence.drivers.production import relationships

            notes.append("fire02_live")
            return list((relationships(t, series_map=series) or {}).get("relationships") or [])
        except Exception as exc:  # noqa: BLE001
            notes.append(f"fire02_unavailable:{type(exc).__name__}")
            return []

    def _fire03() -> list[dict[str, Any]]:
        if fire03_facts is not None:
            notes.append("injected_fire03")
            return list(fire03_facts)
        try:
            from business_intelligence.production import company as bi

            notes.append("fire03_live")
            return list((bi(t) or {}).get("facts") or [])
        except Exception as exc:  # noqa: BLE001
            notes.append(f"fire03_unavailable:{type(exc).__name__}")
            return []

    facts = _fire03()

    def _fire04() -> list[dict[str, Any]]:
        if fire04_findings is not None:
            notes.append("injected_fire04")
            return list(fire04_findings)
        try:
            from evidence_fusion.production import company as ef

            notes.append("fire04_live")
            return list(
                (
                    ef(t, series_map=series, fire03_facts=facts, coverage_pct=cov) or {}
                ).get("findings")
                or []
            )
        except Exception as exc:  # noqa: BLE001
            notes.append(f"fire04_unavailable:{type(exc).__name__}")
            return []

    def _fire05() -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        if fire05_score is not None or fire05_findings is not None:
            notes.append("injected_fire05")
            return fire05_score, list(fire05_findings or [])
        try:
            from management_execution.production import company as me

            notes.append("fire05_live")
            pack = me(
                t,
                series_map=series,
                fire03_facts=facts,
                fire04_findings=[],
                coverage_pct=cov,
            )
            return pack.get("score"), list(pack.get("findings") or [])
        except Exception as exc:  # noqa: BLE001
            notes.append(f"fire05_unavailable:{type(exc).__name__}")
            return None, []

    f01 = _fire01()
    f02 = _fire02()
    f04 = _fire04()
    f05_score, f05_findings = _fire05()

    return {
        "ticker": t,
        "series": series,
        "fire01_findings": f01,
        "fire02_relationships": f02,
        "fire03_facts": facts,
        "fire04_findings": f04,
        "fire05_score": f05_score,
        "fire05_findings": f05_findings,
        "coverage_pct": cov,
        "notes": notes,
        "read_only": True,
        "mutated_warehouse": False,
    }
