"""Fail-closed, unit/period/PIT-aware AFE executor."""

from __future__ import annotations

from datetime import datetime, timezone
import math
import time
from typing import Any

from financial_engine.registry import get_spec, list_specs


def list_calculations() -> list[dict]:
    return list_specs()


def _failure(code: str, calculation_id: str, detail: str, started: float) -> dict[str, Any]:
    return {
        "status": code,
        "calculation_id": str(calculation_id or "").upper(),
        "validation": {"status": "INVALID", "detail": detail},
        "warnings": [],
        "execution_time_ms": round((time.perf_counter() - started) * 1000, 3),
        "deterministic": True,
    }


def _normalise_inputs(inputs: dict[str, Any], required: tuple[str, ...], as_of: str | None, *, allow_mixed_units: bool = False, allow_mixed_periods: bool = False) -> tuple[dict[str, float], dict[str, Any]]:
    values: dict[str, float] = {}
    metadata: dict[str, Any] = {}
    units: set[str] = set()
    currencies: set[str] = set()
    periods: set[str] = set()
    source_ids: set[str] = set()
    for key in required:
        if key not in inputs:
            raise ValueError(f"INSUFFICIENT_DATA:{key}")
        item = inputs[key]
        if isinstance(item, bool):
            raise ValueError(f"INVALID_INPUT:{key}")
        if isinstance(item, (int, float)):
            value = float(item)
            meta = {}
        elif isinstance(item, dict) and isinstance(item.get("value", item.get("normalized_value")), (int, float)):
            value = float(item.get("value", item.get("normalized_value")))
            meta = dict(item)
        else:
            raise ValueError(f"INVALID_INPUT:{key}")
        values[key] = value
        if not math.isfinite(value):
            raise ValueError(f"INVALID_INPUT:{key} must be finite")
        metadata[key] = meta
        if meta.get("unit"): units.add(str(meta["unit"]).lower())
        if meta.get("currency"): currencies.add(str(meta["currency"]).upper())
        if meta.get("period"): periods.add(str(meta["period"]))
        if meta.get("source_id"): source_ids.add(str(meta["source_id"]))
        available_at = meta.get("available_at")
        if as_of and available_at and str(available_at) > str(as_of):
            raise ValueError(f"POINT_IN_TIME_VIOLATION:{key}")
    if len(units) > 1 and not allow_mixed_units:
        raise ValueError("UNIT_MISMATCH:inputs")
    if len(currencies) > 1:
        raise ValueError("CURRENCY_MISMATCH:inputs")
    if len(periods) > 1 and not allow_mixed_periods:
        raise ValueError("PERIOD_MISMATCH:inputs")
    return values, {
        "units": sorted(units), "currencies": sorted(currencies),
        "periods": sorted(periods), "source_ids": sorted(source_ids), "metadata": metadata,
    }


