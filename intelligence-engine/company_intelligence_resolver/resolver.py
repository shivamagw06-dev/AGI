"""Governed company analytical profile and KPI coverage resolver."""

from __future__ import annotations

import re
from typing import Any, Callable

from financial_engine import FinancialDataResolver
from industry_intelligence import framework_for


AFE_KPI_MAP = {
    "roe": "ROE", "roa": "ROA", "loan_growth": "LOAN_GROWTH",
    "deposit_growth": "DEPOSIT_GROWTH", "casa": "CASA_RATIO",
    "casa_ratio": "CASA_RATIO", "credit_deposit_ratio": "CREDIT_DEPOSIT_RATIO",
    "gnpa": "GNPA_RATIO", "nnpa": "NNPA_RATIO", "provision_coverage": "PCR",
    "pcr": "PCR", "nim": "NIM", "credit_cost": "CREDIT_COST",
    "cet1": "CET1_RATIO", "capital_adequacy": "CRAR", "crar": "CRAR",
    "cost_to_income": "COST_TO_INCOME", "pb": "PRICE_TO_BOOK",
}

RAW_KPI_MAP = {
    "revenue": ("revenue",), "revenue_growth": ("revenue",),
    "ebitda": ("ebitda",), "ebit_margin": ("ebit", "revenue"),
    "ebitda_margin": ("ebitda", "revenue"), "pat": ("pat", "net_income"),
    "eps": ("eps",), "cfo": ("cfo",), "capex": ("capex",),
    "fcf": ("free_cash_flow", "fcf"), "cash_conversion": ("cfo", "pat"),
    "roic": ("roic",), "roce": ("roce",), "net_debt": ("debt", "cash"),
    "debt": ("debt",), "working_capital": ("working_capital",),
    "market_price": ("market_price", "price", "close"),
    "book_value_per_share": ("book_value_per_share", "book_value", "bvps"),
    "subscribers": ("subscribers",), "arpu": ("arpu",), "churn": ("churn",),
    "market_share": ("market_share",), "spectrum": ("spectrum",),
    "deal_wins": ("deal_wins",), "utilisation": ("utilisation", "utilization"),
    "attrition": ("attrition",), "headcount": ("headcount", "employee_count"),
    "order_book": ("order_book",), "volume": ("volume",),
    "realization": ("realization", "realisation"), "capacity": ("capacity",),
    "capacity_utilization": ("capacity_utilization", "capacity_utilisation"),
    "ebitda_per_ton": ("ebitda_per_ton", "ebitda_per_tonne"),
}


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _metric(fact: dict[str, Any]) -> str:
    return _key(fact.get("canonical_metric") or fact.get("metric") or "")


def _available(fact: dict[str, Any], as_of_date: str | None) -> bool:
    stamp = fact.get("available_at") or fact.get("publication_date") or fact.get("published_timestamp")
    return not (as_of_date and stamp and str(stamp)[:10] > as_of_date[:10])


def _period_matches(fact: dict[str, Any], period: str | None) -> bool:
    if not period:
        return True
    observed = fact.get("reporting_period") or fact.get("period")
    return str(observed or "").strip().upper() == str(period).strip().upper()


