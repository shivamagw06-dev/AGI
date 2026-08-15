"""Versioned allow-list for deterministic AFE calculations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable


@dataclass(frozen=True)
class CalculationSpec:
    calculation_id: str
    name: str
    category: str
    formula: str
    required_inputs: tuple[str, ...]
    output_unit: str
    function: Callable[[dict[str, float]], float]
    version: str = "1.0.0"
    methodology: str = "AGI deterministic methodology"
    allow_mixed_units: bool = False
    allow_mixed_periods: bool = False

    def public(self) -> dict:
        row = asdict(self)
        row.pop("function", None)
        return row


def _div(a: float, b: float) -> float:
    if b == 0:
        raise ZeroDivisionError
    return a / b


def _growth(i: dict[str, float], begin: str, end: str) -> float:
    return (_div(i[end], i[begin]) - 1.0) * 100.0


def _avg(i: dict[str, float], opening: str, closing: str) -> float:
    return (i[opening] + i[closing]) / 2.0


SPECS = (
    CalculationSpec("PERCENT_CHANGE", "Percentage Change", "basic", "(end / beginning - 1) * 100", ("beginning", "end"), "percent", lambda i: _growth(i, "beginning", "end")),
    CalculationSpec("CAGR", "Compound Annual Growth Rate", "returns", "(end / beginning)^(1 / years) - 1", ("beginning", "end", "years"), "percent", lambda i: ((_div(i["end"], i["beginning"]) ** (1.0 / i["years"])) - 1.0) * 100.0),
    CalculationSpec("PRESENT_VALUE", "Present Value", "time_value", "future_value / (1 + rate)^periods", ("future_value", "rate", "periods"), "currency", lambda i: _div(i["future_value"], (1.0 + i["rate"]) ** i["periods"])),
    CalculationSpec("FUTURE_VALUE", "Future Value", "time_value", "present_value * (1 + rate)^periods", ("present_value", "rate", "periods"), "currency", lambda i: i["present_value"] * (1.0 + i["rate"]) ** i["periods"]),
    CalculationSpec("ROE", "Return on Equity", "profitability", "PAT / average equity * 100", ("pat", "opening_equity", "closing_equity"), "percent", lambda i: _div(i["pat"], _avg(i, "opening_equity", "closing_equity")) * 100.0, methodology="PAT divided by average opening and closing equity"),
    CalculationSpec("ROA", "Return on Assets", "profitability", "PAT / average assets * 100", ("pat", "opening_assets", "closing_assets"), "percent", lambda i: _div(i["pat"], _avg(i, "opening_assets", "closing_assets")) * 100.0),
    CalculationSpec("LOAN_GROWTH", "Loan Growth", "banking", "(closing loans / opening loans - 1) * 100", ("opening_loans", "closing_loans"), "percent", lambda i: _growth(i, "opening_loans", "closing_loans")),
    CalculationSpec("DEPOSIT_GROWTH", "Deposit Growth", "banking", "(closing deposits / opening deposits - 1) * 100", ("opening_deposits", "closing_deposits"), "percent", lambda i: _growth(i, "opening_deposits", "closing_deposits")),
    CalculationSpec("CASA_RATIO", "CASA Ratio", "banking", "CASA deposits / total deposits * 100", ("casa_deposits", "total_deposits"), "percent", lambda i: _div(i["casa_deposits"], i["total_deposits"]) * 100.0),
    CalculationSpec("CREDIT_DEPOSIT_RATIO", "Credit-Deposit Ratio", "banking", "gross loans / deposits * 100", ("gross_loans", "deposits"), "percent", lambda i: _div(i["gross_loans"], i["deposits"]) * 100.0),
    CalculationSpec("GNPA_RATIO", "Gross NPA Ratio", "banking", "gross NPA / gross advances * 100", ("gross_npa", "gross_advances"), "percent", lambda i: _div(i["gross_npa"], i["gross_advances"]) * 100.0),
    CalculationSpec("NNPA_RATIO", "Net NPA Ratio", "banking", "net NPA / net advances * 100", ("net_npa", "net_advances"), "percent", lambda i: _div(i["net_npa"], i["net_advances"]) * 100.0),
    CalculationSpec("PCR", "Provision Coverage Ratio", "banking", "accumulated provisions / relevant NPA base * 100", ("accumulated_provisions", "npa_base"), "percent", lambda i: _div(i["accumulated_provisions"], i["npa_base"]) * 100.0),
    CalculationSpec("NIM", "Net Interest Margin", "banking", "net interest income / average interest-earning assets * 100", ("net_interest_income", "opening_interest_earning_assets", "closing_interest_earning_assets"), "percent", lambda i: _div(i["net_interest_income"], _avg(i, "opening_interest_earning_assets", "closing_interest_earning_assets")) * 100.0),
    CalculationSpec("CREDIT_COST", "Credit Cost", "banking", "provisions / average loans * 100", ("provisions", "opening_loans", "closing_loans"), "percent", lambda i: _div(i["provisions"], _avg(i, "opening_loans", "closing_loans")) * 100.0),
    CalculationSpec("CET1_RATIO", "CET1 Ratio", "banking", "CET1 capital / risk-weighted assets * 100", ("cet1_capital", "risk_weighted_assets"), "percent", lambda i: _div(i["cet1_capital"], i["risk_weighted_assets"]) * 100.0),
    CalculationSpec("CRAR", "Capital Adequacy Ratio", "banking", "eligible regulatory capital / risk-weighted assets * 100", ("regulatory_capital", "risk_weighted_assets"), "percent", lambda i: _div(i["regulatory_capital"], i["risk_weighted_assets"]) * 100.0),
    CalculationSpec("COST_TO_INCOME", "Cost-to-Income Ratio", "banking", "operating expenses / operating income * 100", ("operating_expenses", "operating_income"), "percent", lambda i: _div(i["operating_expenses"], i["operating_income"]) * 100.0),
    CalculationSpec("PRICE_TO_BOOK", "Price to Book", "valuation", "market price per share / book value per share", ("market_price", "book_value_per_share"), "multiple", lambda i: _div(i["market_price"], i["book_value_per_share"])),
    CalculationSpec("PRICE_TO_EARNINGS", "Price to Earnings", "valuation", "market price per share / normalized earnings per share", ("market_price", "normalized_eps"), "multiple", lambda i: _div(i["market_price"], i["normalized_eps"])),
    CalculationSpec("BANK_PRICE_TO_BOOK", "Bank Price to Book", "bank_valuation", "point-in-time market price per share / latest available book value per share", ("market_price", "book_value_per_share"), "multiple", lambda i: _div(i["market_price"], i["book_value_per_share"]), allow_mixed_units=True, allow_mixed_periods=True),
    CalculationSpec("BANK_PRICE_TO_EARNINGS", "Bank Price to Earnings", "bank_valuation", "point-in-time market price per share / latest available normalized earnings per share", ("market_price", "normalized_eps"), "multiple", lambda i: _div(i["market_price"], i["normalized_eps"]), allow_mixed_units=True, allow_mixed_periods=True),
    CalculationSpec("JUSTIFIED_PB", "Justified Price to Book", "bank_valuation", "(ROE - growth) / (cost of equity - growth)", ("roe", "growth", "cost_of_equity"), "multiple", lambda i: _div(i["roe"] - i["growth"], i["cost_of_equity"] - i["growth"])),
    CalculationSpec("PRICE_TO_TANGIBLE_BOOK", "Price to Tangible Book", "bank_valuation", "market price / tangible book value per share", ("market_price", "tangible_book_value_per_share"), "multiple", lambda i: _div(i["market_price"], i["tangible_book_value_per_share"])),
    CalculationSpec("BANK_RESIDUAL_INCOME", "Bank Residual Income Value", "bank_valuation", "book value + book value * (ROE - cost of equity) / (cost of equity - growth)", ("book_value", "roe", "cost_of_equity", "growth"), "currency", lambda i: i["book_value"] + _div(i["book_value"] * (i["roe"] - i["cost_of_equity"]), i["cost_of_equity"] - i["growth"]), allow_mixed_units=True),
    CalculationSpec("BANK_DDM", "Bank Gordon Growth DDM", "bank_valuation", "next dividend / (cost of equity - growth)", ("next_dividend", "cost_of_equity", "growth"), "currency", lambda i: _div(i["next_dividend"], i["cost_of_equity"] - i["growth"]), allow_mixed_units=True),
    CalculationSpec("BANK_IMPLIED_ROE", "Market-Implied Bank ROE", "bank_reverse_valuation", "P/B * (cost of equity - growth) + growth", ("price_to_book", "cost_of_equity", "growth"), "decimal", lambda i: i["price_to_book"] * (i["cost_of_equity"] - i["growth"]) + i["growth"], allow_mixed_units=True, allow_mixed_periods=True),
    CalculationSpec("BANK_IMPLIED_GROWTH", "Market-Implied Bank Growth", "bank_reverse_valuation", "(ROE - P/B * cost of equity) / (1 - P/B)", ("roe", "price_to_book", "cost_of_equity"), "decimal", lambda i: _div(i["roe"] - i["price_to_book"] * i["cost_of_equity"], 1.0 - i["price_to_book"]), allow_mixed_units=True, allow_mixed_periods=True),
    CalculationSpec("MARGIN_OF_SAFETY", "Margin of Safety", "valuation", "(intrinsic value - market price) / intrinsic value * 100", ("intrinsic_value", "market_price"), "percent", lambda i: _div(i["intrinsic_value"] - i["market_price"], i["intrinsic_value"]) * 100.0),
    CalculationSpec("TELECOM_REVENUE_IMPACT", "Telecom ARPU Revenue Impact", "telecom", "ARPU * tariff change * subscribers * realization", ("arpu", "tariff_change", "subscribers", "realization"), "currency", lambda i: i["arpu"] * i["tariff_change"] * i["subscribers"] * i["realization"], methodology="Scenario output; tariff_change and realization are decimal assumptions"),
)

REGISTRY = {spec.calculation_id: spec for spec in SPECS}


def get_spec(calculation_id: str) -> CalculationSpec | None:
    return REGISTRY.get(str(calculation_id or "").strip().upper())


def list_specs() -> list[dict]:
    return [spec.public() for spec in sorted(SPECS, key=lambda row: row.calculation_id)]
