"""Institutional Knowledge Layer (IKL) memory provider."""

from __future__ import annotations

import time

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan


class IklProvider:
    spec = ProviderSpec(
        id="ikl",
        label="Institutional Knowledge Layer",
        coverage="Persistent company/industry/macro memory consulted before retrieval",
        priority=15,
        supported_question_types=("company", "business_model", "industry", "macro", "news"),
        typical_latency_ms=40,
        confidence_ceiling=0.85,
    )

    def health_check(self) -> str:
        try:
            from institutional_knowledge_layer.production import health

            h = health()
            return "ok" if h.get("ok") is not False else "degraded"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        try:
            from institutional_knowledge_layer.production import ask_consult

            out = ask_consult(
                question=plan.question,
                ticker=plan.ticker_hint,
                intent=",".join(plan.question_types),
            ) or {}
            hints = list(out.get("answer_hints") or out.get("hints") or [])
            layers = list(out.get("layers_hit") or out.get("layers") or [])
            if not hints and not layers:
                return empty_result(self.spec.id, t0, "no_ikl_memory")
            return timed_result(
                self.spec.id,
                ok=True,
                empty=False,
                confidence=float(out.get("confidence") or 0.7),
                t0=t0,
                summary=hints[0] if hints else "IKL memory consulted.",
                why=hints[:6],
                evidence=[{"source": "institutional_knowledge_layer", "title": f"layers:{','.join(map(str, layers)) or 'memory'}"}],
                facts=[{"field": "ikl_layers", "value": layers}],
                raw=out if isinstance(out, dict) else {},
            )
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)
