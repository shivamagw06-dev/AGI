"""KUL provider — Valuation Policy / Applicability Engine (VPAE)."""

from __future__ import annotations

import time

from knowledge_unification.providers.base import empty_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

_MARKERS = (
    "valuation",
    "how should",
    "primary metric",
    "primary model",
    "p/e",
    "pe ",
    "expensive",
    "cheap",
    "premium",
    "discount",
    "analyze",
    "compare",
    "metric",
    "industry",
    "bank",
    "institutional",
)


class ValuationPolicyEngineProvider:
    spec = ProviderSpec(
        id="valuation_policy_engine",
        label="Valuation Policy Engine",
        coverage=(
            "Decides which valuation metrics apply for a company / industry DNA — "
            "gates UVE/HVIE displays; never invents multiples"
        ),
        priority=8,
        supported_question_types=(
            "valuation", "company", "investment", "comparison", "attribution",
        ),
        typical_latency_ms=80,
        confidence_ceiling=0.92,
    )

    def health_check(self) -> str:
        try:
            from valuation_policy.engine import evaluate  # noqa: F401

            return "ok"
        except Exception:
            return "degraded"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        question = (plan.question or "").strip()
        qlow = question.lower()
        if not any(m in qlow for m in _MARKERS):
            return empty_result(self.spec.id, t0, "not_a_vpae_question")
        ticker = (plan.ticker_hint or "").strip().upper()
        if not ticker:
            return empty_result(self.spec.id, t0, "no_company_for_vpae")
        try:
            from valuation_policy.ask import answer_for
            from valuation_policy.engine import evaluate

            ask_pack = answer_for(ticker, question)
            policy = evaluate(ticker) if not ask_pack.get("ok") else ask_pack
        except Exception as exc:
            return empty_result(self.spec.id, t0, str(exc)[:160])
        use = ask_pack if ask_pack.get("ok") else policy
        if not use.get("ok") and use.get("error"):
            return empty_result(self.spec.id, t0, str(use.get("error") or "vpae_empty"))
        summary = use.get("answer") or use.get("prose") or (
            f"{ticker} primary valuation model: {use.get('primary_model') or use.get('primary_metric')} "
            f"(status {use.get('status')}). {use.get('reason') or ''}"
        )
        why = []
        if use.get("primary_model") or use.get("primary_metric"):
            why.append(f"Primary model: {use.get('primary_model') or use.get('primary_metric')}")
        if use.get("reason"):
            why.append(str(use.get("reason")))
        for m in (use.get("supporting_models") or use.get("supporting_metrics") or [])[:3]:
            why.append(f"Supporting: {m}")
        for m in (use.get("hidden_metrics") or [])[:2]:
            why.append(f"Suppressed: {m}")
        return timed_result(
            self.spec.id,
            ok=True,
            empty=False,
            confidence=0.85,
            t0=t0,
            summary=str(summary)[:1000],
            why=why[:8],
            evidence=[{"source": "valuation_policy_engine", "title": f"vpae:{ticker}"}],
            facts=[
                {"field": "primary_model", "value": use.get("primary_model") or use.get("primary_metric"), "source": "vpae"},
                {"field": "status", "value": use.get("status"), "source": "vpae"},
            ],
            raw={"engine": "valuation_policy_engine", "symbol": ticker},
        )
