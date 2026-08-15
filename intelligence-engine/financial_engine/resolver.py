"""Canonical warehouse → AFE input bridge with provenance and PIT controls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Any, Callable

from financial_engine.engine import calculate
from financial_engine.registry import get_spec


SOURCE_PRIORITY = {
    "regulatory_filing": 1, "company_filing": 2, "exchange_filing": 3,
    "rbi": 4, "regulator": 4, "validated_warehouse": 5,
    "agi_research_extraction": 6, "verified_other": 7,
}

INPUT_METRICS: dict[str, tuple[str, ...]] = {
    "pat": ("pat", "profit_after_tax", "net_income", "net_profit"),
    "equity": ("total_equity", "equity", "shareholders_equity", "net_worth"),
    "assets": ("total_assets", "assets"),
    "loans": ("gross_loans", "gross_advances", "advances", "loans"),
    "deposits": ("total_deposits", "deposits"),
    "casa_deposits": ("casa_deposits", "current_and_savings_deposits"),
    "gross_npa": ("gross_npa", "gross_non_performing_assets"),
    "net_npa": ("net_npa", "net_non_performing_assets"),
    "provisions": ("provisions", "credit_provisions", "loan_loss_provisions"),
    "net_interest_income": ("net_interest_income", "nii"),
    "interest_earning_assets": ("interest_earning_assets", "average_interest_earning_assets"),
    "cet1_capital": ("cet1_capital",),
    "regulatory_capital": ("regulatory_capital", "eligible_capital"),
    "risk_weighted_assets": ("risk_weighted_assets", "rwa"),
    "operating_expenses": ("operating_expenses", "opex"),
    "operating_income": ("operating_income", "total_income"),
    "market_price": ("market_price", "price", "close"),
    "book_value_per_share": ("book_value_per_share", "bvps"),
}

CALCULATION_INPUT_MAP: dict[str, dict[str, tuple[str, str]]] = {
    "ROE": {"pat": ("pat", "current"), "opening_equity": ("equity", "prior"), "closing_equity": ("equity", "current")},
    "ROA": {"pat": ("pat", "current"), "opening_assets": ("assets", "prior"), "closing_assets": ("assets", "current")},
    "LOAN_GROWTH": {"opening_loans": ("loans", "prior"), "closing_loans": ("loans", "current")},
    "DEPOSIT_GROWTH": {"opening_deposits": ("deposits", "prior"), "closing_deposits": ("deposits", "current")},
    "CASA_RATIO": {"casa_deposits": ("casa_deposits", "current"), "total_deposits": ("deposits", "current")},
    "CREDIT_DEPOSIT_RATIO": {"gross_loans": ("loans", "current"), "deposits": ("deposits", "current")},
    "GNPA_RATIO": {"gross_npa": ("gross_npa", "current"), "gross_advances": ("loans", "current")},
    "NNPA_RATIO": {"net_npa": ("net_npa", "current"), "net_advances": ("loans", "current")},
    "PCR": {"accumulated_provisions": ("provisions", "current"), "npa_base": ("gross_npa", "current")},
    "NIM": {"net_interest_income": ("net_interest_income", "current"), "opening_interest_earning_assets": ("interest_earning_assets", "prior"), "closing_interest_earning_assets": ("interest_earning_assets", "current")},
    "CREDIT_COST": {"provisions": ("provisions", "current"), "opening_loans": ("loans", "prior"), "closing_loans": ("loans", "current")},
    "CET1_RATIO": {"cet1_capital": ("cet1_capital", "current"), "risk_weighted_assets": ("risk_weighted_assets", "current")},
    "CRAR": {"regulatory_capital": ("regulatory_capital", "current"), "risk_weighted_assets": ("risk_weighted_assets", "current")},
    "COST_TO_INCOME": {"operating_expenses": ("operating_expenses", "current"), "operating_income": ("operating_income", "current")},
    "PRICE_TO_BOOK": {"market_price": ("market_price", "current"), "book_value_per_share": ("book_value_per_share", "current")},
}


def _institutional_warehouse_facts(company_id: str) -> list[dict[str, Any]]:
    """Adapt approved annual warehouse rows to the AFE fact contract."""
    try:
        from institutional_warehouse import store
        from institutional_warehouse.schema import find_tab

        result = store.fetch(
            "financials_annual",
            filters={"symbol": {"op": "eq", "value": company_id.upper()}},
            limit=5000,
            include_overrides=True,
        )
        tab = find_tab("financials_annual")
    except Exception:
        return []
    if tab is None:
        return []

    excluded = {
        "symbol", "statement_type", "statement_frequency", "fiscal_year",
        "fiscal_end_date", "filing_date", "effective_date", "restated",
        "source", "last_updated", "import_time", "statement_version",
    }
    facts: list[dict[str, Any]] = []
    for row in result.get("rows") or []:
        meta = row.get("_meta") or {}
        available_at = row.get("effective_date") or row.get("filing_date") or row.get("last_updated") or meta.get("updated_at")
        for column in tab.columns:
            metric = column.key
            value = row.get(metric)
            if metric in excluded or not isinstance(value, (int, float)) or isinstance(value, bool):
                continue
            facts.append({
                "fact_id": f"{row.get('row_id')}:{metric}",
                "canonical_metric": metric,
                "value": float(value),
                "unit": column.unit or "INR million",
                "currency": "INR",
                "reporting_period": row.get("fiscal_year"),
                "period_end": row.get("fiscal_end_date"),
                "publication_date": row.get("filing_date"),
                "available_at": available_at,
                "source": row.get("source") or "validated_warehouse",
                "source_id": row.get("row_id"),
                "statement_type": row.get("statement_type"),
                "quality": meta.get("validation") or meta.get("confidence") or "validated",
            })
    return facts


def _period_number(period: str) -> int:
    nums = re.findall(r"\d{2,4}", str(period or ""))
    if not nums:
        return -1
    n = int(nums[-1])
    return 2000 + n if n < 100 else n


def _metric(fact: dict[str, Any]) -> str:
    return str(fact.get("canonical_metric") or fact.get("metric") or "").strip().lower()


def _value(fact: dict[str, Any]) -> float | None:
    value = fact.get("normalized_value")
    if value is None:
        value = fact.get("value", fact.get("reported_value"))
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _source_type(fact: dict[str, Any]) -> str:
    raw = str(fact.get("source_type") or fact.get("source") or "validated_warehouse").lower()
    if "regulatory" in raw or "annual_report" in raw: return "regulatory_filing"
    if "company" in raw or "investor" in raw: return "company_filing"
    if "nse" in raw or "bse" in raw or "exchange" in raw: return "exchange_filing"
    if "rbi" in raw: return "rbi"
    if "research" in raw: return "agi_research_extraction"
    return raw if raw in SOURCE_PRIORITY else "validated_warehouse"


def _to_inr_million(value: float, unit: str | None) -> tuple[float, str]:
    u = str(unit or "INR million").lower().replace("₹", "inr").strip()
    if u in {"percent", "%", "ratio", "multiple", "per_share", "inr/share", "inr per share"}:
        return value, str(unit or u)
    if "crore" in u: return value * 10.0, "INR million"
    if "billion" in u: return value * 1000.0, "INR million"
    if "lakh" in u: return value * 0.1, "INR million"
    if u in {"inr", "rupees", "absolute inr"}: return value / 1_000_000.0, "INR million"
    if "million" in u: return value, "INR million"
    raise ValueError(f"UNIT_MISMATCH:unsupported unit {unit}")


@dataclass
class FinancialDataResolver:
    loader: Callable[[str], dict[str, Any]] | None = None

    def _load(self, company_id: str) -> list[dict[str, Any]]:
        if self.loader is None:
            try:
                from financial_statements_engine.financial_warehouse.production import get_latest
                pack = get_latest(company_id)
            except Exception:
                pack = {}
            facts = list((pack or {}).get("facts") or [])
            return facts or _institutional_warehouse_facts(company_id)
        else:
            pack = self.loader(company_id)
        return list((pack or {}).get("facts") or [])

    def resolve(self, *, company_id: str, calculation_id: str, period: str | None = None, as_of_date: str | None = None, currency: str = "INR", unit: str = "INR million") -> dict[str, Any]:
        calc_id = str(calculation_id or "").upper()
        spec = get_spec(calc_id)
        mapping = CALCULATION_INPUT_MAP.get(calc_id)
        if spec is None or mapping is None:
            return {"status": "CALCULATION_UNAVAILABLE", "calculation_id": calc_id, "company_id": company_id}
        facts = self._load(company_id)
        if not facts:
            return {"status": "DATA_UNAVAILABLE", "calculation_id": calc_id, "company_id": company_id}
        periods = sorted({_period_number(f.get("reporting_period") or f.get("period")) for f in facts if _period_number(f.get("reporting_period") or f.get("period")) > 0})
        current_n = _period_number(period) if period else (periods[-1] if periods else -1)
        prior_n = max((p for p in periods if p < current_n), default=current_n - 1)
        resolved: dict[str, Any] = {}
        for afe_input, (canonical, which) in mapping.items():
            target_n = prior_n if which == "prior" else current_n
            aliases = set(INPUT_METRICS[canonical])
            candidates = []
            future_candidates = []
            for fact in facts:
                if _metric(fact) not in aliases: continue
                if _period_number(fact.get("reporting_period") or fact.get("period")) != target_n: continue
                available = str(fact.get("available_at") or fact.get("publication_date") or fact.get("published_timestamp") or "")
                if as_of_date and available and available[:10] > as_of_date[:10]:
                    future_candidates.append(fact)
                    continue
                value = _value(fact)
                if value is None: continue
                candidates.append((SOURCE_PRIORITY.get(_source_type(fact), 99), fact, value))
            if not candidates:
                if future_candidates:
                    return {"status": "POINT_IN_TIME_VIOLATION", "input": afe_input, "calculation_id": calc_id, "company_id": company_id, "as_of_date": as_of_date, "available_at": sorted(str(f.get("available_at") or f.get("publication_date") or "") for f in future_candidates)[0]}
                return {"status": "DATA_UNAVAILABLE", "missing_input": afe_input, "calculation_id": calc_id, "company_id": company_id, "period": period}
            candidates.sort(key=lambda row: row[0])
            best_priority = candidates[0][0]
            best = [row for row in candidates if row[0] == best_priority]
            normalized = []
            for _, fact, raw in best:
                try:
                    norm, normalized_unit = _to_inr_million(raw, fact.get("unit"))
                except ValueError as exc:
                    return {"status": "UNIT_MISMATCH", "detail": str(exc), "input": afe_input}
                normalized.append((norm, normalized_unit, fact, raw))
            if len({round(row[0], 8) for row in normalized}) > 1:
                return {"status": "CONFLICTING_FINANCIAL_DATA", "input": afe_input, "company_id": company_id, "competing_values": [{"value": row[3], "normalized_value": row[0], "source_id": row[2].get("source_id") or row[2].get("fact_id")} for row in normalized]}
            norm, normalized_unit, fact, raw = normalized[0]
            available_at = fact.get("available_at") or fact.get("publication_date") or fact.get("published_timestamp")
            if as_of_date and available_at:
                try:
                    age_days = (datetime.fromisoformat(as_of_date[:10]) - datetime.fromisoformat(str(available_at)[:10])).days
                    if age_days > 550:
                        return {"status": "STALE_DATA", "input": afe_input, "available_at": available_at, "as_of_date": as_of_date}
                except ValueError:
                    pass
            resolved[afe_input] = {
                "value": norm, "reported_value": raw, "normalized_value": norm,
                "unit": normalized_unit, "currency": fact.get("currency") or currency,
                "period": period or f"FY{current_n}",
                "source_period": fact.get("reporting_period") or fact.get("period"),
                "source_id": fact.get("source_id") or fact.get("fact_id"),
                "source_type": _source_type(fact), "source_date": fact.get("source_date"),
                "publication_date": fact.get("publication_date") or fact.get("published_timestamp"),
                "available_at": available_at,
                "period_end": fact.get("period_end"), "quality": fact.get("quality") or fact.get("data_quality") or "validated",
                "point_in_time_status": "PASS", "company": company_id,
            }
        return {"status": "SUCCESS", "company_id": company_id.upper(), "calculation_id": calc_id, "period": period or f"FY{current_n}", "as_of_date": as_of_date, "inputs": resolved, "source_hierarchy_applied": True}

    def calculate(self, **request: Any) -> dict[str, Any]:
        resolved = self.resolve(**request)
        if resolved.get("status") != "SUCCESS": return resolved
        result = calculate(calculation_id=resolved["calculation_id"], inputs=resolved["inputs"], as_of=resolved.get("as_of_date"))
        return {**result, "company_id": resolved["company_id"], "resolver": {"status": "SUCCESS", "source_hierarchy_applied": True}, "explanation_trace": {"calculation_id": result.get("calculation_id"), "formula": result.get("formula"), "inputs": result.get("input_provenance"), "result": result.get("display_value")}}
