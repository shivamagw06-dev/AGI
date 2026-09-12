"""Portfolio Intelligence provider — Phase 3.3.5 KUL integration.

Wraps portfolio_intelligence.foundation.production.analyse. Surfaces construction,
exposures, risk, scenarios, and monitoring — without BUY/SELL or trade advice.
Does not bypass KUL.
"""

from __future__ import annotations

import time
from typing import Any

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

_PI_TYPES = frozenset({"portfolio", "company", "comparison", "investment"})

_PORTFOLIO_CUES = (
    "portfolio",
    "position sizing",
    "allocation",
    "watchlist",
    "risk budget",
    "factor exposure",
    "concentration",
    "rebalanc",
    "portfolio construction",
    "portfolio quality",
    "portfolio scenario",
    "agib core",
    "concentrated growth",
)


class PortfolioIntelligenceProvider:
    spec = ProviderSpec(
        id="portfolio_intelligence",
        label="Portfolio Intelligence Engine",
        coverage=(
            "Deterministic portfolio construction, exposures, risk budget, correlation, "
            "quality, scenarios, monitoring — observations only (no BUY/SELL / no trades)"
        ),
        priority=5,
        supported_question_types=("portfolio", "company", "comparison", "investment"),
        typical_latency_ms=50,
        confidence_ceiling=0.93,
    )

    def health_check(self) -> str:
        try:
            from portfolio_intelligence.foundation.production import health

            h = health()
            return "ok" if h.get("ok") is not False else "degraded"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        types = set(plan.question_types or [])
        q = (plan.question or "").lower()

        portfolio_shaped = "portfolio" in types or any(k in q for k in _PORTFOLIO_CUES)
        if types and not types.intersection(_PI_TYPES) and not portfolio_shaped:
            return empty_result(self.spec.id, t0, "not_portfolio_shaped")
        if not portfolio_shaped:
            return empty_result(self.spec.id, t0, "not_portfolio_shaped")

        try:
            from portfolio_intelligence.foundation.production import analyse

            out = analyse(plan.question) or {}
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)

        try:
            summary = str(out.get("executive_summary") or out.get("summary") or "").strip()
            if not out.get("ok") or not summary:
                return empty_result(self.spec.id, t0, "pi_empty")
            if summary.lower().startswith("portfolio intelligence needs"):
                return empty_result(self.spec.id, t0, "pi_unresolved")

            if out.get("recommendation") not in (None, "", "none", "NONE"):
                return empty_result(self.spec.id, t0, "pi_recommendation_blocked")

            modules = list(out.get("modules_used") or [])
            why = []
            if out.get("portfolio_id"):
                why.append(f"Portfolio Intelligence id: {out.get('portfolio_id')}.")
            if modules:
                why.append("PI modules: " + ", ".join(modules[:6]) + ".")
            why.append("Observations only — no BUY/SELL and no trade recommendations.")

            evidence = [
                {
                    "source": "portfolio_intelligence",
                    "title": "modules:" + ",".join(modules[:6]) if modules else "pi_analyse",
                    "portfolio_id": out.get("portfolio_id"),
                    "recommendation_policy": out.get("recommendation_policy"),
                }
            ]
            facts: list[dict[str, Any]] = [
                {"field": "modules_used", "value": modules},
                {"field": "portfolio_id", "value": out.get("portfolio_id")},
                {"field": "recommendation_policy", "value": out.get("recommendation_policy")},
                {"field": "recommendation", "value": None},
            ]
            if out.get("unknowns"):
                facts.append({"field": "unknowns", "value": list(out.get("unknowns") or [])[:6]})

            conf = float(out.get("confidence") or 0.8)
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
                facts=[f for f in facts if f.get("value") is not None or f.get("field") == "recommendation"],
                raw=out,
            )
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)
