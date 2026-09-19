"""Institutional Data Warehouse provider.

The warehouse is the validated, versioned, audited copy of everything the
collectors gather. Where other providers each read their own store, this one
reads the single table the admin desk curates — so what Ask says is what the
warehouse says, and both can be traced to the same row.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan


def _num(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _fact(field: str, value: Any, source: str = "institutional_warehouse", **extra: Any) -> dict[str, Any]:
    return {"field": field, "value": value, "source": source, **extra}


class InstitutionalWarehouseProvider:
    spec = ProviderSpec(
        id="institutional_warehouse",
        label="Institutional Data Warehouse (validated single source of truth)",
        coverage=(
            "Company master, daily market history, annual and quarterly statements, calculated "
            "ratios, valuation snapshots, consensus, ownership, corporate actions and factor "
            "scores — versioned, validated and audited"
        ),
        priority=8,
        supported_question_types=(
            "company", "valuation", "financial", "investment", "market", "industry", "screen",
        ),
        typical_latency_ms=35,
        confidence_ceiling=0.92,
    )

    def health_check(self) -> str:
        try:
            from institutional_warehouse.production import health

            report = health()
            rows = int(report.get("total_rows") or 0)
            if rows >= 1000:
                return "ok"
            if rows > 0:
                return "degraded"
            return "empty"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        try:
            from institutional_warehouse.production import read_company

            ticker = (plan.ticker_hint or "").strip().upper()
            if not ticker:
                return empty_result(self.spec.id, t0, "no_warehouse_company")

            record = read_company(ticker)
            if not record.get("ok") or not record.get("master"):
                return empty_result(self.spec.id, t0, "not_in_warehouse")

            master = record["master"]
            valuation = record.get("valuation") or {}
            ratios = record.get("ratios") or {}
            consensus = record.get("consensus") or {}
            factors = record.get("factors") or {}
            price = record.get("latest_price") or {}
            annual = record.get("latest_annual") or {}
            ownership = record.get("ownership") or {}

            name = master.get("company_name") or ticker
            sector = master.get("sector")
            industry = master.get("industry")

            facts: list[dict[str, Any]] = []
            why: list[str] = []

            for key, field in (
                ("cmp", "price"), ("market_cap", "market_cap"), ("pe", "pe"), ("pb", "pb"),
                ("ev_ebitda", "ev_ebitda"), ("ev_sales", "ev_sales"), ("dividend_yield", "dividend_yield"),
                ("sector_median", "sector_median_pe"), ("percentile", "sector_percentile"),
                ("relative_valuation_score", "relative_valuation_score"), ("upside", "consensus_upside"),
            ):
                value = _num(valuation.get(key))
                if value is not None:
                    facts.append(_fact(field, value, "warehouse.historical_valuation"))

            for key in ("roe", "roce", "net_margin", "ebitda_margin", "debt_equity",
                        "current_ratio", "interest_coverage", "fcf_margin"):
                value = _num(ratios.get(key))
                if value is not None:
                    facts.append(_fact(key, value, "warehouse.historical_ratios",
                                       period=ratios.get("period")))

            for key in ("revenue", "ebitda", "pat", "eps", "equity", "debt", "free_cash_flow"):
                value = _num(annual.get(key))
                if value is not None:
                    facts.append(_fact(key, value, "warehouse.financials_annual",
                                       period=annual.get("fiscal_year")))

            for key in ("target_price", "analyst_count", "target_dispersion"):
                value = _num(consensus.get(key))
                if value is not None:
                    facts.append(_fact(key, value, "warehouse.consensus",
                                       as_of=consensus.get("consensus_date")))

            for key in ("promoter_holding", "institutional_holding", "fii", "dii"):
                value = _num(ownership.get(key))
                if value is not None:
                    facts.append(_fact(key, value, "warehouse.ownership", as_of=ownership.get("as_of")))

            for key in ("value_score", "quality_score", "growth_score", "momentum_score",
                        "opportunity_score", "strategy_agreement"):
                value = _num(factors.get(key))
                if value is not None:
                    facts.append(_fact(key, value, "warehouse.hedge_fund_factors"))

            if not facts:
                return empty_result(self.spec.id, t0, "warehouse_row_empty")

            pieces = [f"{name} ({ticker})"]
            if industry:
                pieces.append(f"in {industry}")
            elif sector:
                pieces.append(f"in {sector}")
            headline = " ".join(pieces)

            pe = _num(valuation.get("pe"))
            median = _num(valuation.get("sector_median"))
            if pe is not None and median:
                gap = round(((pe / median) - 1.0) * 100.0, 1)
                stance = "a premium of" if gap > 0 else "a discount of"
                headline += (
                    f" trades on {pe} P/E against a sector median of {median} — {stance} {abs(gap)}%."
                )
                why.append(
                    f"The comparison is drawn inside the warehouse from {sector or 'the sector'} "
                    "peers priced on the same snapshot date."
                )
            elif pe is not None:
                headline += f" trades on {pe} P/E."
            elif _num(price.get("close")) is not None:
                headline += f" last traded at {price.get('close')}."

            roe = _num(ratios.get("roe"))
            if roe is not None:
                headline += f" Return on equity is {round(roe, 1)}%."
                why.append(
                    f"Ratios are calculated server-side from the {ratios.get('period') or 'latest'} "
                    "statement, not copied from a vendor field."
                )

            upside = _num(valuation.get("upside"))
            if upside is not None and consensus.get("target_price"):
                headline += (
                    f" The consensus target of {consensus['target_price']} implies "
                    f"{round(upside, 1)}% against the current price."
                )

            coverage = record.get("coverage") or {}
            covered = [k for k, v in coverage.items() if v]
            why.append(
                "Every figure here is a warehouse row with provenance, a version history and an "
                "audit trail: "
                + ", ".join(sorted(covered)[:6])
                + (" and more." if len(covered) > 6 else ".")
            )

            overrides = (master.get("_meta") or {}).get("overridden") or []
            if overrides:
                why.append(
                    "Some fields carry a reviewed admin override: " + ", ".join(overrides) + "."
                )

            evidence = [
                {
                    "source": "institutional_warehouse",
                    "title": f"warehouse_company:{ticker}",
                    "effective_date": (valuation.get("date") or price.get("date")
                                       or master.get("last_updated")),
                }
            ]

            confidence = 0.72
            if pe is not None and roe is not None:
                confidence = 0.88
            elif pe is not None or roe is not None:
                confidence = 0.8

            return timed_result(
                self.spec.id,
                ok=True,
                empty=False,
                confidence=min(confidence, self.spec.confidence_ceiling),
                t0=t0,
                summary=headline,
                why=why,
                evidence=evidence,
                facts=facts,
                raw={
                    "ticker": ticker,
                    "company_name": name,
                    "sector": sector,
                    "industry": industry,
                    "valuation": valuation,
                    "ratios": ratios,
                    "consensus": consensus,
                    "factors": factors,
                    "latest_annual": annual,
                    "ownership": ownership,
                    "coverage": coverage,
                },
            )
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)
