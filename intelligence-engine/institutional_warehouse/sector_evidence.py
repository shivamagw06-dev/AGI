"""Build the editable missing-evidence matrix for completed valuation phases."""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable

from institutional_warehouse import store


FINANCIAL_COHORTS = {
    "COMMERCIAL_BANK": {"HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK", "SBIN"},
    "SMALL_FINANCE_BANK": {"AUBANK", "UJJIVANSFB"},
    "NBFC": {"BAJFINANCE", "CHOLAFIN", "MUTHOOTFIN"},
    "HOUSING_FINANCE": {"LICHSGFIN", "PNBHOUSING"},
    "LIFE_INSURANCE": {"HDFCLIFE", "SBILIFE", "ICICIPRULI"},
    "GENERAL_INSURANCE": {"ICICIGI", "NIACL"},
    "HEALTH_INSURANCE": {"STARHEALTH"},
    "ASSET_MANAGEMENT": {"HDFCAMC", "NAM-INDIA"},
    "BROKER": {"ANGELONE", "IIFLSEC"},
    "EXCHANGE_INFRASTRUCTURE": {"BSE", "MCX"},
    "FINTECH_PAYMENTS": {"PAYTM"},
    "DIVERSIFIED_FINANCIALS": {"BAJAJFINSV"},
}

TECHNOLOGY_COHORTS = {
    "IT_SERVICES": {"TCS", "INFY", "HCLTECH", "WIPRO", "TECHM"},
    "SOFTWARE_SAAS": {"NEWGEN", "RATEGAIN", "TANLA"},
    "INTERNET_PLATFORMS_MARKETPLACES": {"NAUKRI", "ZOMATO", "NYKAA"},
    "CONSUMER_INTERNET_DIGITAL_COMMERCE": {"ZOMATO", "NYKAA", "PAYTM"},
    "SEMICONDUCTOR_RELATED": {"MOSCHIP", "SPEL"},
    "TELECOM": {"BHARTIARTL", "IDEA", "TATACOMM"},
    "TELECOM_INFRASTRUCTURE_TOWERS": {"INDUSTOWER"},
    "ERD_TECHNOLOGY_SERVICES": {"KPITTECH", "TATAELXSI"},
    "HARDWARE_ELECTRONICS": {"DIXON", "KAYNES"},
    "DATA_CENTRES": {"NETWEB", "ANANTRAJ"},
    "FINTECH_PAYMENTS": {"PAYTM"},
    "CYBERSECURITY_CLOUD": {"QUICKHEAL"},
}

MARKET_METRICS = {"market_price", "market_cap", "enterprise_value", "trading_volume", "market_share"}
ASSUMPTION_METRICS = {
    "agi_growth_expectation", "cost_of_equity", "payout_ratio", "target_pe", "target_ev_ebitda",
    "terminal_ev_ebitda", "terminal_multiple", "horizon_years", "scenario_revenue_growth",
    "scenario_ebitda_margin", "normalized_spread", "discount_rate", "operating_life",
    "annual_fcf", "initial_capex", "holdco_discount",
}
CALCULATED_METRICS = {
    "normalized_eps", "normalized_ebitda", "book_value_per_share", "fcf_per_share", "gross_profit",
    "contribution_profit", "cash_burn", "net_debt", "spread", "roa", "roe", "fcf",
}
PERCENT_METRICS = {
    "roe", "roa", "growth", "cost_of_equity", "payout_ratio", "gnpa", "credit_cost", "cet1",
    "capital_adequacy", "solvency", "persistency", "claims_ratio", "expense_ratio", "fee_yield",
    "operating_margin", "retention", "market_share", "utilization", "attrition", "client_concentration",
    "gross_margin", "ebitda_margin", "capacity_utilization", "occupancy", "allowed_return",
}
COUNT_METRICS = {
    "opening_headcount", "closing_headcount", "active_clients", "active_merchants", "opening_stores",
    "closing_stores", "rooms", "sites", "tenants", "shares_outstanding", "available_days",
}

DEFINITIONS = {
    "aum": "Assets under management at period end.",
    "agi_growth_expectation": "AGI base-case forward growth assumption used for reverse valuation; this is not a reported fact.",
    "cost_of_equity": "AGI required annual equity return assumption for the company.",
    "market_price": "Closing or live NSE share price at the stated as-of timestamp.",
    "enterprise_value": "Market capitalisation plus net debt and other claims, using the same as-of date.",
    "normalized_eps": "Earnings per share adjusted to remove exceptional and non-recurring items.",
    "fcf": "Cash from operations less capital expenditure for the stated period.",
    "ebitda": "Reported or consistently adjusted earnings before interest, tax, depreciation and amortisation.",
    "revenue": "Consolidated operating revenue for the stated period.",
    "gnpa": "Gross non-performing assets divided by gross advances.",
    "credit_cost": "Loan-loss provisions divided by average advances, annualised where appropriate.",
    "cet1": "Common Equity Tier 1 capital ratio under the applicable regulatory framework.",
    "trading_volume": "Exchange or broker trading activity for a clearly stated period and measurement basis.",
    "operating_margin": "Operating profit divided by revenue for the stated period.",
    "installed_capacity_mw": "Operational installed generation capacity in megawatts at period end.",
    "generation": "Electricity generated during the period, normally in MWh or GWh.",
    "production_volume": "Physical output during the period in the company-disclosed unit.",
    "realization_per_unit": "Average realised selling price per physical unit during the period.",
    "cash_cost_per_unit": "Cash operating cost per physical unit on a consistent basis.",
    "reserves": "Proved or reported economically recoverable reserves at period end.",
    "total_contract_value": "Value of signed contracts or deal wins disclosed for the period.",
}


