"""Persist FIE outputs to warehouse tabs (append-only history; master summary)."""

from __future__ import annotations

from typing import Any

from forecast_intelligence_engine.models import ENGINE_CODE


def persist_forecast(pack: dict[str, Any]) -> dict[str, Any]:
    """Best-effort write of forecast summary + history + scenarios + assumptions."""
    written = {"forecast_company": 0, "forecast_history": 0, "forecast_scenarios": 0, "forecast_assumptions": 0, "forecast_metric_predictions": 0}
    try:
        from institutional_warehouse import gateway
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}

    symbol = pack.get("symbol")
    as_of = (pack.get("generated_at") or "")[:10]
    quality = pack.get("forecast_quality") or {}
    modules = pack.get("modules") or {}
    executive = modules.get("executive") or {}
    scenarios = modules.get("scenarios") or {}
    probs = scenarios.get("probabilities") or pack.get("probabilities") or {}

    summary = {
        "symbol": symbol,
        "as_of": as_of,
        "forecast_confidence": quality.get("forecast_confidence"),
        "score": quality.get("score"),
        "coverage_pct": quality.get("coverage_pct"),
        "status": pack.get("status"),
        "dqiv": (pack.get("dqiv") or {}).get("status"),
        "executive_summary": (pack.get("executive_summary") or "")[:500],
        "bull_pct": probs.get("bull"),
        "base_pct": probs.get("base"),
        "bear_pct": probs.get("bear"),
        "modules_ok": sum(1 for k, v in modules.items() if k != "confidence" and v.get("ok")),
        "version": pack.get("version"),
    }
    try:
        r = gateway.write(
            "forecast_company",
            [summary],
            source=ENGINE_CODE,
            actor="fie",
            reason="fie_company_summary",
        )
        written["forecast_company"] = int(r.get("written") or 0)
    except Exception:
        pass

    history_row = {
        **summary,
        "event": "generated",
        "generated_at": pack.get("generated_at"),
    }
    try:
        r = gateway.write(
            "forecast_history",
            [history_row],
            source=ENGINE_CODE,
            actor="fie",
            reason="fie_history_append",
        )
        written["forecast_history"] = int(r.get("written") or 0)
    except Exception:
        pass

    scen_rows = []
    for name, payload in (scenarios.get("scenarios") or {}).items():
        scen_rows.append({
            "symbol": symbol,
            "as_of": as_of,
            "scenario": name,
            "probability_pct": probs.get(name),
            "payload_summary": str((payload or {}).get("growth_rates_used") or "")[:280],
            "status": "generated",
        })
    if scen_rows:
        try:
            r = gateway.write(
                "forecast_scenarios",
                scen_rows,
                source=ENGINE_CODE,
                actor="fie",
                reason="fie_scenarios_append",
            )
            written["forecast_scenarios"] = int(r.get("written") or 0)
        except Exception:
            pass

    # Freeze the forecast line items before any future actual can be observed.
    try:
        from forecast_intelligence_engine.accuracy import prediction_rows

        metric_rows = prediction_rows(pack)
        if metric_rows:
            r = gateway.write(
                "forecast_metric_predictions",
                metric_rows,
                source=ENGINE_CODE,
                actor="fie",
                reason="immutable_forecast_vintage",
                detect_conflicts=False,
            )
            written["forecast_metric_predictions"] = int(r.get("written") or 0)
    except Exception:
        pass

    # Atomic assumptions are independently testable against each consequence.
    assum_rows = []
    try:
        from forecast_intelligence_engine.accuracy import prediction_rows

        for row in prediction_rows(pack):
            metric_name = row.get("metric")
            assum_rows.append({
                "symbol": symbol,
                "as_of": as_of,
                "generated_at": pack.get("generated_at"),
                "name": f"{metric_name}_growth_anchor",
                "metric": metric_name,
                "horizon": row.get("horizon"),
                "scenario": row.get("scenario"),
                "value": row.get("historical_cagr_pct"),
                "basis": "warehouse_historical_cagr",
                "assumption_type": "derived",
                "expected_consequence": row.get("forecast_value"),
                "confidence": row.get("forecast_confidence"),
                "status": "OPEN",
            })
    except Exception:
        assum_rows = []
    if assum_rows:
        try:
            r = gateway.write(
                "forecast_assumptions",
                assum_rows,
                source=ENGINE_CODE,
                actor="fie",
                reason="fie_assumptions_append",
            )
            written["forecast_assumptions"] = int(r.get("written") or 0)
        except Exception:
            pass

    try:
        gateway.write(
            "forecast_confidence",
            [{
                "symbol": symbol,
                "as_of": as_of,
                "forecast_confidence": quality.get("forecast_confidence"),
                "score": quality.get("score"),
                "coverage_pct": quality.get("coverage_pct"),
                "high_n": (quality.get("distribution") or {}).get("High"),
                "medium_n": (quality.get("distribution") or {}).get("Medium"),
                "low_n": (quality.get("distribution") or {}).get("Low"),
            }],
            source=ENGINE_CODE,
            actor="fie",
            reason="fie_confidence_append",
        )
    except Exception:
        pass

    snapshot = pack.get("forecast_snapshot") or {}
    if snapshot:
        try:
            r = gateway.write(
                "forecast_snapshots", [snapshot], source=ENGINE_CODE, actor="fie",
                reason="point_in_time_forecast_snapshot", detect_conflicts=False,
            )
            written["forecast_snapshots"] = int(r.get("written") or 0)
        except Exception:
            pass

    return {"ok": True, "written": written}
