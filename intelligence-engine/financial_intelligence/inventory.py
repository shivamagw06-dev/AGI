"""Read-only inventory from Financial Warehouse + DME + coverage metadata."""

from __future__ import annotations

from typing import Any

from financial_intelligence.schema import TREND_METRICS


def _fact_to_point(fact: dict[str, Any], metric: str) -> dict[str, Any] | None:
    val = fact.get("value")
    if not isinstance(val, (int, float)):
        return None
    pe = fact.get("reporting_period") or fact.get("period")
    if not pe:
        return None
    return {
        "period": str(pe)[:10],
        "value": float(val),
        "version": fact.get("version") or fact.get("version_number") or 0,
        "warehouse_version": fact.get("warehouse_version"),
        "validation_id": fact.get("validation_id"),
        "validation_status": fact.get("validation_status"),
        "quality_score": fact.get("quality_score"),
        "fact_key": fact.get("fact_key"),
        "metric": metric,
    }


def _series_from_latest_facts(facts: list[dict[str, Any]], metric: str) -> list[dict[str, Any]]:
    out = []
    for f in facts or []:
        name = str(f.get("canonical_metric") or f.get("metric") or "").lower()
        if name != metric:
            continue
        pt = _fact_to_point(f, metric)
        if pt:
            out.append(pt)
    return out


def load_metric_series(ticker: str, metrics: tuple[str, ...] | list[str] = TREND_METRICS) -> dict[str, Any]:
    """Load metric time series via warehouse history + DME company metrics (read-only)."""
    t = ticker.upper().strip()
    series_map: dict[str, list[dict[str, Any]]] = {m: [] for m in metrics}
    warehouse_version = None
    validation_notes: list[dict[str, Any]] = []

    # Warehouse latest facts (multi-period if published that way)
    try:
        from financial_statements_engine.financial_warehouse.production import get_latest, get_metric_history

        latest = get_latest(t)
        warehouse_version = None
        for f in latest.get("facts") or []:
            if f.get("warehouse_version"):
                warehouse_version = f.get("warehouse_version")
                break
        for m in metrics:
            hist = get_metric_history(t, m)
            rows = []
            for f in hist.get("history") or []:
                pt = _fact_to_point(f, m)
                if pt:
                    rows.append(pt)
            if not rows:
                rows = _series_from_latest_facts(latest.get("facts") or [], m)
            series_map[m] = rows
    except Exception as exc:  # noqa: BLE001
        validation_notes.append({"source": "warehouse", "error": str(exc)[:200]})

    # DME overlays (margins / returns) — never call calculate()
    try:
        from financial_statements_engine.derived_metrics.production import company_metrics, get_metric

        cm = company_metrics(t)
        stored = cm.get("metrics") or cm.get("data") or []
        if isinstance(stored, dict):
            stored_items = [{"metric": k, **(v if isinstance(v, dict) else {"value": v})} for k, v in stored.items()]
        else:
            stored_items = list(stored or [])
        for item in stored_items:
            m = str(item.get("metric") or item.get("metric_id") or item.get("name") or "").lower()
            if m not in series_map:
                # allow equity / debt_to_equity for quality
                if m in {"total_equity", "equity", "debt_to_equity", "gross_margin"}:
                    series_map.setdefault(m, [])
                else:
                    continue
            pt = _fact_to_point(
                {
                    "value": item.get("value"),
                    "reporting_period": item.get("period") or item.get("reporting_period"),
                    "version": item.get("metric_version") or item.get("version") or 0,
                    "warehouse_version": item.get("warehouse_version") or warehouse_version,
                    "validation_id": item.get("lineage_reference") or item.get("validation_id"),
                    "validation_status": item.get("quality_status") or item.get("validation_status"),
                    "quality_score": item.get("quality_score"),
                    "fact_key": item.get("metric_id") or m,
                },
                m,
            )
            if pt:
                series_map.setdefault(m, []).append(pt)
        # Fill missing via get_metric if empty
        for m in list(series_map.keys()):
            if series_map[m]:
                continue
            try:
                one = get_metric(t, m)
                data = one.get("metric") or one.get("data") or one
                if isinstance(data, dict) and isinstance(data.get("value"), (int, float)):
                    pt = _fact_to_point(
                        {
                            "value": data.get("value"),
                            "reporting_period": data.get("period") or data.get("reporting_period"),
                            "version": data.get("metric_version") or 0,
                            "warehouse_version": warehouse_version,
                            "validation_status": data.get("quality_status"),
                        },
                        m,
                    )
                    if pt:
                        series_map[m] = [pt]
            except Exception:
                continue
    except Exception as exc:  # noqa: BLE001
        validation_notes.append({"source": "dme", "error": str(exc)[:200]})

    coverage: dict[str, Any] = {}
    try:
        from financial_statements_engine.fdo.production import coverage_company

        coverage = coverage_company(t)
    except Exception:
        try:
            from financial_statements_engine.evidence_coverage.production import company as ecd_company

            coverage = ecd_company(t)
        except Exception as exc:  # noqa: BLE001
            validation_notes.append({"source": "coverage", "error": str(exc)[:200]})

    validation: dict[str, Any] = {}
    try:
        from financial_statements_engine.validation.production import reports_for

        validation = reports_for(t)
    except Exception as exc:  # noqa: BLE001
        validation_notes.append({"source": "validation", "error": str(exc)[:200]})

    return {
        "ticker": t,
        "series": series_map,
        "warehouse_version": warehouse_version,
        "coverage": coverage,
        "validation": validation,
        "notes": validation_notes,
        "read_only": True,
        "mutated_warehouse": False,
    }