class CompanyIntelligenceResolver:
    def __init__(
        self,
        *,
        identity_loader: Callable[[str], Any] | None = None,
        financial_resolver: FinancialDataResolver | None = None,
    ) -> None:
        if identity_loader is None:
            from company_identity.service import identity_for
            identity_loader = identity_for
        self.identity_loader = identity_loader
        self.financial = financial_resolver or FinancialDataResolver()

    def resolve(
        self,
        *,
        company_id: str,
        period: str | None = None,
        as_of_date: str | None = None,
        segments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        ticker = str(company_id or "").strip().upper()
        identity_obj = self.identity_loader(ticker)
        identity = identity_obj.to_dict() if hasattr(identity_obj, "to_dict") else dict(identity_obj or {})
        if not identity.get("resolved", bool(identity.get("industry_dna"))):
            return {"ok": False, "status": "COMPANY_CLASSIFICATION_UNAVAILABLE", "company_id": ticker, "fabricated": False}

        segment_rows = self._segments(identity, segments)
        frameworks = []
        required: list[str] = []
        for segment in segment_rows:
            model = framework_for(segment["industry"])
            frameworks.append({**segment, "framework": model})
            if model.get("ok"):
                required.extend(model.get("kpis", {}).get("required") or [])
        required = list(dict.fromkeys(_key(kpi) for kpi in required if _key(kpi)))
        facts = self.financial.facts_for(ticker)
        coverage = [self._cover_kpi(ticker, kpi, facts, period, as_of_date) for kpi in required]
        available = [row for row in coverage if row["status"] in {"CALCULATED", "SOURCE_AVAILABLE"}]
        missing = [row for row in coverage if row["status"] == "MISSING"]
        unmapped = [row for row in coverage if row["status"] == "UNMAPPED"]
        pct = round(100.0 * len(available) / len(required), 1) if required else 0.0
        return {
            "ok": True,
            "status": "READY" if required and len(available) == len(required) else "PARTIAL",
            "company_id": ticker,
            "company": {
                "name": identity.get("company_name"), "sector": identity.get("primary_sector"),
                "industry": identity.get("primary_industry"), "sub_industry": identity.get("industry_classification"),
                "business_type": identity.get("business_type"), "geography": identity.get("country"),
                "classification_source": identity.get("source"),
            },
            "segments": frameworks,
            "period": period,
            "as_of_date": as_of_date,
            "kpi_coverage": {
                "required": len(required), "available": len(available), "missing": len(missing),
                "unmapped": len(unmapped), "coverage_percent": pct, "items": coverage,
            },
            "research_protocol": self._protocol(frameworks),
            "fabricated": False,
        }

    @staticmethod
    def _segments(identity: dict[str, Any], supplied: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        if supplied:
            rows = []
            for item in supplied:
                if not item.get("industry"):
                    continue
                rows.append({"name": item.get("name") or item["industry"], "industry": item["industry"], "weight": item.get("weight")})
            return rows
        return [{"name": "primary", "industry": identity.get("industry_dna") or identity.get("primary_industry"), "weight": 100.0}]

    def _cover_kpi(self, ticker: str, kpi: str, facts: list[dict[str, Any]], period: str | None, as_of_date: str | None) -> dict[str, Any]:
        calc_id = AFE_KPI_MAP.get(kpi)
        if calc_id:
            result = self.financial.resolve(company_id=ticker, calculation_id=calc_id, period=period, as_of_date=as_of_date)
            if result.get("status") == "SUCCESS":
                return {"kpi": kpi, "status": "CALCULATED", "calculation_id": calc_id, "inputs": sorted(result.get("inputs") or {})}
            return {"kpi": kpi, "status": "MISSING", "calculation_id": calc_id, "reason": result.get("status"), "missing_input": result.get("missing_input")}
        aliases = set(RAW_KPI_MAP.get(kpi) or ())
        if not aliases:
            return {"kpi": kpi, "status": "UNMAPPED", "reason": "KPI_MAPPING_UNAVAILABLE"}
        found = [fact for fact in facts if _metric(fact) in aliases and _period_matches(fact, period) and _available(fact, as_of_date)]
        if not found:
            return {"kpi": kpi, "status": "MISSING", "canonical_metrics": sorted(aliases), "reason": "DATA_UNAVAILABLE"}
        sources = sorted({str(f.get("source_id") or f.get("fact_id")) for f in found if f.get("source_id") or f.get("fact_id")})
        return {"kpi": kpi, "status": "SOURCE_AVAILABLE", "canonical_metrics": sorted(aliases), "source_ids": sources[:10]}

    @staticmethod
    def _protocol(frameworks: list[dict[str, Any]]) -> dict[str, Any]:
        drivers, valuation, risks, monitoring = [], [], [], []
        for row in frameworks:
            model = row.get("framework") or {}
            drivers.extend(model.get("forecast_drivers") or [])
            valuation.extend((model.get("valuation") or {}).get("methods") or [])
            risks.extend(model.get("risks") or [])
            monitoring.extend(model.get("monitoring") or [])
        return {
            "sequence": ["business", "industry", "financials", "drivers", "causality", "valuation", "scenarios", "risks", "thesis", "invalidation", "monitoring"],
            "earnings_drivers": list(dict.fromkeys(drivers)),
            "valuation_methods": list(dict.fromkeys(valuation)),
            "risks": list(dict.fromkeys(risks)),
            "monitoring": list(dict.fromkeys(monitoring)),
        }
