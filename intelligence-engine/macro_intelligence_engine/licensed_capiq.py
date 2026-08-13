"""Controlled internal import of the checked-in Capital IQ India macro workbook."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from macro_intelligence_engine.public_ingestion import _rest, _write_chunks

WORKBOOK = Path(__file__).resolve().parents[2] / "India_Macroeconomics Overview.xls"
SOURCE = "S&P Capital IQ"
VINTAGE = "2026-08-14"

HISTORICAL = {
    "GDP - Nominal": ("gdp_nominal", "USD"),
    "GDP per Capita - Nominal": ("gdp_per_capita_nominal", "USD"),
    "GDP - Real": ("gdp_real", "USD"),
    "GDP - Real (YOY% Growth)": ("gdp_real_growth", "%"),
    "GDP - Real (USD)": ("gdp_real_usd", "USD"),
    "Inflows (USD)": ("fdi_inflows", "USD"),
    "Outflows (USD)": ("fdi_outflows", "USD"),
    "Net (USD)": ("fdi_net", "USD"),
    "Balance of Payments (USD)": ("balance_of_payments", "USD"),
    "Current Account Balance (USD)": ("current_account_balance", "USD"),
    "Net Portfolio Investment (USD)": ("net_portfolio_investment", "USD"),
    "Foreign Currency Reserves (USD)": ("fx_reserves", "USD"),
    "Imports (USD)": ("imports", "USD"),
    "Exports (USD)": ("exports", "USD"),
    "Trade Balance (USD)": ("trade_balance", "USD"),
    "Current Account Balance (% of GDP)": ("current_account_gdp", "% GDP"),
    "CPI (YOY% Growth)": ("cpi_growth", "%"),
    "Unemployment Rate": ("unemployment", "%"),
    "Employment (YOY% Growth)": ("employment_growth", "%"),
    "Retail Sales (YOY% Growth)": ("retail_sales_growth", "%"),
    "Private Consumption Growth - Real": ("consumption_growth", "%"),
    "Fixed Investment - Real (% Growth)": ("fixed_investment_growth", "%"),
    "Fiscal Balance (% of GDP)": ("fiscal_balance_gdp", "% GDP"),
    "Industrial Production Index (% Growth)": ("industrial_production_growth", "%"),
    "Foreign Currency Reserves (% of GDP)": ("fx_reserves_gdp", "% GDP"),
    "Exchange Rate vs USD": ("usd_fx", "local currency per USD"),
    "Population": ("population", "persons"),
    "Stock Market Index": ("stock_market_index", "index"),
}

FORECASTS = {
    "GDP - Nominal": ("gdp_nominal", "local currency"),
    "GDP per Capita - Nominal (YOY% Growth)": ("gdp_per_capita_nominal_growth", "%"),
    "GDP - Real": ("gdp_real", "local currency"),
    "GDP - Real (YOY% Growth)": ("gdp_real_growth", "%"),
    "GDP - Real (USD)": ("gdp_real_usd", "USD"),
    "Foreign Currency Reserves (% of GDP)": ("fx_reserves_gdp", "% GDP"),
    "Population": ("population", "persons"),
    "CPI (YOY% Growth)": ("cpi_growth", "%"),
    "Exchange Rate vs USD": ("usd_fx", "local currency per USD"),
}


def _frame(sheet: str):
    import pandas as pd

    engine = "xlrd" if WORKBOOK.suffix.lower() == ".xls" else "openpyxl"
    return pd.read_excel(WORKBOOK, sheet_name=sheet, header=None, engine=engine)


def _number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if number == number else None
    except (TypeError, ValueError):
        return None


def parse_workbook() -> dict[str, Any]:
    if not WORKBOOK.exists():
        return {"ok": False, "error": "workbook_missing", "path": str(WORKBOOK)}
    digest = hashlib.sha256(WORKBOOK.read_bytes()).hexdigest()
    historical = _frame("Global Historical")
    forecasts = _frame("Global Forecast")
    observations: list[dict[str, Any]] = []
    forecast_rows: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []

    for row_index in range(9, min(len(historical), 48)):
        label = str(historical.iat[row_index, 0] or "").strip()
        mapped = HISTORICAL.get(label)
        if not mapped:
            continue
        series_id, unit = mapped
        for column in range(2, 15):
            raw = historical.iat[row_index, column]
            value = _number(raw)
            offset = 14 - column
            relative_period = f"quarter_minus_{offset}" if offset else "quarter"
            if value in (None, 0.0):
                quarantine.append({"source_file":WORKBOOK.name,"source_sheet":"Global Historical","row_label":label,"period_label":relative_period,"raw_value":None if value is None else str(value),"reason":"missing_or_ambiguous_zero","source_hash":digest})
                continue
            observations.append({"country_code":"IND","series_id":series_id,"label":label,"as_of_date":VINTAGE,"relative_period":relative_period,"value_numeric":value,"unit":unit,"frequency":"quarterly","source":SOURCE,"source_file":WORKBOOK.name,"source_sheet":"Global Historical","source_hash":digest,"licence_class":"LICENSED_INTERNAL_ONLY","pit_status":"FETCH_VINTAGE_ONLY","publish_allowed":False,"metadata":{"period_date_available":False,"usage":"internal_research_only"}})

    for row_index in range(9, min(len(forecasts), 23)):
        label = str(forecasts.iat[row_index, 0] or "").strip()
        mapped = FORECASTS.get(label)
        if not mapped:
            continue
        series_id, unit = mapped
        for horizon, column in enumerate(range(2, 15)):
            raw = forecasts.iat[row_index, column]
            value = _number(raw)
            if value in (None, 0.0):
                quarantine.append({"source_file":WORKBOOK.name,"source_sheet":"Global Forecast","row_label":label,"period_label":f"year_plus_{horizon}","raw_value":None if value is None else str(value),"reason":"missing_or_ambiguous_zero","source_hash":digest})
                continue
            forecast_rows.append({"country_code":"IND","series_id":series_id,"label":label,"vintage_date":VINTAGE,"target_year":2026+horizon,"horizon_years":horizon,"value_numeric":value,"unit":unit,"source":SOURCE,"source_file":WORKBOOK.name,"source_sheet":"Global Forecast","source_hash":digest,"licence_class":"LICENSED_INTERNAL_ONLY","pit_status":"FETCH_VINTAGE_ONLY","publish_allowed":False,"metadata":{"forecast_origin":"workbook_relative_year_header","usage":"internal_research_only"}})

    return {"ok": True,"source":SOURCE,"vintage":VINTAGE,"source_hash":digest,"observation_rows":observations,"forecast_rows":forecast_rows,"quarantine_rows":quarantine,"publish_allowed":False,"licence_class":"LICENSED_INTERNAL_ONLY"}


def import_workbook() -> dict[str, Any]:
    parsed = parse_workbook()
    if not parsed.get("ok"):
        return parsed
    observations = parsed.pop("observation_rows")
    forecast_rows = parsed.pop("forecast_rows")
    quarantine = parsed.pop("quarantine_rows")
    _write_chunks("macro_licensed_observations", observations, query="?on_conflict=country_code,series_id,as_of_date,relative_period,source")
    _write_chunks("macro_licensed_forecasts", forecast_rows, query="?on_conflict=country_code,series_id,vintage_date,target_year,source")
    _write_chunks("macro_licensed_quarantine", quarantine, query="?on_conflict=source_file,source_sheet,row_label,period_label,reason,source_hash")
    return {**parsed,"observations":len(observations),"forecasts":len(forecast_rows),"quarantined":len(quarantine)}
