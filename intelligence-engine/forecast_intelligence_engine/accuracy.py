"""Immutable forecast vintages and point-in-time outcome evaluation."""

from __future__ import annotations

import re
import statistics
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
VALID_OUTCOME = "VALID"


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def calibration_summary(
    accuracy_rows: Iterable[dict[str, Any]],
    evaluation_rows_: Iterable[dict[str, Any]],
    *,
    prediction_count: Optional[int] = None,
    consensus_vintage_count: int = 0,
    consensus_symbol_count: int = 0,
    consensus_matched_predictions: int = 0,
    consensus_match_coverage_pct: float = 0.0,
    minimum_outcomes: int = 100,
    minimum_sector_outcomes: int = 20,
    minimum_consensus_vintages: int = 100,
    minimum_consensus_symbols: int = 20,
) -> dict[str, Any]:
    """Aggregate only governed outcomes; never infer accuracy from open forecasts."""
    accuracy = [row for row in accuracy_rows if row.get("ape_pct") is not None]
    evaluations = list(evaluation_rows_)
    outcome_status_counts: dict[str, int] = {}
    review_required = 0
    for row in evaluations:
        status = str(row.get("outcome_status") or "UNKNOWN").upper()
        outcome_status_counts[status] = outcome_status_counts.get(status, 0) + 1
        review_required += int(bool(row.get("requires_review")))
    apes = sorted(float(row["ape_pct"]) for row in accuracy)
    directions = [bool(row["direction_correct"]) for row in accuracy if row.get("direction_correct") is not None]
    aligned = [row for row in accuracy if row.get("calibration_status") == "ALIGNED"]
    valid_evaluations = [row for row in evaluations if row.get("outcome_status") == VALID_OUTCOME]
    sector_counts: dict[str, int] = {}
    for row in valid_evaluations:
        sector = str(row.get("sector") or "Unclassified")
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
    median = statistics.median(apes) if apes else None
    gates = {
        "minimum_outcomes": len(accuracy) >= minimum_outcomes,
        "median_ape_at_most_20_pct": median is not None and median <= 20.0,
        "directional_accuracy_at_least_50_pct": bool(directions) and sum(directions) / len(directions) >= 0.50,
        "confidence_alignment_at_least_60_pct": bool(accuracy) and len(aligned) / len(accuracy) >= 0.60,
        "sector_models_supported": bool(sector_counts) and all(count >= minimum_sector_outcomes for count in sector_counts.values()),
        "consensus_vintages_available": (
            consensus_vintage_count >= minimum_consensus_vintages
            and consensus_symbol_count >= minimum_consensus_symbols
            and consensus_matched_predictions >= minimum_consensus_symbols
            and consensus_match_coverage_pct >= 50.0
        ),
    }
    empirically_ready = all(gates.values())
    return {
        "status": "RESEARCH_CALIBRATED" if empirically_ready else "ACCUMULATING_OUTCOMES",
        "execution_eligible": False,
        "valid_accuracy_outcomes": len(accuracy),
        "governed_valid_evaluations": len(valid_evaluations),
        "total_evaluations": len(evaluations),
        "forecast_predictions": int(prediction_count if prediction_count is not None else len(evaluations)),
        "outcome_status_counts": dict(sorted(outcome_status_counts.items())),
        "review_required": review_required,
        "mean_ape_pct": round(sum(apes) / len(apes), 3) if apes else None,
        "median_ape_pct": round(median, 3) if median is not None else None,
        "directional_accuracy_pct": round(sum(directions) / len(directions) * 100, 2) if directions else None,
        "confidence_alignment_pct": round(len(aligned) / len(accuracy) * 100, 2) if accuracy else None,
        "sector_outcome_counts": dict(sorted(sector_counts.items())),
        "consensus_vintages": int(consensus_vintage_count),
        "consensus_symbols": int(consensus_symbol_count),
        "consensus_matched_predictions": int(consensus_matched_predictions),
        "consensus_match_coverage_pct": round(float(consensus_match_coverage_pct), 2),
        "consensus_minimums": {
            "vintages": int(minimum_consensus_vintages),
            "symbols": int(minimum_consensus_symbols),
        },
        "gates": gates,
        "missing_dependencies": [name for name, passed in gates.items() if not passed],
        "outcome_diagnostic": (
            "NO_PREDICTIONS" if prediction_count == 0
            else "NOT_YET_EVALUATED" if prediction_count and not evaluations
            else "NO_MATURED_VALID_OUTCOMES" if not accuracy
            else "OUTCOMES_ACCUMULATING"
        ),
        "rule": "Forecast calibration may inform research confidence only; it cannot authorize strategy or portfolio execution.",
    }


