"""Immutable forecast vintages and point-in-time outcome evaluation."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from forecast_intelligence_engine.evidence import metric
from forecast_intelligence_engine.models import ENGINE_CODE
from forecast_intelligence_engine.models import SCENARIO_GROWTH_MULT, SCENARIO_MARGIN_DELTA_PP

_ALIASES = {
    "revenue": ("revenue", "total_revenue", "sales"),
    "ebitda": ("ebitda",),
    "ebit": ("ebit", "operating_profit"),
    "pat": ("pat", "net_income", "profit_after_tax"),
    "eps": ("eps",),
    "book_value": ("equity", "shareholders_equity"),
    "operating_cash_flow": ("cfo", "operating_cash_flow"),
    "free_cash_flow": ("free_cash_flow", "fcf"),
}
_YEARS = {"FY+1": 1, "FY+2": 2, "FY+3": 3, "FY+5": 5}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def target_period(base_period: Any, horizon: str) -> Optional[str]:
    """Advance common fiscal-year labels while retaining their representation."""
    years = _YEARS.get(str(horizon))
    raw = str(base_period or "").strip()
    if years is None or not raw:
        return None
    match = re.search(r"(?i)FY\s*[-/]?\s*(\d{2,4})", raw)
    if match:
        digits = match.group(1)
        value = int(digits) + years
        width = len(digits)
        return f"FY{value % (100 if width == 2 else 10000):0{width}d}"
    range_match = re.fullmatch(r"((?:19|20)\d{2})[-/]([0-9]{2,4})", raw)
    if range_match:
        start, end = range_match.groups()
        end_mod = 100 if len(end) == 2 else 10000
        separator = "/" if "/" in raw else "-"
        return f"{int(start) + years}{separator}{(int(end) + years) % end_mod:0{len(end)}d}"
    match = re.search(r"(19|20)\d{2}", raw)
    if match:
        year = int(match.group(0)) + years
        return raw[: match.start()] + str(year) + raw[match.end() :]
    return None


def prediction_rows(pack: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten scenario line items into an immutable, gradeable forecast vintage."""
    modules = pack.get("modules") or {}
    scenarios = (modules.get("scenarios") or {}).get("scenarios") or {}
    probabilities = pack.get("probabilities") or {}
    quality = pack.get("forecast_quality") or {}
    generated_at = pack.get("generated_at") or _now()
    rows: list[dict[str, Any]] = []
    for scenario, payload in scenarios.items():
        payload = payload or {}
        base_period = payload.get("base_period")
        base_values = payload.get("base_values") or {}
        growth_rates = payload.get("growth_rates_used") or {}
        for metric_name, horizons in (payload.get("lines") or {}).items():
            for horizon, value in (horizons or {}).items():
                # NQ is intentionally excluded until the model produces a true
                # quarterly target comparable with a reported quarterly actual.
                period = target_period(base_period, horizon)
                if value is None or period is None:
                    continue
                rows.append({
                    "symbol": pack.get("symbol"),
                    "forecast_as_of": str(generated_at)[:10],
                    "generated_at": generated_at,
                    "base_period": base_period,
                    "target_period": period,
                    "horizon": horizon,
                    "scenario": scenario,
                    "metric": metric_name,
                    "base_value": base_values.get(metric_name),
                    "forecast_value": value,
                    "historical_cagr_pct": growth_rates.get({
                        "book_value": "equity", "operating_cash_flow": "revenue",
                        "free_cash_flow": "fcf", "ebit": "ebitda",
                    }.get(metric_name, metric_name)),
                    "scenario_multiplier": SCENARIO_GROWTH_MULT.get(scenario),
                    "margin_assumption_pp": SCENARIO_MARGIN_DELTA_PP.get(scenario),
                    "probability_pct": probabilities.get(scenario),
                    "forecast_confidence": quality.get("forecast_confidence"),
                    "confidence_score": quality.get("score"),
                    "model_version": pack.get("version"),
                    "status": "OPEN",
                })
    return rows


