"""Public-source Core 50 registry and warehouse readiness. No collection on read."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

CORE_50: tuple[tuple[str, str, str, str], ...] = (
    ("gdp", "growth", "GDP", "quarterly"),
    ("gdp_growth", "growth", "GDP Growth", "quarterly"),
    ("gdp_qoq", "growth", "GDP QoQ", "quarterly"),
    ("consumption", "growth", "Consumption", "quarterly"),
    ("investment", "growth", "Investment", "quarterly"),
    ("industrial_production", "growth", "Industrial Production", "monthly"),
    ("cpi", "inflation", "Headline CPI", "monthly"),
    ("core_cpi", "inflation", "Core CPI", "monthly"),
    ("ppi", "inflation", "Producer Prices", "monthly"),
    ("food_inflation", "inflation", "Food Inflation", "monthly"),
    ("unemployment", "labour", "Unemployment", "monthly"),
    ("employment", "labour", "Employment", "monthly"),
    ("wage_growth", "labour", "Wage Growth", "quarterly"),
    ("policy_rate", "monetary", "Policy Rate", "event"),
    ("real_policy_rate", "monetary", "Real Policy Rate", "derived"),
    ("yield_2y", "monetary", "2Y Yield", "daily"),
    ("yield_10y", "monetary", "10Y Yield", "daily"),
    ("yield_curve_10y_2y", "monetary", "10Y–2Y Curve", "derived"),
    ("government_debt_gdp", "fiscal", "Government Debt / GDP", "annual"),
    ("fiscal_balance_gdp", "fiscal", "Fiscal Balance / GDP", "annual"),
    ("primary_balance_gdp", "fiscal", "Primary Balance / GDP", "annual"),
    ("current_account_gdp", "external", "Current Account / GDP", "quarterly"),
    ("trade_balance", "external", "Trade Balance", "monthly"),
    ("exports", "external", "Exports", "monthly"),
    ("imports", "external", "Imports", "monthly"),
    ("fx_reserves", "external", "FX Reserves", "weekly"),
    ("private_credit_gdp", "credit", "Private Credit / GDP", "quarterly"),
    ("credit_growth", "credit", "Credit Growth", "monthly"),
    ("credit_gdp_gap", "credit", "Credit-to-GDP Gap", "quarterly"),
    ("debt_service_ratio", "credit", "Debt-Service Ratio", "quarterly"),
    ("usd_fx", "currency", "USD Exchange Rate", "daily"),
    ("reer", "currency", "Real Effective Exchange Rate", "monthly"),
    ("pmi", "activity", "Composite PMI", "monthly"),
    ("retail_sales", "activity", "Retail Sales", "monthly"),
    ("consumer_confidence", "activity", "Consumer Confidence", "monthly"),
    ("business_confidence", "activity", "Business Confidence", "monthly"),
    ("house_prices", "property", "House Prices", "quarterly"),
    ("commercial_property", "property", "Commercial Property Prices", "quarterly"),
    ("bank_credit", "financial", "Bank Credit", "monthly"),
    ("money_supply", "financial", "Money Supply", "monthly"),
    ("central_bank_assets", "financial", "Central-Bank Assets", "weekly"),
    ("oil", "global", "Crude Oil", "daily"),
    ("gas", "global", "Natural Gas", "daily"),
    ("copper", "global", "Copper", "daily"),
    ("gold", "global", "Gold", "daily"),
    ("global_liquidity", "global", "Global Liquidity", "quarterly"),
    ("global_trade", "global", "Global Trade", "monthly"),
    ("global_gdp", "global", "Global GDP", "quarterly"),
    ("us_financial_conditions", "global", "US Financial Conditions", "weekly"),
    ("global_risk", "global", "Global Risk Indicator", "daily"),
)


def _warehouse_rows(table: str, limit: int = 5000) -> list[dict[str, Any]]:
    if table.startswith("macro_public_"):
        try:
            from macro_intelligence_engine.public_ingestion import _rest
            return list(_rest(table, query=f"?select=*&limit={int(limit)}") or [])
        except Exception:
            return []
    try:
        from institutional_warehouse import store
        return list((store.fetch(table, limit=limit) or {}).get("rows") or [])
    except Exception:
        return []


def readiness(country: str = "India") -> dict[str, Any]:
    """Report persisted public-data coverage; never fabricates readiness from placeholders."""
    country_norm = str(country or "India").strip()
    registry = _warehouse_rows("macro_public_series_registry")
    observations = _warehouse_rows("macro_public_observations")
    registry_ids = {
        str(row.get("series_id") or "") for row in registry
        if str(row.get("country_code") or row.get("country") or "").lower() in {country_norm.lower(), "in", "ind", "global"}
    }
    observed_ids = {
        str(row.get("series_id") or "") for row in observations
        if str(row.get("country_code") or row.get("country") or "").lower() in {country_norm.lower(), "in", "ind", "global"}
        and row.get("value_numeric") is not None
    }
    domains = Counter(domain for series_id, domain, _, _ in CORE_50 if series_id in observed_ids)
    domain_totals = Counter(domain for _, domain, _, _ in CORE_50)
    items = [
        {
            "series_id": series_id,
            "domain": domain,
            "label": label,
            "frequency": frequency,
            "registered": series_id in registry_ids,
            "observed": series_id in observed_ids,
        }
        for series_id, domain, label, frequency in CORE_50
    ]
    observed = sum(1 for row in items if row["observed"])
    return {
        "ok": True,
        "country": country_norm,
        "catalogue": "G20 Core 50 v1",
        "total": len(CORE_50),
        "registered": sum(1 for row in items if row["registered"]),
        "observed": observed,
        "coverage_percent": round(100 * observed / len(CORE_50), 1),
        "status": "OPERATIONAL" if observed >= 40 else "DATA BUILDING",
        "domains": [
            {"domain": domain, "observed": domains[domain], "total": total}
            for domain, total in sorted(domain_totals.items())
        ],
        "series": items,
        "sources": __import__("macro_intelligence_engine.public_ingestion", fromlist=["source_status"]).source_status(),
        "policy": "Only persisted public/official observations count. Catalogue placeholders do not count as coverage.",
    }


def latest_observations(country: str = "India") -> dict[str, Any]:
    """Return latest persisted observations with lineage; never calculate missing values."""
    country_norm = str(country or "India").strip()
    allowed = {country_norm.lower(), "in", "ind"}
    registry = {
        str(row.get("series_id") or ""): row
        for row in _warehouse_rows("macro_public_series_registry")
    }
    rows = [
        row for row in _warehouse_rows("macro_public_observations")
        if str(row.get("country_code") or row.get("country") or "").lower() in allowed
        and row.get("value_numeric") is not None
    ]
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        series_id = str(row.get("series_id") or "")
        ordering = (str(row.get("period_date") or ""), str(row.get("available_at") or ""))
        prior = latest.get(series_id)
        if prior is None or ordering > prior[0]:
            latest[series_id] = (ordering, row)
    catalogue = {series_id: (domain, label, frequency) for series_id, domain, label, frequency in CORE_50}
    observations = []
    for series_id, (_, row) in sorted(latest.items()):
        domain, label, frequency = catalogue.get(series_id, ("other", series_id, row.get("frequency")))
        meta = registry.get(series_id) or {}
        observations.append({
            "series_id": series_id, "domain": domain, "label": label,
            "value": row.get("value_numeric"), "unit": row.get("unit") or meta.get("unit"),
            "frequency": row.get("frequency") or frequency,
            "observation_date": row.get("period_date"), "release_date": row.get("release_date"),
            "available_at": row.get("available_at"), "vintage_date": row.get("vintage_date"),
            "revision_number": row.get("revision_number", 0),
            "quality_status": row.get("quality_status") or "UNKNOWN",
            "source": row.get("source") or meta.get("primary_source"),
            "source_url": row.get("source_url") or meta.get("source_url"),
            "pit_status": "PIT LIMITED",
        })
    freshest = max((str(row.get("available_at") or "") for _, row in latest.values()), default=None)
    return {
        "ok": True, "country": country_norm, "generated_at": datetime.now(timezone.utc).isoformat(),
        "latest_available_at": freshest, "count": len(observations), "observations": observations,
        "pit_status": "PIT LIMITED",
        "policy": "Values are persisted official/public observations. No missing value is estimated or backfilled on read.",
    }
