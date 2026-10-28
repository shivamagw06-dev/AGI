"""Valuation Terminal provider — live market multiples against the industry.

Where `valuation_consensus` carries what the sell side expects, this carries
what the market is actually paying today: the sector-appropriate multiple, the
industry median it is measured against, and the returns that justify or
undermine the gap.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

_LABELS = {
    "pe": "P/E",
    "forward_pe": "forward P/E",
    "pb": "P/B",
    "ps": "P/S",
    "ev_ebitda": "EV/EBITDA",
    "ev_sales": "EV/Sales",
    "dividend_yield": "dividend yield",
}


def _num(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


class ValuationTerminalProvider:
    spec = ProviderSpec(
        id="valuation_terminal",
        label="Valuation Terminal (market multiples)",
        coverage="~1,180 Indian listed companies; sector-lensed market multiples and industry medians",
        priority=18,
        supported_question_types=("valuation", "company", "market", "industry", "investment"),
        typical_latency_ms=25,
        confidence_ceiling=0.88,
    )

    def health_check(self) -> str:
        try:
            from valuation_terminal.store import all_rows

            n = len(all_rows() or {})
            if n >= 500:
                return "ok"
            if n > 0:
                return "degraded"
            return "empty"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        try:
            from valuation_terminal.sector_lens import lens_for
            from valuation_terminal.store import all_rows

            ticker = plan.ticker_hint
            if not ticker:
                return empty_result(self.spec.id, t0, "no_valuation_company")

            rows = all_rows() or {}
            row = rows.get(str(ticker).upper())
            if not row:
                return empty_result(self.spec.id, t0, "not_in_valuation_terminal")

            name = row.get("company_name") or ticker
            industry = row.get("primary_industry")
            sector = row.get("primary_sector")
            # Prefer VPAE policy; fall back to sector_lens baseline.
            policy = None
            try:
                from valuation_policy import evaluate as vpae_evaluate

                policy = vpae_evaluate(str(ticker).upper())
            except Exception:
                policy = None
            if policy and policy.get("ok"):
                metric = policy.get("primary_metric") or "pe"
                label = _LABELS.get(metric, policy.get("primary_model") or metric.upper())
                lens = {
                    "primary_metric": metric,
                    "rationale": policy.get("reason"),
                    "status": policy.get("status"),
                    "confidence": policy.get("confidence"),
                }
            else:
                lens = lens_for(row.get("industry_dna"))
                metric = lens.get("primary_metric") or "pe"
                label = _LABELS.get(metric, metric.upper())

            peers = [
                r for r in rows.values()
                if r.get("primary_industry") == industry and _num(r.get(metric)) is not None
            ]
            values = sorted(_num(r.get(metric)) for r in peers)
            median = None
            if values:
                mid = len(values) // 2
                median = values[mid] if len(values) % 2 else round((values[mid - 1] + values[mid]) / 2, 2)

            value = _num(row.get(metric))
            roe = _num(row.get("roe"))
            roe_values = sorted(
                v for v in (_num(r.get("roe")) for r in peers) if v is not None
            )
            roe_median = None
            if roe_values:
                mid = len(roe_values) // 2
                roe_median = (
                    roe_values[mid] if len(roe_values) % 2
                    else round((roe_values[mid - 1] + roe_values[mid]) / 2, 2)
                )

            if value is None:
                return empty_result(self.spec.id, t0, "no_primary_metric")

            why: list[str] = []
            facts: list[dict[str, Any]] = []
            if policy and policy.get("ok"):
                why.append(
                    f"Valuation policy: primary model {policy.get('primary_model')} "
                    f"({policy.get('status')}, confidence {policy.get('confidence')}). "
                    f"{policy.get('reason')}"
                )
                facts.append({
                    "field": "valuation_policy_primary_model",
                    "value": policy.get("primary_model"),
                    "status": policy.get("status"),
                })
            gap = None
            if median:
                gap = round(((value / median) - 1.0) * 100.0, 1)
                stance = "a premium to" if gap > 0 else "a discount to"
                summary = (
                    f"{name} trades at {value} on {label} against an {industry} median of "
                    f"{median} — {stance} the peer group of {abs(gap)}% across {len(peers)} companies."
                )
                why.append(f"{label} is the primary lens for {industry}: {lens.get('rationale') or 'sector-appropriate multiple'}.")
                facts.append({"field": f"{metric}_industry_median", "value": median, "peers": len(peers)})
                facts.append({"field": "gap_to_industry_pct", "value": gap})
            else:
                summary = f"{name} trades at {value} on {label}; the {industry} peer set is too thin for a median."

            facts.append({"field": metric, "value": value, "source": "yahoo_finance"})

            if roe is not None:
                facts.append({"field": "roe", "value": roe})
                if roe_median is not None:
                    verdict = "above" if roe > roe_median else "below"
                    why.append(
                        f"Return on equity of {roe}% is {verdict} the industry median of {roe_median}%"
                        + (
                            " — the discount may be deserved."
                            if gap is not None and gap < 0 and roe < roe_median
                            else " — profitability supports the rating."
                            if gap is not None and gap > 0 and roe > roe_median
                            else "."
                        )
                    )

            for field in ("pe", "forward_pe", "pb", "ev_ebitda", "ev_sales", "profit_margin",
                          "debt_to_equity", "dividend_yield", "market_cap", "price"):
                v = _num(row.get(field))
                if v is not None and field != metric:
                    facts.append({"field": field, "value": v, "source": "yahoo_finance"})

            margin = _num(row.get("profit_margin"))
            debt = _num(row.get("debt_to_equity"))
            if margin is not None:
                why.append(f"Net margin of {margin}%.")
            if debt is not None:
                why.append(f"Debt to equity of {debt}.")
            why.append(
                "Market multiples are the price the market pays today; they describe expectation, "
                "not value."
            )

            return timed_result(
                self.spec.id,
                ok=True,
                empty=False,
                confidence=0.85,
                t0=t0,
                summary=summary,
                why=why,
                evidence=[
                    {
                        "source": "valuation_terminal",
                        "title": f"market_multiples:{ticker}",
                        "effective_date": row.get("updated_at") or row.get("as_of"),
                    }
                ],
                facts=facts,
                raw={
                    "ticker": ticker,
                    "company_name": name,
                    "sector": sector,
                    "industry": industry,
                    "primary_metric": metric,
                    "value": value,
                    "industry_median": median,
                    "gap_pct": gap,
                    "roe": roe,
                    "industry_median_roe": roe_median,
                    "peers": len(peers),
                },
            )
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)
