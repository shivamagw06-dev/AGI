"""CapIQ Institutional Knowledge Tables provider — full column surface."""

from __future__ import annotations

import re
import time
from typing import Any, Optional

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan


class CapIqIktProvider:
    spec = ProviderSpec(
        id="capiq_ikt",
        label="CapIQ Institutional Knowledge Tables",
        coverage="~5,500 Indian public companies; CapIQ screener columns",
        priority=20,
        supported_question_types=("company", "business_model", "market", "valuation", "industry"),
        typical_latency_ms=15,
        confidence_ceiling=0.9,
    )

    def health_check(self) -> str:
        try:
            from institutional_knowledge_tables.store import list_companies

            n = len(list_companies())
            if n >= 1500:
                return "ok"
            if n > 0:
                return "degraded"
            return "empty"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        try:
            from institutional_knowledge_tables.store import get_table

            # Trust the Knowledge Plan's ticker bind. Re-detecting here undoes
            # pedagogy guards (e.g. "in advance" → ADVANCE / Advance Agrolife).
            ticker = plan.ticker_hint
            if not ticker:
                return empty_result(self.spec.id, t0, "no_ikt_company")

            master = get_table(ticker, "company_master").get("row") or {}
            biz = get_table(ticker, "business_model").get("row") or {}
            market_rows = get_table(ticker, "market_data").get("rows") or []
            fin_rows = get_table(ticker, "financial_statements").get("rows") or []
            competitors = get_table(ticker, "competitors").get("row") or {}
            products = get_table(ticker, "products").get("row") or {}
            market = market_rows[0] if market_rows else {}
            fin = fin_rows[0] if fin_rows else {}

            def _v(row: dict, key: str) -> Any:
                cell = row.get(key)
                return cell.get("value") if isinstance(cell, dict) else None

            company_name = _v(master, "company_name") or ticker
            description = _v(biz, "description") or _v(biz, "description_short")
            if not description and not _v(master, "sector"):
                return empty_result(self.spec.id, t0, "no_usable_ikt_facts")

            why: list[str] = []
            facts: list[dict[str, Any]] = []
            evidence: list[dict[str, Any]] = []

            if description:
                sentences = re.split(r"(?<=[.!?])\s+", str(description).strip())
                summary = " ".join(sentences[:3])
                evidence.append(
                    {
                        "source": "institutional_knowledge_tables.business_model",
                        "title": f"{ticker}.description",
                        "effective_date": (biz.get("description") or {}).get("effective_date")
                        if isinstance(biz.get("description"), dict)
                        else None,
                    }
                )
            else:
                summary = f"{company_name} operates in {_v(master, 'industry') or _v(master, 'sector') or 'n/a'}."

            sector, industry = _v(master, "sector"), _v(master, "industry")
            if sector or industry:
                why.append(f"Sector: {sector or 'n/a'}; Industry: {industry or 'n/a'}.")
                facts.append({"field": "sector", "value": sector, "table": "company_master"})

            if _v(master, "company_type") or _v(master, "country"):
                why.append(
                    f"{_v(master, 'company_type') or 'Company'} based in {_v(master, 'country') or 'n/a'}."
                )

            if _v(master, "parent_company"):
                why.append(f"Ultimate parent: {_v(master, 'parent_company')}.")
                facts.append({"field": "parent_company", "value": _v(master, "parent_company")})

            if _v(master, "website"):
                facts.append({"field": "website", "value": _v(master, "website")})

            mc, ev = _v(market, "market_cap"), _v(market, "enterprise_value")
            if mc:
                why.append(f"Market Cap ({market.get('period')}): ${mc}mm USD (CapIQ).")
                facts.append({"field": "market_cap", "value": mc, "period": market.get("period")})
            if ev:
                why.append(f"Enterprise Value ({market.get('period')}): ${ev}mm USD (CapIQ).")
                facts.append({"field": "enterprise_value", "value": ev})

            # Returns / price / earnings — previously stored but unused by Ask
            close = _v(market, "close")
            if close is not None:
                facts.append({"field": "close", "value": close, "period": market.get("period")})
            for rk in (
                "returns_1d",
                "returns_1w",
                "returns_1m",
                "returns_3m",
                "returns_6m",
                "returns_ytd",
                "returns_1y",
                "returns_3y",
                "returns_5y",
            ):
                rv = _v(market, rk)
                if rv is not None:
                    facts.append({"field": rk, "value": rv, "period": market.get("period")})
            for ek in ("next_earnings_date_announced", "next_earnings_date_expected"):
                evd = _v(market, ek)
                if evd:
                    why.append(f"{ek.replace('_', ' ').title()}: {evd}.")
                    facts.append({"field": ek, "value": evd})

            rev, ebitda = _v(fin, "revenue"), _v(fin, "ebitda")
            if rev is not None:
                why.append(f"Total Revenue ({fin.get('period')}): ${rev}mm USD (LTM).")
                facts.append({"field": "revenue", "value": rev, "period": fin.get("period")})
            if ebitda is not None:
                why.append(f"EBITDA ({fin.get('period')}): ${ebitda}mm USD (LTM).")
                facts.append({"field": "ebitda", "value": ebitda, "period": fin.get("period")})

            peer = _v(competitors, "peer")
            if peer:
                names = [p.strip().split(" (")[0] for p in str(peer).split(";") if p.strip()][:5]
                if names:
                    why.append(f"Named competitors: {', '.join(names)}.")
                    facts.append({"field": "competitors", "value": names})

            product = _v(products, "product")
            if product:
                facts.append({"field": "products", "value": str(product)[:500]})
                why.append(f"Products (CapIQ): {str(product)[:180]}.")

            investors = _v(biz, "investors")
            if investors:
                facts.append({"field": "investors", "value": str(investors)[:400]})

            return timed_result(
                self.spec.id,
                ok=True,
                empty=False,
                confidence=0.88,
                t0=t0,
                summary=summary,
                why=why,
                evidence=evidence
                or [{"source": "institutional_knowledge_tables", "title": f"company_master:{ticker}"}],
                facts=facts,
                raw={
                    "ticker": ticker,
                    "company_name": company_name,
                    "identity": {
                        "ticker": ticker,
                        "name": company_name,
                        "sector": sector,
                        "industry": industry,
                        "country": _v(master, "country"),
                        "company_type": _v(master, "company_type"),
                        "website": _v(master, "website"),
                        "parent_company": _v(master, "parent_company"),
                    },
                    "market": {k: _v(market, k) for k in ("close", "market_cap", "enterprise_value", "volume") if _v(market, k) is not None},
                    "financials": {"revenue": rev, "ebitda": ebitda, "period": fin.get("period")},
                    "products": product,
                    "competitors": peer,
                },
            )
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)