def _metric_metadata(metric: str, phase: str, family: str) -> dict[str, str]:
    label = metric.replace("_", " ").strip().title()
    input_type = "ASSUMPTION" if metric in ASSUMPTION_METRICS else "MARKET" if metric in MARKET_METRICS else "CALCULATED" if metric in CALCULATED_METRICS else "REPORTED"
    if metric in PERCENT_METRICS or metric.endswith(("_margin", "_ratio", "_growth", "_share", "_yield")):
        unit = "decimal ratio (e.g. 0.15 = 15%)"
    elif metric in COUNT_METRICS or metric.endswith(("_days", "_years")):
        unit = "count"
    elif metric.endswith("_mw"):
        unit = "MW"
    elif "per_unit" in metric or metric in {"market_price", "normalized_eps", "book_value_per_share", "fcf_per_share", "asp", "adr"}:
        unit = "INR per share / stated unit"
    elif metric in {"revenue", "ebitda", "ebit", "fcf", "capex", "net_debt", "enterprise_value", "gross_profit", "aum", "vnb", "ape"}:
        unit = "INR million"
    else:
        unit = "company-reported unit; specify it"
    period = "As-of date" if input_type in {"MARKET", "ASSUMPTION"} else "Latest quarter and FY; retain historical periods"
    if input_type == "ASSUMPTION":
        source = "Enter AGI analyst assumption with rationale in Evidence Note; do not present as reported data."
    elif input_type == "MARKET":
        source = "NSE/BSE or approved market-data feed; record exact as-of date/time."
    elif phase.startswith("Phase 1"):
        source = "Annual report, quarterly filing, investor presentation, RBI/IRDAI/AMFI/exchange disclosure as applicable."
    elif phase.startswith("Phase 5"):
        source = "Annual report, investor presentation, regulatory/project disclosure, tariff order or official operating update."
    else:
        source = "Annual report, quarterly results, investor presentation or NSE/BSE filing; use a primary source first."
    definition = DEFINITIONS.get(metric, f"{label} required by the {family.replace('_', ' ').title()} valuation model. Use the disclosed definition consistently across periods.")
    return {"metric_label": label, "definition": definition, "input_type": input_type,
            "expected_unit": unit, "expected_period": period, "source_guidance": source}


def _technology_required(family: str) -> tuple[str, ...]:
    from technology_valuation.service import REQUIRED_INPUTS
    from technology_valuation.saas_service import REQUIRED_SAAS_INPUTS
    from technology_valuation.platform_service import REQUIRED_PLATFORM_INPUTS
    from technology_valuation.consumer_service import REQUIRED_CONSUMER_INPUTS
    from technology_valuation.semiconductor_service import REQUIRED_SEMI_INPUTS
    from technology_valuation.telecom_service import REQUIRED_TELECOM_INPUTS
    from technology_valuation.tower_service import REQUIRED_TOWER_INPUTS
    from technology_valuation.specialized_service import REQUIRED_SPECIALIZED
    mapping = {
        "IT_SERVICES": REQUIRED_INPUTS,
        "SOFTWARE_SAAS": REQUIRED_SAAS_INPUTS,
        "INTERNET_PLATFORMS_MARKETPLACES": REQUIRED_PLATFORM_INPUTS,
        "CONSUMER_INTERNET_DIGITAL_COMMERCE": REQUIRED_CONSUMER_INPUTS,
        "SEMICONDUCTOR_RELATED": REQUIRED_SEMI_INPUTS,
        "TELECOM": REQUIRED_TELECOM_INPUTS,
        "TELECOM_INFRASTRUCTURE_TOWERS": REQUIRED_TOWER_INPUTS,
    }
    return tuple(mapping.get(family) or REQUIRED_SPECIALIZED.get(family) or ())


def _curricula() -> Iterable[tuple[str, str, set[str], tuple[str, ...]]]:
    from financials_valuation.service import CRITICAL
    from financials_valuation.nonbank_service import PROFILES
    from consumer_valuation.classification import COHORTS as CONSUMER
    from consumer_valuation.service import COMMON_REQUIRED, SPECIAL_REQUIRED
    from industrial_valuation.classification import COHORTS as INDUSTRIAL
    from industrial_valuation.service import required_inputs as industrial_required
    from energy_valuation.classification import COHORTS as ENERGY
    from energy_valuation.service import required_inputs as energy_required
    for family, symbols in FINANCIAL_COHORTS.items():
        required = CRITICAL if family == "COMMERCIAL_BANK" else PROFILES[family].required
        yield "Phase 1 - Financials", family, symbols, tuple(required)
    for family, symbols in TECHNOLOGY_COHORTS.items():
        yield "Phase 2 - Technology", family, symbols, _technology_required(family)
    for family, symbols in CONSUMER.items():
        yield "Phase 3 - Consumer", family, symbols, COMMON_REQUIRED + SPECIAL_REQUIRED[family]
    for family, symbols in INDUSTRIAL.items():
        yield "Phase 4 - Industrials", family, symbols, industrial_required(family)
    for family, symbols in ENERGY.items():
        yield "Phase 5 - Energy", family, symbols, energy_required(family)