def _period(row: dict[str, Any]) -> str:
    return str(row.get("fiscal_year") or row.get("period") or "").strip().upper().replace(" ", "")


def _band(ape: float) -> str:
    if ape <= 5:
        return "EXCELLENT"
    if ape <= 10:
        return "GOOD"
    if ape <= 20:
        return "FAIR"
    return "MISS"


def _calibration(confidence: Any, ape: float) -> str:
    level = str(confidence or "").upper()
    if level == "HIGH" and ape > 20:
        return "OVERCONFIDENT"
    if level == "LOW" and ape <= 10:
        return "UNDERCONFIDENT"
    return "ALIGNED"


def evaluate_predictions(
    predictions: Iterable[dict[str, Any]],
    actuals: Iterable[dict[str, Any]],
    *,
    evaluated_at: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Evaluate only exact future periods; unavailable actuals remain untouched."""
    actual_by_period = {_period(row): row for row in actuals if _period(row)}
    stamp = evaluated_at or _now()
    out: list[dict[str, Any]] = []
    for pred in predictions:
        actual_row = actual_by_period.get(str(pred.get("target_period") or "").upper().replace(" ", ""))
        aliases = _ALIASES.get(str(pred.get("metric") or ""))
        if not actual_row or not aliases:
            continue
        forecast = metric(pred, "forecast_value")
        actual = metric(actual_row, *aliases)
        if forecast is None or actual is None:
            continue
        error = actual - forecast
        denominator = abs(forecast)
        error_pct = (100.0 * error / denominator) if denominator else None
        ape = abs(error_pct) if error_pct is not None else None
        base = metric(pred, "base_value")
        direction = None
        if base is not None:
            direction = (forecast - base >= 0) == (actual - base >= 0)
        out.append({
            "symbol": pred.get("symbol"),
            "forecast_as_of": pred.get("forecast_as_of"),
            "generated_at": pred.get("generated_at"),
            "actual_period": pred.get("target_period"),
            "horizon": pred.get("horizon"),
            "scenario": pred.get("scenario"),
            "metric": pred.get("metric"),
            "base_value": base,
            "forecast_value": forecast,
            "actual_value": actual,
            "absolute_error": round(abs(error), 4),
            "error_pct": round(error_pct, 4) if error_pct is not None else None,
            "ape_pct": round(ape, 4) if ape is not None else None,
            "direction_correct": direction,
            "accuracy_band": _band(ape) if ape is not None else "UNSCORABLE",
            "forecast_confidence": pred.get("forecast_confidence"),
            "confidence_score": pred.get("confidence_score"),
            "calibration_status": _calibration(pred.get("forecast_confidence"), ape) if ape is not None else None,
            "model_version": pred.get("model_version"),
            "actual_source": "warehouse.financials_annual",
            "evaluated_at": stamp,
            "attribution": {"status": "pending", "drivers": []},
            "status": "EVALUATED",
        })
    return out


def evaluate_symbol(symbol: str) -> dict[str, Any]:
    from institutional_warehouse import gateway, store

    ticker = str(symbol or "").strip().upper()
    predictions = store.all_rows("forecast_metric_predictions", entity=ticker, limit=10000)
    actuals = store.all_rows("financials_annual", entity=ticker, limit=100)
    existing = store.all_rows("forecast_accuracy", entity=ticker, limit=10000)
    keys = {
        (r.get("generated_at"), r.get("actual_period"), r.get("horizon"), r.get("scenario"), r.get("metric"))
        for r in existing
    }
    due = [
        row for row in evaluate_predictions(predictions, actuals)
        if (row.get("generated_at"), row.get("actual_period"), row.get("horizon"), row.get("scenario"), row.get("metric")) not in keys
    ]
    result = gateway.write(
        "forecast_accuracy", due, source=ENGINE_CODE, actor="fie_accuracy",
        reason="point_in_time_forecast_evaluation", detect_conflicts=False,
    ) if due else {"ok": True, "written": 0}
    return {"ok": bool(result.get("ok", True)), "symbol": ticker, "eligible": len(due), "written": int(result.get("written") or 0)}
