"""Business Intelligence Foundation provider — Phase 3.0.5 KUL integration.

Wraps business_intelligence.foundation.analyse. Does not invent knowledge;
surfaces structured business-model / moat / unit-economics / comparison output
for business-shaped questions before generic retrieval.
"""

from __future__ import annotations

import time
from typing import Any

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

_BUSINESS_TYPES = frozenset(
    {
        "business_model",
        "industry",
        "company",
        "moat",
        "unit_economics",
        "comparison",
        "business_risk",
    }
)


class BusinessIntelligenceProvider:
    spec = ProviderSpec(
        id="business_intelligence",
        label="Business Intelligence Foundation",
        coverage="Deterministic business model, moat, unit economics, industry, comparison",
        priority=8,
        supported_question_types=(
            "business_model",
            "industry",
            "company",
            "moat",
            "unit_economics",
            "comparison",
            "business_risk",
        ),
        typical_latency_ms=40,
        confidence_ceiling=0.92,
    )

    def health_check(self) -> str:
        try:
            from business_intelligence.foundation.production import health

            h = health()
            return "ok" if h.get("ok") is not False else "degraded"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        types = set(plan.question_types or [])
        # Skip pure finance/accounting/valuation pedagogy unless also business-shaped.
        if types and not types.intersection(_BUSINESS_TYPES):
            if types.intersection(
                {"concept", "accounting", "financial_statement", "valuation", "macro", "portfolio"}
            ) and "company" not in types:
                return empty_result(self.spec.id, t0, "not_business_shaped")

        try:
            from business_intelligence.foundation.production import analyse

            out = analyse(plan.question, ticker=plan.ticker_hint) or {}
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)

        try:
            if not out.get("ok") and not out.get("summary"):
                return empty_result(self.spec.id, t0, "bi_not_ok")

            summary = str(out.get("summary") or "").strip()
            modules = list(out.get("modules_used") or [])
            why = [str(w) for w in (out.get("why") or []) if w][:8]
            if not why and modules:
                why.append("BI modules: " + ", ".join(modules[:6]) + ".")
            if not summary and not why:
                return empty_result(self.spec.id, t0, "bi_empty")

            evidence = list(out.get("evidence") or [])
            if not evidence:
                evidence = [
                    {
                        "source": "business_intelligence.foundation",
                        "title": "modules:" + ",".join(modules[:6]) if modules else "bi_analyse",
                    }
                ]

            facts: list[dict[str, Any]] = [
                {"field": "modules_used", "value": modules},
                {"field": "industry", "value": out.get("industry")},
                {"field": "ticker", "value": out.get("ticker")},
            ]
            bm = out.get("business_model") or {}
            if isinstance(bm, dict) and bm.get("business_type"):
                facts.append({"field": "business_type", "value": bm.get("business_type")})
            if isinstance(bm, dict) and bm.get("how_it_makes_money"):
                facts.append(
                    {"field": "how_it_makes_money", "value": bm.get("how_it_makes_money")}
                )

            conf = float(out.get("confidence") or 0.7)
            conf = min(conf, self.spec.confidence_ceiling)

            return timed_result(
                self.spec.id,
                ok=True,
                empty=False,
                confidence=conf,
                t0=t0,
                summary=summary[:900],
                why=why,
                evidence=evidence,
                facts=[f for f in facts if f.get("value") is not None],
                raw=out,
            )
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)
