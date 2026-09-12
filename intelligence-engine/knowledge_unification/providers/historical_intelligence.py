"""Historical Intelligence provider — the route by which Ask reasons over history.

Other providers answer "what is true now". This one answers "how did it get
here", and it is the only provider that declines on purpose: when the warehouse
does not hold the period asked about, it returns the coverage statement rather
than a current-state answer dressed as a historical one.

That distinction is the whole point. Before this existed, "when was Axis Bank
cheapest on price to book" returned today's multiple — a correct number
presented as an answer to a question it did not address.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

_CONFIDENCE = {"strong": 0.9, "moderate": 0.7, "weak": 0.5, "none": 0.3}


class HistoricalIntelligenceProvider:
    spec = ProviderSpec(
        id="historical_intelligence",
        label="Historical Intelligence (coverage-aware historical reasoning)",
        coverage=(
            "Trend, valuation history, corporate event timelines and cross-company comparison "
            "over the warehouse's observed windows, with the observation span stated on every "
            "answer"
        ),
        priority=6,
        supported_question_types=(
            "historical", "company", "valuation", "financial", "investment", "market",
        ),
        typical_latency_ms=120,
        confidence_ceiling=0.9,
    )

    def health_check(self) -> str:
        try:
            from historical_intelligence.production import health

            report = health()
            if report.get("status") == "ok":
                return "ok"
            return "empty"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        try:
            from historical_intelligence import intent
            from historical_intelligence.production import ask

            question = plan.question or ""
            if not intent.is_historical(question):
                return empty_result(self.spec.id, t0, "not_a_historical_question")

            ticker = (plan.ticker_hint or "").strip().upper()
            if not ticker:
                return empty_result(self.spec.id, t0, "no_company_for_history")

            answer = ask(question, symbol=ticker)
            if not answer.get("ok"):
                return empty_result(self.spec.id, t0,
                                    str(answer.get("error") or "no_historical_answer"))

            closing = answer.get("explain") or {}
            coverage = answer.get("coverage") or {}
            guard = answer.get("guard") or {}
            window = answer.get("observation_window")

            facts: list[dict[str, Any]] = [
                {
                    "field": "observation_window",
                    "value": window,
                    "source": f"warehouse.{coverage.get('tab')}",
                    "metric": coverage.get("metric"),
                    "observations": coverage.get("observations"),
                },
            ]
            for key in ("cagr_pct", "percentile", "median", "consistency_pct",
                        "premium_to_own_median_pct", "change_pct"):
                value = (answer.get("detail") or {}).get(key)
                if value is not None:
                    facts.append({"field": key, "value": value,
                                  "source": "historical_intelligence",
                                  "window": window})

            why = list(answer.get("conclusions") or [])
            if closing.get("why_it_mattered"):
                why.append(closing["why_it_mattered"])
            for limit in closing.get("limits") or []:
                why.append(limit)

            # A coverage-limited reply is a successful answer, not an empty one: the
            # useful content is the boundary itself.
            coverage_limited = bool(answer.get("coverage_limited"))
            confidence = _CONFIDENCE.get(str(answer.get("confidence")), 0.5)
            if not guard.get("may_conclude", True):
                confidence = min(confidence, 0.45)

            return timed_result(
                self.spec.id,
                ok=True,
                empty=False,
                confidence=min(confidence, self.spec.confidence_ceiling),
                t0=t0,
                summary=answer.get("answer") or answer.get("finding") or "",
                why=why,
                evidence=[
                    {
                        "source": "historical_intelligence",
                        "title": f"{answer.get('module')}:{ticker}:{coverage.get('metric')}",
                        "effective_date": coverage.get("latest"),
                        "observation_window": window,
                    }
                ],
                facts=facts,
                raw={
                    "module": answer.get("module"),
                    "metric": answer.get("metric"),
                    "observation_window": window,
                    "coverage_limited": coverage_limited,
                    "guard_verdict": guard.get("verdict"),
                    "confidence": answer.get("confidence"),
                    "conclusions": answer.get("conclusions"),
                    "plan": answer.get("plan"),
                },
            )
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)
