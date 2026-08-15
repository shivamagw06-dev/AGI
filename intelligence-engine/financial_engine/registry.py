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
    CalculationSpec("FINANCIAL_PRICE_TO_BOOK", "Financial Institution Price to Book", "financials_valuation", "point-in-time market price per share / latest available book value per share", ("market_price", "book_value_per_share"), "multiple", lambda i: _div(i["market_price"], i["book_value_per_share"]), allow_mixed_units=True, allow_mixed_periods=True),
    CalculationSpec("FINANCIAL_PRICE_TO_EARNINGS", "Financial Institution Price to Earnings", "financials_valuation", "point-in-time market price per share / latest available normalized earnings per share", ("market_price", "normalized_eps"), "multiple", lambda i: _div(i["market_price"], i["normalized_eps"]), allow_mixed_units=True, allow_mixed_periods=True),
    CalculationSpec("JUSTIFIED_PB", "Justified Price to Book", "bank_valuation", "(ROE - growth) / (cost of equity - growth)", ("roe", "growth", "cost_of_equity"), "multiple", lambda i: _div(i["roe"] - i["growth"], i["cost_of_equity"] - i["growth"])),
    CalculationSpec("PRICE_TO_TANGIBLE_BOOK", "Price to Tangible Book", "bank_valuation", "market price / tangible book value per share", ("market_price", "tangible_book_value_per_share"), "multiple", lambda i: _div(i["market_price"], i["tangible_book_value_per_share"])),
    CalculationSpec("BANK_RESIDUAL_INCOME", "Bank Residual Income Value", "bank_valuation", "book value + book value * (ROE - cost of equity) / (cost of equity - growth)", ("book_value", "roe", "cost_of_equity", "growth"), "currency", lambda i: i["book_value"] + _div(i["book_value"] * (i["roe"] - i["cost_of_equity"]), i["cost_of_equity"] - i["growth"]), allow_mixed_units=True),
    CalculationSpec("BANK_DDM", "Bank Gordon Growth DDM", "bank_valuation", "next dividend / (cost of equity - growth)", ("next_dividend", "cost_of_equity", "growth"), "currency", lambda i: _div(i["next_dividend"], i["cost_of_equity"] - i["growth"]), allow_mixed_units=True),
    CalculationSpec("BANK_IMPLIED_ROE", "Market-Implied Bank ROE", "bank_reverse_valuation", "P/B * (cost of equity - growth) + growth", ("price_to_book", "cost_of_equity", "growth"), "decimal", lambda i: i["price_to_book"] * (i["cost_of_equity"] - i["growth"]) + i["growth"], allow_mixed_units=True, allow_mixed_periods=True),
    CalculationSpec("BANK_IMPLIED_GROWTH", "Market-Implied Bank Growth", "bank_reverse_valuation", "(ROE - P/B * cost of equity) / (1 - P/B)", ("roe", "price_to_book", "cost_of_equity"), "decimal", lambda i: _div(i["roe"] - i["price_to_book"] * i["cost_of_equity"], 1.0 - i["price_to_book"]), allow_mixed_units=True, allow_mixed_periods=True),
    CalculationSpec("PRICE_TO_EMBEDDED_VALUE", "Price to Embedded Value", "insurance_valuation", "market price / embedded value per share", ("market_price", "embedded_value_per_share"), "multiple", lambda i: _div(i["market_price"], i["embedded_value_per_share"]), allow_mixed_units=True, allow_mixed_periods=True),
    CalculationSpec("EV_EBITDA", "Enterprise Value to EBITDA", "operating_financial_valuation", "enterprise value / EBITDA", ("enterprise_value", "ebitda"), "multiple", lambda i: _div(i["enterprise_value"], i["ebitda"])),
    CalculationSpec("EV_SALES", "Enterprise Value to Sales", "fintech_valuation", "enterprise value / revenue", ("enterprise_value", "revenue"), "multiple", lambda i: _div(i["enterprise_value"], i["revenue"])),
    CalculationSpec("EV_GROSS_PROFIT", "Enterprise Value to Gross Profit", "fintech_valuation", "enterprise value / gross profit", ("enterprise_value", "gross_profit"), "multiple", lambda i: _div(i["enterprise_value"], i["gross_profit"])),
    CalculationSpec("GORDON_DCF", "Gordon Growth Equity Value", "cash_flow_valuation", "next period FCF / (discount rate - terminal growth)", ("next_fcf", "discount_rate", "terminal_growth"), "currency", lambda i: _div(i["next_fcf"], i["discount_rate"] - i["terminal_growth"]), allow_mixed_units=True),
    CalculationSpec("FCF_YIELD", "Free Cash Flow Yield", "valuation", "FCF per share / market price", ("fcf_per_share", "market_price"), "decimal", lambda i: _div(i["fcf_per_share"], i["market_price"]), allow_mixed_units=True, allow_mixed_periods=True),
    CalculationSpec("VNB_MARGIN", "Value of New Business Margin", "insurance", "VNB / APE", ("vnb", "ape"), "decimal", lambda i: _div(i["vnb"], i["ape"])),
    CalculationSpec("COMBINED_RATIO", "Combined Ratio", "insurance", "claims ratio + expense ratio", ("claims_ratio", "expense_ratio"), "decimal", lambda i: i["claims_ratio"] + i["expense_ratio"], allow_mixed_units=True),
    CalculationSpec("FEE_YIELD", "Asset Management Fee Yield", "asset_management", "revenue / average AUM", ("revenue", "average_aum"), "decimal", lambda i: _div(i["revenue"], i["average_aum"])),
    CalculationSpec("TAKE_RATE", "Payments Take Rate", "fintech", "revenue / TPV", ("revenue", "tpv"), "decimal", lambda i: _div(i["revenue"], i["tpv"])),
    CalculationSpec("CONTRIBUTION_MARGIN", "Contribution Margin", "fintech", "contribution profit / revenue", ("contribution_profit", "revenue"), "decimal", lambda i: _div(i["contribution_profit"], i["revenue"])),
    CalculationSpec("IMPLIED_GROWTH_FROM_PE", "Market-Implied Growth from P/E", "reverse_valuation", "cost of equity - payout ratio / P/E", ("cost_of_equity", "payout_ratio", "price_to_earnings"), "decimal", lambda i: i["cost_of_equity"] - _div(i["payout_ratio"], i["price_to_earnings"]), allow_mixed_units=True, allow_mixed_periods=True),
    CalculationSpec("IMPLIED_GROWTH_FROM_MULTIPLE", "Market-Implied Growth from Multiple", "reverse_valuation", "(current multiple / terminal multiple)^(1 / horizon years) - 1", ("current_multiple", "terminal_multiple", "horizon_years"), "decimal", lambda i: (_div(i["current_multiple"], i["terminal_multiple"]) ** _div(1.0, i["horizon_years"])) - 1.0, allow_mixed_units=True, allow_mixed_periods=True),
    CalculationSpec("IMPLIED_HOLDCO_DISCOUNT", "Market-Implied Holding Company Discount", "reverse_valuation", "1 - market capitalization / gross SOTP equity value", ("market_cap","segment_1_value","segment_2_value","segment_3_value","net_debt"), "decimal", lambda i: 1.0 - _div(i["market_cap"], i["segment_1_value"] + i["segment_2_value"] + i["segment_3_value"] - i["net_debt"]), allow_mixed_units=True, allow_mixed_periods=True),
    CalculationSpec("SOTP_3_SEGMENT", "Three-Segment Sum of the Parts", "diversified_valuation", "(segment 1 + segment 2 + segment 3 - net debt) * (1 - holdco discount)", ("segment_1_value", "segment_2_value", "segment_3_value", "net_debt", "holdco_discount"), "currency", lambda i: (i["segment_1_value"] + i["segment_2_value"] + i["segment_3_value"] - i["net_debt"]) * (1.0 - i["holdco_discount"]), allow_mixed_units=True),
    CalculationSpec("MARGIN_OF_SAFETY", "Margin of Safety", "valuation", "(intrinsic value - market price) / intrinsic value * 100", ("intrinsic_value", "market_price"), "percent", lambda i: _div(i["intrinsic_value"] - i["market_price"], i["intrinsic_value"]) * 100.0),
    CalculationSpec("TELECOM_REVENUE_IMPACT", "Telecom ARPU Revenue Impact", "telecom", "ARPU * tariff change * subscribers * realization", ("arpu", "tariff_change", "subscribers", "realization"), "currency", lambda i: i["arpu"] * i["tariff_change"] * i["subscribers"] * i["realization"], methodology="Scenario output; tariff_change and realization are decimal assumptions"),
    CalculationSpec("TELECOM_SUBSCRIBER_GROWTH", "Telecom Subscriber Growth", "telecom", "closing subscribers / opening subscribers - 1", ("opening_subscribers","closing_subscribers"), "decimal", lambda i: _div(i["closing_subscribers"],i["opening_subscribers"]) - 1.0),
    CalculationSpec("TELECOM_ANNUAL_SERVICE_REVENUE", "Telecom Annualized Service Revenue", "telecom", "average subscribers * monthly ARPU * 12", ("opening_subscribers","closing_subscribers","monthly_arpu"), "currency", lambda i: _avg(i,"opening_subscribers","closing_subscribers")*i["monthly_arpu"]*12.0, allow_mixed_units=True, methodology="Subscriber/ARPU bridge, not reported consolidated revenue"),
    CalculationSpec("TELECOM_EV_PER_SUBSCRIBER", "Telecom EV per Subscriber", "telecom_valuation", "enterprise value / subscribers", ("enterprise_value","subscribers"), "currency_per_subscriber", lambda i: _div(i["enterprise_value"],i["subscribers"]), allow_mixed_units=True),
    CalculationSpec("TELECOM_CAPEX_INTENSITY", "Telecom Capex Intensity", "telecom", "capex / revenue", ("capex","revenue"), "decimal", lambda i: _div(i["capex"],i["revenue"])),
    CalculationSpec("TELECOM_EBITDA_MARGIN", "Telecom EBITDA Margin", "telecom", "EBITDA / revenue", ("ebitda","revenue"), "decimal", lambda i: _div(i["ebitda"],i["revenue"])),
    CalculationSpec("TELECOM_NET_DEBT_EBITDA", "Telecom Net Debt to EBITDA", "telecom", "net debt plus spectrum liabilities / EBITDA", ("net_debt","spectrum_liabilities","ebitda"), "multiple", lambda i: _div(i["net_debt"]+i["spectrum_liabilities"],i["ebitda"]), allow_mixed_units=True),
    CalculationSpec("TELECOM_INTEREST_COVERAGE", "Telecom Interest Coverage", "telecom", "EBITDA / interest expense", ("ebitda","interest_expense"), "multiple", lambda i: _div(i["ebitda"],i["interest_expense"])),
    CalculationSpec("TELECOM_ENTERPRISE_MIX", "Telecom Enterprise Revenue Mix", "telecom", "enterprise revenue / total revenue", ("enterprise_revenue","revenue"), "decimal", lambda i: _div(i["enterprise_revenue"],i["revenue"])),
    CalculationSpec("TELECOM_SCENARIO_EQUITY", "Telecom Tariff Scenario Equity Value", "technology_scenario", "(EBITDA + ARPU * tariff change * subscribers * 12 * realization * incremental margin) * target EV/EBITDA - net debt - spectrum liabilities", ("ebitda","arpu","tariff_change","subscribers","realization","incremental_margin","target_ev_ebitda","net_debt","spectrum_liabilities"), "currency", lambda i: (i["ebitda"]+i["arpu"]*i["tariff_change"]*i["subscribers"]*12.0*i["realization"]*i["incremental_margin"])*i["target_ev_ebitda"]-i["net_debt"]-i["spectrum_liabilities"], allow_mixed_units=True, methodology="Explicit tariff scenario; assumptions are not facts"),
    CalculationSpec("TOWER_TENANCY_RATIO", "Tower Tenancy Ratio", "telecom_infrastructure", "tenants / revenue-generating sites", ("tenants","sites"), "tenants_per_site", lambda i: _div(i["tenants"],i["sites"]), allow_mixed_units=True),
    CalculationSpec("TOWER_REVENUE_PER_TENANT", "Tower Revenue per Tenant", "telecom_infrastructure", "rental revenue / tenants", ("rental_revenue","tenants"), "currency_per_tenant", lambda i: _div(i["rental_revenue"],i["tenants"]), allow_mixed_units=True),
    CalculationSpec("TOWER_EV_PER_SITE", "Tower EV per Site", "telecom_infrastructure_valuation", "enterprise value / revenue-generating sites", ("enterprise_value","sites"), "currency_per_site", lambda i: _div(i["enterprise_value"],i["sites"]), allow_mixed_units=True),
    CalculationSpec("TOWER_ENERGY_PASS_THROUGH", "Tower Energy Pass-through Coverage", "telecom_infrastructure", "energy reimbursements / energy costs", ("energy_reimbursements","energy_costs"), "multiple", lambda i: _div(i["energy_reimbursements"],i["energy_costs"])),
    CalculationSpec("TOWER_NET_DEBT_EBITDA", "Tower Net Debt to EBITDA", "telecom_infrastructure", "net debt / EBITDA", ("net_debt","ebitda"), "multiple", lambda i: _div(i["net_debt"],i["ebitda"]), allow_mixed_units=True),
    CalculationSpec("TOWER_SCENARIO_EQUITY", "Tower Scenario Equity Value", "technology_scenario", "sites * tenancy ratio * annual rent per tenant * EBITDA margin * target EV/EBITDA - net debt", ("sites","tenancy_ratio","annual_rent_per_tenant","ebitda_margin","target_ev_ebitda","net_debt"), "currency", lambda i: i["sites"]*i["tenancy_ratio"]*i["annual_rent_per_tenant"]*i["ebitda_margin"]*i["target_ev_ebitda"]-i["net_debt"], allow_mixed_units=True, methodology="Explicit contracted-infrastructure scenario; assumptions are not facts"),
    CalculationSpec("TECH_SPECIALIZED_RATIO", "Specialized Technology Ratio", "technology", "numerator / denominator", ("numerator","denominator"), "ratio", lambda i: _div(i["numerator"],i["denominator"]), allow_mixed_units=True),
    CalculationSpec("TECH_SPECIALIZED_GROWTH", "Specialized Technology Growth", "technology", "closing / opening - 1", ("opening","closing"), "decimal", lambda i: _div(i["closing"],i["opening"])-1.0, allow_mixed_units=True),
    CalculationSpec("TECH_SPECIALIZED_SCENARIO_EQUITY", "Specialized Technology Scenario Equity Value", "technology_scenario", "revenue * (1 + revenue growth) * EBITDA margin * target EV/EBITDA - net debt", ("revenue","revenue_growth","ebitda_margin","target_ev_ebitda","net_debt"), "currency", lambda i: i["revenue"]*(1.0+i["revenue_growth"])*i["ebitda_margin"]*i["target_ev_ebitda"]-i["net_debt"], allow_mixed_units=True, methodology="Explicit one-period scenario; assumptions are not facts"),
    CalculationSpec("TECH_PRICE_TO_EARNINGS", "Technology Price to Earnings", "technology_valuation", "point-in-time market price per share / normalized earnings per share", ("market_price", "normalized_eps"), "multiple", lambda i: _div(i["market_price"], i["normalized_eps"]), allow_mixed_units=True, allow_mixed_periods=True),
    CalculationSpec("REVENUE_PER_EMPLOYEE", "Revenue per Employee", "it_services", "revenue / average headcount", ("revenue", "opening_headcount", "closing_headcount"), "currency_per_employee", lambda i: _div(i["revenue"], _avg(i, "opening_headcount", "closing_headcount")), allow_mixed_units=True),
    CalculationSpec("BOOK_TO_BILL", "Book to Bill", "it_services", "total contract value / revenue", ("total_contract_value", "revenue"), "multiple", lambda i: _div(i["total_contract_value"], i["revenue"])),
    CalculationSpec("EBIT_MARGIN", "EBIT Margin", "profitability", "EBIT / revenue", ("ebit", "revenue"), "decimal", lambda i: _div(i["ebit"], i["revenue"])),
    CalculationSpec("FCF_MARGIN", "Free Cash Flow Margin", "cash_flow", "free cash flow / revenue", ("fcf", "revenue"), "decimal", lambda i: _div(i["fcf"], i["revenue"])),
    CalculationSpec("UTILIZATION_REVENUE_CAPACITY", "IT Services Utilization Revenue Capacity", "it_services", "average headcount * utilization * billing rate * billable periods", ("opening_headcount", "closing_headcount", "utilization", "billing_rate", "billable_periods"), "currency", lambda i: _avg(i, "opening_headcount", "closing_headcount") * i["utilization"] * i["billing_rate"] * i["billable_periods"], allow_mixed_units=True, methodology="Capacity bridge, not reported revenue; utilization is a decimal assumption or disclosed KPI"),
    CalculationSpec("IT_SERVICES_SCENARIO_PRICE", "IT Services Scenario Equity Value per Share", "technology_scenario", "revenue * (1 + revenue growth) * EBIT margin * (1 - tax rate) / shares outstanding * target P/E", ("revenue", "revenue_growth", "ebit_margin", "tax_rate", "shares_outstanding", "target_pe"), "currency_per_share", lambda i: _div(i["revenue"] * (1.0 + i["revenue_growth"]) * i["ebit_margin"] * (1.0 - i["tax_rate"]), i["shares_outstanding"]) * i["target_pe"], allow_mixed_units=True, methodology="Explicit one-period scenario; assumptions are not facts"),
    CalculationSpec("ARR_GROWTH", "Annual Recurring Revenue Growth", "saas", "closing ARR / opening ARR - 1", ("opening_arr", "closing_arr"), "decimal", lambda i: _div(i["closing_arr"], i["opening_arr"]) - 1.0),
    CalculationSpec("NET_REVENUE_RETENTION", "Net Revenue Retention", "saas", "(opening ARR - churned ARR - contraction ARR + expansion ARR) / opening ARR", ("opening_arr", "churned_arr", "contraction_arr", "expansion_arr"), "decimal", lambda i: _div(i["opening_arr"] - i["churned_arr"] - i["contraction_arr"] + i["expansion_arr"], i["opening_arr"])),
    CalculationSpec("GROSS_REVENUE_RETENTION", "Gross Revenue Retention", "saas", "(opening ARR - churned ARR - contraction ARR) / opening ARR", ("opening_arr", "churned_arr", "contraction_arr"), "decimal", lambda i: _div(i["opening_arr"] - i["churned_arr"] - i["contraction_arr"], i["opening_arr"])),
    CalculationSpec("CAC_PAYBACK_MONTHS", "CAC Payback", "saas", "customer acquisition cost / monthly gross profit from new customer", ("customer_acquisition_cost", "monthly_revenue_per_new_customer", "gross_margin"), "months", lambda i: _div(i["customer_acquisition_cost"], i["monthly_revenue_per_new_customer"] * i["gross_margin"]), allow_mixed_units=True),
    CalculationSpec("CUSTOMER_LTV", "Customer Lifetime Value", "saas", "annual revenue per customer * gross margin / annual logo churn", ("annual_revenue_per_customer", "gross_margin", "annual_logo_churn"), "currency_per_customer", lambda i: _div(i["annual_revenue_per_customer"] * i["gross_margin"], i["annual_logo_churn"]), allow_mixed_units=True),
    CalculationSpec("LTV_CAC", "Lifetime Value to CAC", "saas", "customer lifetime value / customer acquisition cost", ("customer_lifetime_value", "customer_acquisition_cost"), "multiple", lambda i: _div(i["customer_lifetime_value"], i["customer_acquisition_cost"]), allow_mixed_units=True),
    CalculationSpec("RULE_OF_40", "Rule of 40", "saas", "ARR growth + free cash flow margin", ("arr_growth", "fcf_margin"), "decimal", lambda i: i["arr_growth"] + i["fcf_margin"], allow_mixed_units=True),
    CalculationSpec("EV_ARR", "Enterprise Value to ARR", "saas_valuation", "enterprise value / annual recurring revenue", ("enterprise_value", "arr"), "multiple", lambda i: _div(i["enterprise_value"], i["arr"])),
    CalculationSpec("SAAS_SCENARIO_EV", "SaaS Scenario Enterprise Value", "technology_scenario", "ARR * (1 + ARR growth) * target EV/ARR", ("arr", "arr_growth", "target_ev_arr"), "currency", lambda i: i["arr"] * (1.0 + i["arr_growth"]) * i["target_ev_arr"], allow_mixed_units=True, methodology="Explicit one-period scenario; assumptions are not facts"),
    CalculationSpec("PLATFORM_TAKE_RATE", "Platform Take Rate", "marketplace", "platform revenue / gross merchandise value", ("revenue", "gmv"), "decimal", lambda i: _div(i["revenue"], i["gmv"])),
    CalculationSpec("PLATFORM_GMV_GROWTH", "Platform GMV Growth", "marketplace", "closing GMV / opening GMV - 1", ("opening_gmv", "closing_gmv"), "decimal", lambda i: _div(i["closing_gmv"], i["opening_gmv"]) - 1.0),
    CalculationSpec("PLATFORM_ORDER_FREQUENCY", "Platform Order Frequency", "marketplace", "orders / active buyers", ("orders", "active_buyers"), "orders_per_buyer", lambda i: _div(i["orders"], i["active_buyers"]), allow_mixed_units=True),
    CalculationSpec("PLATFORM_CONTRIBUTION_MARGIN", "Platform Contribution Margin", "marketplace", "contribution profit / revenue", ("contribution_profit", "revenue"), "decimal", lambda i: _div(i["contribution_profit"], i["revenue"])),
    CalculationSpec("PLATFORM_CUSTOMER_ACQUISITION_COST", "Platform Customer Acquisition Cost", "marketplace", "sales and marketing spend / new customers", ("sales_marketing_spend", "new_customers"), "currency_per_customer", lambda i: _div(i["sales_marketing_spend"], i["new_customers"]), allow_mixed_units=True),
    CalculationSpec("EV_GMV", "Enterprise Value to GMV", "marketplace_valuation", "enterprise value / gross merchandise value", ("enterprise_value", "gmv"), "multiple", lambda i: _div(i["enterprise_value"], i["gmv"])),
    CalculationSpec("PLATFORM_SCENARIO_EV", "Platform Scenario Enterprise Value", "technology_scenario", "GMV * (1 + GMV growth) * take rate * target EV/revenue", ("gmv", "gmv_growth", "take_rate", "target_ev_revenue"), "currency", lambda i: i["gmv"] * (1.0 + i["gmv_growth"]) * i["take_rate"] * i["target_ev_revenue"], allow_mixed_units=True, methodology="Explicit one-period scenario; assumptions are not facts"),
    CalculationSpec("DIGITAL_NET_REVENUE_GROWTH", "Digital Commerce Net Revenue Growth", "digital_commerce", "closing net revenue / opening net revenue - 1", ("opening_net_revenue", "closing_net_revenue"), "decimal", lambda i: _div(i["closing_net_revenue"], i["opening_net_revenue"]) - 1.0),
    CalculationSpec("DIGITAL_AVERAGE_ORDER_VALUE", "Digital Commerce Average Order Value", "digital_commerce", "net sales / net orders", ("net_sales", "net_orders"), "currency_per_order", lambda i: _div(i["net_sales"], i["net_orders"]), allow_mixed_units=True),
    CalculationSpec("DIGITAL_GROSS_MARGIN", "Digital Commerce Gross Margin", "digital_commerce", "gross profit / net revenue", ("gross_profit", "net_revenue"), "decimal", lambda i: _div(i["gross_profit"], i["net_revenue"])),
    CalculationSpec("DIGITAL_INVENTORY_TURNS", "Digital Commerce Inventory Turns", "digital_commerce", "cost of goods sold / average inventory", ("cogs", "opening_inventory", "closing_inventory"), "multiple", lambda i: _div(i["cogs"], _avg(i,"opening_inventory","closing_inventory")), allow_mixed_units=True),
    CalculationSpec("DIGITAL_RETURN_RATE", "Digital Commerce Return Rate", "digital_commerce", "returned orders / gross orders", ("returned_orders", "gross_orders"), "decimal", lambda i: _div(i["returned_orders"], i["gross_orders"]), allow_mixed_units=True),
    CalculationSpec("DIGITAL_AD_ARPU", "Consumer Internet Advertising ARPU", "consumer_internet", "advertising revenue / monetizable users", ("advertising_revenue", "monetizable_users"), "currency_per_user", lambda i: _div(i["advertising_revenue"], i["monetizable_users"]), allow_mixed_units=True),
    CalculationSpec("DIGITAL_SCENARIO_EV", "Consumer Internet Scenario Enterprise Value", "technology_scenario", "net revenue * (1 + growth) * target EV/revenue", ("net_revenue", "revenue_growth", "target_ev_revenue"), "currency", lambda i: i["net_revenue"] * (1.0 + i["revenue_growth"]) * i["target_ev_revenue"], allow_mixed_units=True, methodology="Explicit one-period scenario; assumptions are not facts"),
    CalculationSpec("SEMI_REVENUE_GROWTH", "Semiconductor Revenue Growth", "semiconductor", "closing revenue / opening revenue - 1", ("opening_revenue","closing_revenue"), "decimal", lambda i: _div(i["closing_revenue"],i["opening_revenue"]) - 1.0),
    CalculationSpec("SEMI_CAPACITY_REVENUE", "Semiconductor Capacity Revenue", "semiconductor", "capacity * utilization * yield * average selling price", ("capacity","utilization","yield_rate","average_selling_price"), "currency", lambda i: i["capacity"]*i["utilization"]*i["yield_rate"]*i["average_selling_price"], allow_mixed_units=True, methodology="Capacity bridge, not reported revenue"),
    CalculationSpec("SEMI_RND_INTENSITY", "Semiconductor R&D Intensity", "semiconductor", "research and development expense / revenue", ("rnd_expense","revenue"), "decimal", lambda i: _div(i["rnd_expense"],i["revenue"])),
    CalculationSpec("SEMI_CAPEX_INTENSITY", "Semiconductor Capex Intensity", "semiconductor", "capital expenditure / revenue", ("capex","revenue"), "decimal", lambda i: _div(i["capex"],i["revenue"])),
    CalculationSpec("SEMI_SCENARIO_EV", "Semiconductor Scenario Enterprise Value", "technology_scenario", "revenue * (1 + growth) * EBITDA margin * target EV/EBITDA", ("revenue","revenue_growth","ebitda_margin","target_ev_ebitda"), "currency", lambda i: i["revenue"]*(1.0+i["revenue_growth"])*i["ebitda_margin"]*i["target_ev_ebitda"], allow_mixed_units=True, methodology="Explicit one-period scenario; assumptions are not facts"),
)

REGISTRY = {spec.calculation_id: spec for spec in SPECS}


def get_spec(calculation_id: str) -> CalculationSpec | None:
    return REGISTRY.get(str(calculation_id or "").strip().upper())


def list_specs() -> list[dict]:
    return [spec.public() for spec in sorted(SPECS, key=lambda row: row.calculation_id)]
