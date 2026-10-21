"""Financial Statement Intelligence (Phase 2) provider."""

from __future__ import annotations

import time

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan


class FinancialStatementIntelligenceProvider:
    spec = ProviderSpec(
        id="financial_statement_intelligence",
        label="Financial Statement Intelligence",
        coverage="Deterministic FSA / statement reading / ratio interpretation",
        priority=7,
        supported_question_types=("financial_statement", "accounting", "concept"),
        typical_latency_ms=10,
        confidence_ceiling=0.95,
    )

    def health_check(self) -> str:
        try:
            from financial_statement_intelligence.production import health

            h = health()
            return "ok" if h.get("ok") is not False else "degraded"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        # Only fire for statement-shaped questions; foundations provider
        # covers pure accounting pedagogy via the same router.
        types = set(plan.question_types)
        if not types.intersection({"financial_statement", "accounting", "concept"}):
            return empty_result(self.spec.id, t0, "not_fsa_question")
        try:
            from app.ui.financial_router import route as financial_router_route

            hit = financial_router_route(plan.question)
            if not hit:
                return empty_result(self.spec.id, t0, "fsi_miss")
            engine = str(hit.get("engine") or hit.get("financial_engine") or "").lower()
            # Accept foundations-shaped FSA answers through this provider when
            # the router classified the question as statement analysis but
            # answered via foundations helpers (common for interpret cases).
            summary = hit.get("summary") or hit.get("executive") or ""
            why = list(hit.get("why") or [])
            if not summary and not why:
                return empty_result(self.spec.id, t0, "fsi_empty")
            # Prefer claiming FSI when question is FSA-shaped; otherwise only
            # when router named statement intelligence.
            is_fsa = "financial_statement" in types or "statement" in engine
            if not is_fsa and "foundation" in engine:
                return empty_result(self.spec.id, t0, "router_chose_foundations")
            return timed_result(
                self.spec.id,
                ok=True,
                empty=False,
                confidence=0.93,
                t0=t0,
                summary=str(summary)[:800],
                why=why[:8],
                evidence=list(
                    hit.get("evidence")
                    or [{"source": "financial_statement_intelligence", "title": engine or "fsa"}]
                ),
                facts=[
                    {"field": "engine", "value": engine or "financial_statement_intelligence"},
                    {"field": "key", "value": hit.get("key")},
                ],
                raw=hit if isinstance(hit, dict) else {},
            )
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)
