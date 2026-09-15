"""Financial Statement Warehouse provider — parsed statements, not pedagogy.

Reads the FSE warehouse when facts exist. Falls back to CapIQ IKT LTM figures
so Ask still has numerical financial evidence while the warehouse is filling.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan


def _cell(row: dict, key: str) -> Any:
    cell = row.get(key)
    return cell.get("value") if isinstance(cell, dict) else cell


class FinancialStatementWarehouseProvider:
    spec = ProviderSpec(
        id="financial_statement_warehouse",
        label="Financial Statement Warehouse",
        coverage="Parsed filings + CapIQ LTM financials for covered Indian companies",
        priority=21,
        supported_question_types=("financials", "valuation", "company", "accounting", "investment"),
        typical_latency_ms=40,
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
            ticker = plan.ticker_hint
            if not ticker:
                return empty_result(self.spec.id, t0, "no_financials_company")

            warehouse_facts = self._warehouse(ticker)
            ikt_facts = self._ikt(ticker)

            if not warehouse_facts and not ikt_facts:
                return empty_result(self.spec.id, t0, "no_financial_facts")

            why: list[str] = []
            facts: list[dict[str, Any]] = []
            evidence: list[dict[str, Any]] = []

            if warehouse_facts:
                facts.extend(warehouse_facts)
                why.append(
                    f"Financial Statement Warehouse returned {len(warehouse_facts)} parsed facts for {ticker}."
                )
                evidence.append(
                    {"source": "financial_statements_engine.warehouse", "title": f"latest:{ticker}"}
                )

            if ikt_facts:
                facts.extend(ikt_facts)
                period = next((f.get("period") for f in ikt_facts if f.get("period")), "LTM")
                bits = [
                    f"{f['field']}={f['value']}"
                    for f in ikt_facts
                    if f.get("field") in {"revenue", "ebitda", "net_income", "total_assets", "total_debt"}
                ]
                if bits:
                    why.append(f"CapIQ financials ({period}): " + ", ".join(bits[:4]) + ".")
                evidence.append(
                    {"source": "institutional_knowledge_tables.financial_statements", "title": f"{ticker}:{period}"}
                )

            # Prefer a warehouse-led summary when available; otherwise CapIQ LTM.
            if warehouse_facts:
                summary = (
                    f"{ticker} has {len(warehouse_facts)} warehouse facts available for historical "
                    "statement analysis (revenue, margins, debt, cash and related ratios)."
                )
                confidence = 0.88
            else:
                rev = next((f["value"] for f in ikt_facts if f.get("field") == "revenue"), None)
                ebitda = next((f["value"] for f in ikt_facts if f.get("field") == "ebitda"), None)
                period = next((f.get("period") for f in ikt_facts if f.get("period")), "LTM")
                parts = []
                if rev is not None:
                    parts.append(f"revenue ${rev}mm")
                if ebitda is not None:
                    parts.append(f"EBITDA ${ebitda}mm")
                summary = (
                    f"{ticker} CapIQ {period} financials: " + ", ".join(parts) + "."
                    if parts
                    else f"{ticker} CapIQ financial statement row is present."
                )
                confidence = 0.8
                why.append(
                    "Parsed warehouse facts are not yet loaded for this ticker; CapIQ LTM figures are used instead."
                )

            return timed_result(
                self.spec.id,
                ok=True,
                empty=False,
                confidence=confidence,
                t0=t0,
                summary=summary,
                why=why,
                evidence=evidence,
                facts=facts,
                raw={"ticker": ticker, "warehouse_n": len(warehouse_facts), "ikt_n": len(ikt_facts)},
            )
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)

    def _warehouse(self, ticker: str) -> list[dict[str, Any]]:
        try:
            from financial_statements_engine.financial_warehouse.production import get_latest

            data = get_latest(ticker) or {}
            rows = data.get("facts") or []
            out: list[dict[str, Any]] = []
            for row in rows[:40]:
                if not isinstance(row, dict):
                    continue
                field = row.get("metric") or row.get("field") or row.get("name")
                value = row.get("value")
                if field is None or value is None:
                    continue
                out.append(
                    {
                        "field": str(field),
                        "value": value,
                        "period": row.get("period"),
                        "source": "financial_statement_warehouse",
                    }
                )
            return out
        except Exception:
            return []

    def _ikt(self, ticker: str) -> list[dict[str, Any]]:
        try:
            from institutional_knowledge_tables.store import get_table

            pack = get_table(ticker, "financial_statements") or {}
            rows = pack.get("rows") or []
            if not rows:
                return []
            row = rows[0]
            out: list[dict[str, Any]] = []
            period = row.get("period")
            for key in ("revenue", "ebitda", "net_income", "total_assets", "total_debt", "cash", "capex"):
                value = _cell(row, key)
                if value is not None:
                    out.append(
                        {
                            "field": key,
                            "value": value,
                            "period": period,
                            "source": "capiq_ikt",
                        }
                    )
            return out
        except Exception:
            return []
