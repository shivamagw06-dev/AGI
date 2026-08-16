"""Public-source Core 50 registry and warehouse readiness. No collection on read."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import time
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

_PUBLIC_CACHE: dict[tuple[str, int], tuple[float, list[dict[str, Any]]]] = {}


def _warehouse_rows(table: str, limit: int = 5000) -> list[dict[str, Any]]:
    if table.startswith("macro_public_"):
        try:
            from macro_intelligence_engine.public_ingestion import _rest
            requested=max(1,int(limit)); cache_key=(table,requested); now=time.monotonic()
            cached=_PUBLIC_CACHE.get(cache_key)
            if cached and now-cached[0] < 20:
                return list(cached[1])
            rows=[]; page_size=min(1000,requested)
            order = "&order=ingested_at.desc" if table == "macro_public_observations" else ""
            for offset in range(0,requested,page_size):
                page=list(_rest(table,query=f"?select=*&limit={page_size}&offset={offset}{order}") or [])
                rows.extend(page)
                if len(page) < page_size: break
            result=rows[:requested]
            _PUBLIC_CACHE[cache_key]=(now,result)
            return list(result)
        except Exception:
            return []
    try:
        from institutional_warehouse import store
        return list((store.fetch(table, limit=limit) or {}).get("rows") or [])
    except Exception:
        return []


def _core_observation_rows(limit: int = 10000) -> list[dict[str, Any]]:
    """Read only Core 50 evidence so G20 and market histories cannot crowd it out."""
    try:
        from macro_intelligence_engine.public_ingestion import _rest
        requested=max(1,int(limit)); cache_key=("macro_public_observations_core",requested); now=time.monotonic()
        cached=_PUBLIC_CACHE.get(cache_key)
        if cached and now-cached[0] < 20:
            return list(cached[1])
        ids=",".join(row[0] for row in CORE_50); rows=[]; page_size=min(1000,requested)
        for offset in range(0,requested,page_size):
            query=(f"?select=*&series_id=in.({ids})&country_code=in.(IND,WLD)"
                   f"&order=ingested_at.desc&limit={page_size}&offset={offset}")
            page=list(_rest("macro_public_observations",query=query) or [])
            rows.extend(page)
            if len(page) < page_size: break
        result=rows[:requested]; _PUBLIC_CACHE[cache_key]=(now,result)
        return list(result)
    except Exception:
        return []


def readiness(country: str = "India") -> dict[str, Any]:
    """Report persisted public-data coverage; never fabricates readiness from placeholders."""
    country_norm = str(country or "India").strip()
    registry = _warehouse_rows("macro_public_series_registry")
    observations = _core_observation_rows()
    allowed_countries = {country_norm.lower(), "in", "ind", "global", "wld"}
    registry_ids = {
        str(row.get("series_id") or "") for row in registry
        if str(row.get("country_code") or row.get("country") or "").lower() in allowed_countries
    }
    usable_observations = [
        row for row in observations
        if str(row.get("country_code") or row.get("country") or "").lower() in allowed_countries
        and row.get("value_numeric") is not None
    ]
    observed_ids = {str(row.get("series_id") or "") for row in usable_observations}
    verified_ids = {
        str(row.get("series_id") or "") for row in usable_observations
        if str(row.get("quality_status") or "").upper() == "VERIFIED"
    }
    pit_valid_ids = {
        str(row.get("series_id") or "") for row in usable_observations
        if str(row.get("pit_status") or "").upper() in {"OFFICIAL_VINTAGE", "RELEASE_TIMESTAMP_RECORDED"}
    }
    history_periods: dict[str, set[str]] = {}
    for row in usable_observations:
        history_periods.setdefault(str(row.get("series_id") or ""), set()).add(str(row.get("period_date") or ""))
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
            "evidence_validated": series_id in verified_ids,
            "pit_validated": series_id in pit_valid_ids,
            "history_periods": len(history_periods.get(series_id, set())),
            "production_ready": series_id in verified_ids and series_id in pit_valid_ids and len(history_periods.get(series_id, set())) >= 24,
        }
        for series_id, domain, label, frequency in CORE_50
    ]
    observed = sum(1 for row in items if row["observed"])
    evidence_validated = sum(1 for row in items if row["evidence_validated"])
    pit_validated = sum(1 for row in items if row["pit_validated"])
    production_ready = sum(1 for row in items if row["production_ready"])
    return {
        "ok": True,
        "country": country_norm,
        "catalogue": "G20 Core 50 v1",
        "total": len(CORE_50),
        "registered": sum(1 for row in items if row["registered"]),
        "observed": observed,
        "mapped_but_empty": sum(1 for row in items if row["registered"] and not row["observed"]),
        "unmapped": sum(1 for row in items if not row["registered"]),
        "evidence_validated": evidence_validated,
        "pit_validated": pit_validated,
        "production_ready": production_ready,
        "coverage_percent": round(100 * observed / len(CORE_50), 1),
        "evidence_quality_percent": round(100 * evidence_validated / len(CORE_50), 1),
        "pit_quality_percent": round(100 * pit_validated / len(CORE_50), 1),
        "production_ready_percent": round(100 * production_ready / len(CORE_50), 1),
        "interpretation_readiness": "READY" if production_ready == len(CORE_50) else "BLOCKED",
        "status": "PRODUCTION READY" if production_ready == len(CORE_50) else "RED / NON-OPERATIONAL",
        "domains": [
            {"domain": domain, "observed": domains[domain], "total": total}
            for domain, total in sorted(domain_totals.items())
        ],
        "series": items,
        "sources": __import__("macro_intelligence_engine.public_ingestion", fromlist=["source_status"]).source_status(),
        "policy": "Coverage, evidence validation, PIT validation and production readiness are separate gates. Catalogue placeholders never count as evidence.",
    }


def latest_observations(country: str = "India") -> dict[str, Any]:
    """Return latest persisted observations with lineage; never calculate missing values."""
    country_norm = str(country or "India").strip()
    allowed = {country_norm.lower(), "in", "ind", "wld"}
    registry = {
        str(row.get("series_id") or ""): row
        for row in _warehouse_rows("macro_public_series_registry")
    }
    rows = [
        row for row in _core_observation_rows()
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


def g20_matrix() -> dict[str, Any]:
    """Latest comparable G20 observations. No scores or regimes are inferred."""
    from macro_intelligence_engine.public_ingestion import G20_COUNTRIES, G20_WORLD_BANK_SERIES

    registry = {
        str(row.get("series_id") or ""): row
        for row in _warehouse_rows("macro_public_series_registry", limit=10000)
    }
    rows = [
        row for row in _warehouse_rows("macro_public_observations", limit=10000)
        if str(row.get("series_id") or "").startswith("g20_")
        and row.get("value_numeric") is not None
    ]
    latest = {}
    for row in rows:
        key = (
            str(row.get("country_code") or "").upper(),
            str(row.get("series_id") or "").split("_", 2)[-1],
        )
        order = (str(row.get("period_date") or ""), str(row.get("available_at") or ""))
        if key not in latest or order > latest[key][0]:
            latest[key] = (order, row)
    countries = []
    frequency_counts = Counter()
    for iso3, name in G20_COUNTRIES.items():
        indicators = {}
        for key, (_source, label, unit) in G20_WORLD_BANK_SERIES.items():
            item = latest.get((iso3, key))
            row = item[1] if item else None
            if row:
                frequency_counts[str(row.get("frequency") or "unknown")] += 1
            indicators[key] = None if row is None else {
                "value": row.get("value_numeric"), "unit": row.get("unit") or unit,
                "frequency": row.get("frequency"), "observation_date": row.get("period_date"),
                "release_date": row.get("release_date"), "available_at": row.get("available_at"),
                "revision_number": row.get("revision_number", 0), "source": row.get("source"),
                "quality_status": row.get("quality_status"), "pit_status": "PIT LIMITED",
                "source_tier": "C", "label": label,
            }
        countries.append({
            "iso3": iso3, "country": name,
            "observed": sum(value is not None for value in indicators.values()),
            "total": len(indicators), "indicators": indicators,
        })
    observed = sum(row["observed"] for row in countries)
    total = len(countries) * len(G20_WORLD_BANK_SERIES)
    tier_counts = Counter()
    pit_valid = 0
    verified = 0
    for _, row in latest.values():
        meta = registry.get(str(row.get("series_id") or "")) or {}
        tier = str(meta.get("source_tier") or (row.get("metadata") or {}).get("source_tier") or "C").upper()
        tier_counts[tier if tier in {"A", "B", "C", "D"} else "C"] += 1
        if str(row.get("pit_status") or "").upper() in {"OFFICIAL_VINTAGE", "RELEASE_TIMESTAMP_RECORDED"}:
            pit_valid += 1
        if str(row.get("quality_status") or "").upper() == "VERIFIED":
            verified += 1
    critical_keys = {"gdp_growth", "inflation", "policy_rate", "yield_10y", "usd_fx"}
    critical_observed = sum(1 for (_iso3, key) in latest if key in critical_keys)
    return {
        "ok": True, "universe": "G20 19 economies", "countries": countries,
        "country_count": len(countries), "indicator_count": len(G20_WORLD_BANK_SERIES),
        "observed": observed, "total": total,
        "coverage_percent": round(100 * observed / total, 1) if total else 0,
        "frequency_mix": dict(sorted(frequency_counts.items())),
        "source_tier_mix": {tier: tier_counts[tier] for tier in ("A", "B", "C", "D")},
        "evidence_validated": verified,
        "pit_validated": pit_valid,
        "production_ready": 0,
        "critical_5": {"observed": critical_observed, "total": len(G20_COUNTRIES) * 5, "coverage_percent": round(100 * critical_observed / (len(G20_COUNTRIES) * 5), 1)},
        "status": "RED / NON-OPERATIONAL",
        "pit_status": "PIT LIMITED",
        "calculation_gate": "BLOCKED",
        "blocked_outputs": ["country_scores", "rankings", "macro_regimes", "investment_implications"],
        "policy": "Tier C harmonized observations only. Coverage is not validation. No country score, rank or regime is inferred.",
    }


def g20_source_plan() -> dict[str, Any]:
    """Return the governed collection plan reconciled to persisted warehouse data."""
    from macro_intelligence_engine.g20_source_catalog import COUNTRY_SOURCES, MODULES, catalogue

    registry = _warehouse_rows("macro_public_series_registry", limit=10000)
    observations = _warehouse_rows("macro_public_observations", limit=10000)
    registry_by_id = {str(row.get("series_id") or ""): row for row in registry}
    module_domains = {
        "central_bank": {"monetary"}, "fiscal": {"fiscal"}, "inflation": {"inflation"},
        "growth": {"growth", "activity", "labour", "structural"}, "rates": {"monetary"},
        "liquidity": {"financial", "credit", "monetary"}, "credit": {"financial", "credit"},
        "fx_external": {"external", "currency"}, "commodities": {"global", "commodities"},
    }
    registered_cells = set()
    observed_cells = set()
    for series_id, meta in registry_by_id.items():
        iso3 = str(meta.get("country_code") or "").upper()
        domain = str(meta.get("domain") or "").lower()
        for module, domains in module_domains.items():
            if domain in domains:
                registered_cells.add((iso3, module))
    for observation in observations:
        if observation.get("value_numeric") is None:
            continue
        series_id = str(observation.get("series_id") or "")
        meta = registry_by_id.get(series_id) or {}
        iso3 = str(observation.get("country_code") or meta.get("country_code") or "").upper()
        domain = str(meta.get("domain") or "").lower()
        for module, domains in module_domains.items():
            if domain in domains:
                observed_cells.add((iso3, module))
    rows = []
    for row in catalogue():
        iso3 = row["iso3"]
        key = (iso3, row["module"])
        state = "OBSERVED_PARTIAL" if key in observed_cells else ("REGISTERED" if key in registered_cells else "PLANNED")
        rows.append({**row, "status": state})
    status_counts = Counter(row["status"] for row in rows)
    return {
        "ok": True,
        "catalogue": "G20 x 9 Module Source Plan v1",
        "economies": len(COUNTRY_SOURCES),
        "modules": len(MODULES),
        "cells": len(rows),
        "source_priority": ["S1 Official Primary", "S2 Official International", "S3 Market Data", "S4 Alternative"],
        "status_counts": dict(status_counts),
        "plan": rows,
        "calculation_gate": "BLOCKED",
        "policy": "Catalogue presence is not evidence. A module is not validated until mapped observations pass provenance, history, freshness and PIT gates.",
    }
