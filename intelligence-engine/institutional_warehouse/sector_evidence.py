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
            for metric in missing_metrics:
                value, meta = _find_value(record, metric)
                source = meta.get("source_id") or meta.get("source")
                period = meta.get("period") or meta.get("fiscal_year") or meta.get("quarter")
                available_at = meta.get("available_at") or meta.get("last_updated")
                supported = value is not None and bool(source) and bool(period) and bool(available_at)
                rows.append({
                    "phase": phase, "symbol": symbol, "subsector": family, "metric": metric,
                    "required": True, "available": supported, "value": value if isinstance(value, (int, float)) else None,
                    "unit": meta.get("unit"), "period": period,
                    "publication_date": str(available_at)[:10] if available_at else None,
                    "as_of_date": today, "pit_valid": supported,
                    "source": source or "curriculum_gap_audit", "evidence": None,
                    "quality": "UNREVIEWED", "status": "SUPPORTED" if supported else "DATA_REQUIRED",
                    "review_notes": "Auto-matched by exact warehouse key; verify before research use." if supported else None,
                })
    result = store.upsert("sector_evidence_matrix", rows, source="curriculum_gap_audit", actor=actor,
                          reason="sync completed sector evidence requirements", journal=False)
    return {**result, "requirements": sum(len(symbols) * len(metrics) for _, _, symbols, metrics in _curricula())}
