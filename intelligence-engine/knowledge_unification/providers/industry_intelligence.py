"""Industry Intelligence provider — Phase 3.1.5 KUL integration.

Wraps industry_intelligence.production.analyse. Surfaces Industry DNA for
industry / KPI / valuation / economics / competition / regulation questions.
Does not invent knowledge. Does not bypass KUL.
"""

from __future__ import annotations

import time
from typing import Any

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

_II_TYPES = frozenset(
    {
        "industry",
        "unit_economics",
        "business_risk",
        "valuation",
        "concept",
        "comparison",
        "business_model",
    }
)


class IndustryIntelligenceProvider:
    spec = ProviderSpec(
        id="industry_intelligence",
        label="Industry Intelligence Engine",
        coverage="Deterministic Industry DNA — economics, KPIs, valuation, regulation, competition, cycles, risks",
        priority=7,
        supported_question_types=(
            "industry",
            "unit_economics",
            "business_risk",
            "valuation",
            "concept",
            "comparison",
            "business_model",
        ),
        typical_latency_ms=35,
        confidence_ceiling=0.94,
    )

    def health_check(self) -> str:
        try:
            from industry_intelligence.production import health

            h = health()
            return "ok" if h.get("ok") is not False else "degraded"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        types = set(plan.question_types or [])
        if types and not types.intersection(_II_TYPES):
            if types.intersection(
                {"accounting", "financial_statement", "macro", "portfolio", "news", "market"}
            ) and "industry" not in types:
                return empty_result(self.spec.id, t0, "not_industry_shaped")

        try:
            from industry_intelligence.production import analyse

            out = analyse(plan.question) or {}
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)

        try:
            summary = str(out.get("summary") or "").strip()
            # Do not surface the unresolved-industry stub into Ask fusion.
            if not out.get("ok") or not out.get("industry") or summary.lower().startswith(
                "industry intelligence requires a supported industry"
            ):
                return empty_result(self.spec.id, t0, "ii_no_industry_dna")

            modules = list(out.get("modules_used") or [])
            why = [str(w) for w in (out.get("why") or []) if w][:8]
            if out.get("industry"):
                why.insert(0, f"Industry DNA: {out.get('industry_name') or out.get('industry')}.")
            if not why and modules:
                why.append("II modules: " + ", ".join(modules[:6]) + ".")
            if not summary and not why:
                return empty_result(self.spec.id, t0, "ii_empty")

            evidence = [
                {
                    "source": "industry_intelligence.dna",
                    "title": "modules:" + ",".join(modules[:6]) if modules else "ii_analyse",
                    "industry": out.get("industry"),
                }
            ]

            facts: list[dict[str, Any]] = [
                {"field": "modules_used", "value": modules},
                {"field": "industry", "value": out.get("industry")},
                {"field": "industry_name", "value": out.get("industry_name")},
                {"field": "industry_dna_used", "value": bool(out.get("dna"))},
            ]
            val = out.get("valuation") or {}
            if isinstance(val, dict) and val.get("valuation_methods"):
                facts.append({"field": "valuation_methods", "value": val.get("valuation_methods")})
            eco = out.get("economics") or {}
            if isinstance(eco, dict) and eco.get("revenue_drivers"):
                facts.append({"field": "revenue_drivers", "value": eco.get("revenue_drivers")})

            conf = float(out.get("confidence") or 0.75)
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