def _find_value(record: Any, metric: str) -> tuple[Any, dict[str, Any]]:
    """Conservative exact-key lookup; never infer one accounting concept from another."""
    if isinstance(record, dict):
        if metric in record and record[metric] not in (None, ""):
            value = record[metric]
            return (value.get("value"), value) if isinstance(value, dict) else (value, record)
        for value in record.values():
            found, meta = _find_value(value, metric)
            if found not in (None, ""):
                return found, meta
    elif isinstance(record, list):
        for value in record:
            found, meta = _find_value(value, metric)
            if found not in (None, ""):
                return found, meta
    return None, {}


def _existing_manual() -> set[tuple[str, str, str, str]]:
    rows = store.all_rows("sector_evidence_matrix", limit=5000)
    return {(str(x.get("phase")), str(x.get("symbol")), str(x.get("subsector")), str(x.get("metric"))) for x in rows}


def sync(*, actor: str = "sector_evidence_sync") -> dict[str, Any]:
    """Add newly required rows without overwriting any administrator entry."""
    from institutional_warehouse.production import read_company
    existing = _existing_manual()
    today = date.today().isoformat()
    rows: list[dict[str, Any]] = []
    for phase, family, symbols, metrics in _curricula():
        for symbol in sorted(symbols):
            missing_metrics = [metric for metric in metrics if (phase, symbol, family, metric) not in existing]
            if not missing_metrics:
                continue
            try:
                record = read_company(symbol) or {}
            except Exception:
                record = {}
            master = record.get("master") if isinstance(record.get("master"), dict) else {}
            company_name = master.get("company_name") or master.get("legal_name") or symbol
            for metric in missing_metrics:
                value, meta = _find_value(record, metric)
                source = meta.get("source_id") or meta.get("source")
                period = meta.get("period") or meta.get("fiscal_year") or meta.get("quarter")
                available_at = meta.get("available_at") or meta.get("last_updated")
                supported = value is not None and bool(source) and bool(period) and bool(available_at)
                rows.append({
                    "company_name": company_name, "phase": phase, "symbol": symbol, "subsector": family, "metric": metric,
                    **_metric_metadata(metric, phase, family),
                    "required": True, "available": supported, "value": value if isinstance(value, (int, float)) else None,
                    "unit": meta.get("unit"), "period": period,
                    "publication_date": str(available_at)[:10] if available_at else None,
                    "as_of_date": today, "pit_valid": supported,
                    "source": source, "evidence": None,
                    "quality": "UNREVIEWED", "status": "SUPPORTED" if supported else "DATA_REQUIRED",
                    "review_notes": "Auto-matched by exact warehouse key; verify before research use." if supported else None,
                })
    # Schema/instruction enrichment is safe for already-created rows: admin
    # overrides live in a separate layer and remain effective.
    current_rows = store.all_rows("sector_evidence_matrix", limit=5000)
    enrichment = []
    company_cache: dict[str, str] = {}
    for row in current_rows:
        needs_enrichment = not row.get("company_name") or not row.get("metric_label") or row.get("source") == "curriculum_gap_audit"
        if not needs_enrichment:
            continue
        symbol = str(row.get("symbol") or "")
        if symbol not in company_cache:
            try:
                record = read_company(symbol) or {}
                master = record.get("master") if isinstance(record.get("master"), dict) else {}
                company_cache[symbol] = str(master.get("company_name") or master.get("legal_name") or symbol)
            except Exception:
                company_cache[symbol] = symbol
        phase = str(row.get("phase") or "")
        family = str(row.get("subsector") or "")
        metric = str(row.get("metric") or "")
        payload = {"phase": phase, "symbol": symbol, "subsector": family, "metric": metric,
                   "company_name": company_cache[symbol], **_metric_metadata(metric, phase, family)}
        if row.get("source") == "curriculum_gap_audit":
            payload["source"] = None
        enrichment.append(payload)
    result = store.upsert("sector_evidence_matrix", rows, source="curriculum_gap_audit", actor=actor,
                          reason="sync completed sector evidence requirements", journal=False)
    enriched = store.upsert("sector_evidence_matrix", enrichment, source="curriculum_gap_audit", actor=actor,
                            reason="add company names and manual-fill instructions", journal=False)
    return {**result, "enriched": enriched.get("updated", 0),
            "requirements": sum(len(symbols) * len(metrics) for _, _, symbols, metrics in _curricula())}