def consensus_comparison_summary(
    predictions: Iterable[dict[str, Any]], consensus_vintages: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Match base forecasts to the latest consensus vintage known on the forecast date."""
    index: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in consensus_vintages:
        key = (
            str(row.get("symbol") or "").upper(),
            str(row.get("target_period") or "").upper(),
            str(row.get("metric") or "").lower(),
        )
        if all(key):
            index.setdefault(key, []).append(row)
    for rows in index.values():
        rows.sort(key=lambda row: str(row.get("consensus_date") or ""))
    eligible = [row for row in predictions if str(row.get("scenario") or "").lower() == "base"]
    matched = 0
    absolute_spreads: list[float] = []
    for prediction in eligible:
        key = (
            str(prediction.get("symbol") or "").upper(),
            str(prediction.get("target_period") or "").upper(),
            str(prediction.get("metric") or "").lower(),
        )
        cutoff = str(prediction.get("forecast_as_of") or prediction.get("generated_at") or "")[:10]
        candidates = [row for row in index.get(key, []) if str(row.get("consensus_date") or "")[:10] <= cutoff]
        if not candidates:
            continue
        estimate = _number(candidates[-1].get("mean_estimate"))
        forecast = _number(prediction.get("forecast_value"))
        if estimate is None or forecast is None:
            continue
        matched += 1
        if abs(estimate) > 1e-12:
            absolute_spreads.append(abs(100.0 * (forecast - estimate) / estimate))
    coverage = 100.0 * matched / len(eligible) if eligible else 0.0
    return {
        "eligible_base_predictions": len(eligible),
        "matched_predictions": matched,
        "match_coverage_pct": round(coverage, 2),
        "mean_absolute_forecast_consensus_spread_pct": (
            round(sum(absolute_spreads) / len(absolute_spreads), 3) if absolute_spreads else None
        ),
        "point_in_time_match_rule": "latest consensus_date <= forecast_as_of for identical symbol/target_period/metric",
    }


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


def evaluation_rows(
    predictions: Iterable[dict[str, Any]],
    actuals: Iterable[dict[str, Any]],
    *,
    sector: Optional[str] = None,
    regime: Optional[str] = None,
    evaluated_at: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Register every prediction outcome, including non-scoreable operational states."""
    actual_list = list(actuals)
    actual_by_period = {_period(row): row for row in actual_list if _period(row)}
    known_periods = sorted(actual_by_period)
    stamp = evaluated_at or _now()
    out: list[dict[str, Any]] = []
    for pred in predictions:
        target = str(pred.get("target_period") or "").upper().replace(" ", "")
        aliases = _ALIASES.get(str(pred.get("metric") or ""))
        actual_row = actual_by_period.get(target)
        actual_value = metric(actual_row or {}, *(aliases or ())) if aliases else None
        status = VALID_OUTCOME
        reason = "exact_period_and_metric_match"
        requires_review = False
        if not target:
            status, reason = "PERIOD_MISMATCH", "forecast_target_period_missing"
            requires_review = True
        elif actual_row is None:
            # A later period on file means the target was skipped or labelled
            # differently; otherwise the actual simply has not arrived yet.
            status = "PERIOD_MISMATCH" if known_periods and target < max(known_periods) else "MISSING_ACTUAL"
            reason = "target_period_not_found" if status == "PERIOD_MISMATCH" else "actual_not_reported_yet"
            requires_review = status == "PERIOD_MISMATCH"
        elif actual_value is None:
            status, reason = "MISSING_ACTUAL", "metric_missing_in_actual_statement"
        elif bool(actual_row.get("restated") or actual_row.get("is_restated")):
            status, reason = "DATA_REVISION", "actual_statement_marked_restated"
            requires_review = True
        elif str(actual_row.get("accounting_change") or "").strip():
            status, reason = "ACCOUNTING_CHANGE", str(actual_row.get("accounting_change"))[:260]
            requires_review = True
        out.append({
            "symbol": pred.get("symbol"),
            "generated_at": pred.get("generated_at"),
            "forecast_as_of": pred.get("forecast_as_of"),
            "target_period": pred.get("target_period"),
            "actual_period": _period(actual_row or {}) or None,
            "horizon": pred.get("horizon"),
            "scenario": pred.get("scenario"),
            "metric": pred.get("metric"),
            "forecast_value": pred.get("forecast_value"),
            "actual_value": actual_value,
            "outcome_status": status,
            "validation_reason": reason,
            "requires_review": requires_review,
            "sector": sector,
            "regime": regime,
            "forecast_confidence": pred.get("forecast_confidence"),
            "model_version": pred.get("model_version"),
            "actual_source": "warehouse.financials_annual" if actual_row else None,
            "evaluated_at": stamp,
        })
    return out


def evaluate_symbol(symbol: str) -> dict[str, Any]:
    from institutional_warehouse import gateway, store

    ticker = str(symbol or "").strip().upper()
    predictions = store.all_rows("forecast_metric_predictions", entity=ticker, limit=10000)
    actuals = store.all_rows("financials_annual", entity=ticker, limit=100)
    masters = store.all_rows("company_master", entity=ticker, limit=1)
    master = masters[0] if masters else {}
    evaluations = store.all_rows("forecast_evaluations", entity=ticker, limit=10000)
    evaluation_keys = {
        (r.get("generated_at"), r.get("target_period"), r.get("horizon"), r.get("scenario"), r.get("metric"), r.get("outcome_status"))
        for r in evaluations
    }
    evaluation_due = [
        row for row in evaluation_rows(predictions, actuals, sector=master.get("sector"))
        if (row.get("generated_at"), row.get("target_period"), row.get("horizon"), row.get("scenario"), row.get("metric"), row.get("outcome_status")) not in evaluation_keys
    ]
    evaluation_result = gateway.write(
        "forecast_evaluations", evaluation_due, source=ENGINE_CODE, actor="fie_accuracy",
        reason="forecast_outcome_governance", detect_conflicts=False,
    ) if evaluation_due else {"ok": True, "written": 0}
    existing = store.all_rows("forecast_accuracy", entity=ticker, limit=10000)
    keys = {
        (r.get("generated_at"), r.get("actual_period"), r.get("horizon"), r.get("scenario"), r.get("metric"))
        for r in existing
    }
    valid_keys = {
        (r.get("generated_at"), r.get("target_period"), r.get("horizon"), r.get("scenario"), r.get("metric"))
        for r in [*evaluations, *evaluation_due] if r.get("outcome_status") == VALID_OUTCOME
    }
    due = [
        row for row in evaluate_predictions(predictions, actuals)
        if (row.get("generated_at"), row.get("actual_period"), row.get("horizon"), row.get("scenario"), row.get("metric")) in valid_keys
        if (row.get("generated_at"), row.get("actual_period"), row.get("horizon"), row.get("scenario"), row.get("metric")) not in keys
    ]
    result = gateway.write(
        "forecast_accuracy", due, source=ENGINE_CODE, actor="fie_accuracy",
        reason="point_in_time_forecast_evaluation", detect_conflicts=False,
    ) if due else {"ok": True, "written": 0}
    return {
        "ok": bool(result.get("ok", True)) and bool(evaluation_result.get("ok", True)),
        "symbol": ticker,
        "evaluations_written": int(evaluation_result.get("written") or 0),
        "eligible": len(due),
        "written": int(result.get("written") or 0),
    }