def calculate(*, calculation_id: str | None = None, operation: str | None = None, inputs: dict[str, Any], as_of: str | None = None, assumptions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    calc_id = str(calculation_id or operation or "").strip().upper()
    spec = get_spec(calc_id)
    if spec is None:
        return _failure("UNSUPPORTED_CALCULATION", calc_id, "calculation is not registered", started)
    if not isinstance(inputs, dict):
        return _failure("INVALID_INPUT", calc_id, "inputs must be an object", started)
    try:
        values, provenance = _normalise_inputs(inputs, spec.required_inputs, as_of,
            allow_mixed_units=spec.allow_mixed_units, allow_mixed_periods=spec.allow_mixed_periods)
        if calc_id in {"CAGR"} and values.get("years", 0) <= 0:
            return _failure("INVALID_INPUT", calc_id, "years must be positive", started)
        if calc_id == "CAGR" and (values["beginning"] <= 0 or values["end"] < 0):
            return _failure("INVALID_INPUT", calc_id, "CAGR requires a positive beginning and non-negative ending value", started)
        if calc_id in {"JUSTIFIED_PB", "BANK_RESIDUAL_INCOME", "BANK_DDM"} and values["cost_of_equity"] <= values["growth"]:
            return _failure("INVALID_TERMINAL_GROWTH", calc_id, "cost of equity must exceed growth", started)
        if calc_id == "GORDON_DCF" and values["discount_rate"] <= values["terminal_growth"]:
            return _failure("INVALID_TERMINAL_GROWTH", calc_id, "discount rate must exceed terminal growth", started)
        if calc_id == "BANK_IMPLIED_GROWTH" and values["price_to_book"] == 1.0:
            return _failure("DIVISION_BY_ZERO", calc_id, "P/B cannot equal 1 for this algebraic reverse-growth form", started)
        if calc_id == "IMPLIED_GROWTH_FROM_MULTIPLE" and (values["terminal_multiple"] <= 0 or values["horizon_years"] <= 0):
            return _failure("INVALID_INPUT", calc_id, "terminal multiple and horizon years must be positive", started)
        if calc_id == "UTILIZATION_REVENUE_CAPACITY" and (
            not 0 <= values["utilization"] <= 1 or values["opening_headcount"] <= 0
            or values["closing_headcount"] <= 0 or values["billing_rate"] <= 0
            or values["billable_periods"] <= 0
        ):
            return _failure("INVALID_INPUT", calc_id, "utilization must be 0-1 and capacity inputs must be positive", started)
        if calc_id == "IT_SERVICES_SCENARIO_PRICE" and (
            values["revenue"] <= 0 or values["revenue_growth"] <= -1
            or not 0 <= values["ebit_margin"] <= 1 or not 0 <= values["tax_rate"] <= 1
            or values["shares_outstanding"] <= 0 or values["target_pe"] <= 0
        ):
            return _failure("INVALID_INPUT", calc_id, "scenario economics are outside valid bounds", started)
        if calc_id in {"ARR_GROWTH", "NET_REVENUE_RETENTION", "GROSS_REVENUE_RETENTION"} and values["opening_arr"] <= 0:
            return _failure("INVALID_INPUT", calc_id, "opening ARR must be positive", started)
        if calc_id in {"NET_REVENUE_RETENTION", "GROSS_REVENUE_RETENTION"} and any(values[key] < 0 for key in values if key != "opening_arr"):
            return _failure("INVALID_INPUT", calc_id, "retention bridge components cannot be negative", started)
        if calc_id == "CAC_PAYBACK_MONTHS" and (values["customer_acquisition_cost"] < 0 or values["monthly_revenue_per_new_customer"] <= 0 or not 0 < values["gross_margin"] <= 1):
            return _failure("INVALID_INPUT", calc_id, "CAC must be non-negative, revenue positive and gross margin 0-1", started)
        if calc_id == "CUSTOMER_LTV" and (values["annual_revenue_per_customer"] <= 0 or not 0 < values["gross_margin"] <= 1 or not 0 < values["annual_logo_churn"] <= 1):
            return _failure("INVALID_INPUT", calc_id, "LTV inputs are outside valid bounds", started)
        if calc_id == "SAAS_SCENARIO_EV" and (values["arr"] <= 0 or values["arr_growth"] <= -1 or values["target_ev_arr"] <= 0):
            return _failure("INVALID_INPUT", calc_id, "SaaS scenario inputs are outside valid bounds", started)
        value = spec.function(values)
    except ZeroDivisionError:
        return _failure("DIVISION_BY_ZERO", calc_id, "formula denominator is zero", started)
    except ValueError as exc:
        code, _, detail = str(exc).partition(":")
        return _failure(code or "INVALID_INPUT", calc_id, detail or str(exc), started)
    raw_value = float(value)
    precision = 2 if spec.output_unit in {"percent", "multiple"} else 4
    return {
        "status": "SUCCESS",
        "calculation_id": spec.calculation_id,
        "calculation_version": spec.version,
        "name": spec.name,
        "category": spec.category,
        "raw_value": raw_value,
        "calculated_value": raw_value,
        "display_value": round(raw_value, precision),
        "unit": spec.output_unit,
        "currency": provenance["currencies"][0] if len(provenance["currencies"]) == 1 else None,
        "period": provenance["periods"][0] if len(provenance["periods"]) == 1 else None,
        "formula": spec.formula,
        "inputs": values,
        "input_provenance": provenance["metadata"],
        "source_ids": provenance["source_ids"],
        "assumptions": assumptions or [],
        "as_of": as_of,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "validation": {"status": "VALID"},
        "warnings": ["SCENARIO_NOT_FACT"] if calc_id in {"TELECOM_REVENUE_IMPACT", "IT_SERVICES_SCENARIO_PRICE", "UTILIZATION_REVENUE_CAPACITY", "SAAS_SCENARIO_EV"} else [],
        "execution_time_ms": round((time.perf_counter() - started) * 1000, 3),
        "deterministic": True,
        "model_generated_formula": False,
    }
