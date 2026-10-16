"""KUL provider — Forecast Intelligence Engine (Phase 8.5)."""

from __future__ import annotations

import time

from knowledge_unification.providers.base import empty_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

_FORECAST_MARKERS = (
    "forecast",
    "outlook",
    "bull case",
    "bear case",
    "base case",
    "bull, base",
    "scenario",
    "next 3 years",
    "next 3–5 years",
    "next 3-5 years",
    "3–5 years",
    "3-5 years",
    "fy+",
    "assumptions matter",
    "confidence low",
    "invalidate this forecast",
    "how has the forecast",
    "sensitivity",
    "forecast confidence",
    "growth outlook",
    "analyze",
    "analyse",
    "institutional",
    "compounder",
    "catalyst",
)


class ForecastIntelligenceEngineProvider:
    spec = ProviderSpec(
        id="forecast_intelligence_engine",
        label="Forecast Intelligence Engine (institutional forward outlook)",
        coverage=(
            "Explainable business/growth/valuation outlooks and bull/base/bear scenarios "
            "from warehouse + UVE/HVIE/VARIE/RIE — no vendors, no BUY/SELL, no target prices"
        ),
        priority=5,
        supported_question_types=(
            "forecast", "outlook", "company", "valuation", "scenario", "risk",
        ),
        typical_latency_ms=220,
        confidence_ceiling=0.86,
    )

    def health_check(self) -> str:
        try:
            from forecast_intelligence_engine import health

            return "ok" if health().get("ok") else "empty"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        question = (plan.question or "").strip()
        qlow = question.lower()
        if not any(m in qlow for m in _FORECAST_MARKERS):
            return empty_result(self.spec.id, t0, "not_a_forecast_question")
        ticker = (plan.ticker_hint or "").strip().upper()
        if not ticker:
            return empty_result(self.spec.id, t0, "no_company_for_forecast")
        try:
            from forecast_intelligence_engine import ask_slice

            pack = ask_slice(question, symbol=ticker)
        except Exception as exc:
            return empty_result(self.spec.id, t0, str(exc)[:160])
        if not pack.get("ok"):
            return empty_result(self.spec.id, t0, str(pack.get("error") or "fie_empty"))
        conf_raw = pack.get("confidence")
        if isinstance(conf_raw, dict):
            level = str(conf_raw.get("confidence") or "Medium")
            score = float(conf_raw.get("score") or 0.55)
        else:
            level = str(conf_raw or "Medium")
            score = {"High": 0.85, "Medium": 0.65, "Low": 0.4}.get(level, 0.55)
        summary = pack.get("summary") or ""
        findings = list(pack.get("findings") or [])
        return timed_result(
            self.spec.id,
            ok=True,
            empty=False,
            confidence=min(score, self.spec.confidence_ceiling),
            t0=t0,
            summary=summary,
            why=findings[:8],
            evidence=[
                {
                    "source": "forecast_intelligence_engine",
                    "title": f"fie:{pack.get('module')}:{ticker}",
                    "explainability": pack.get("explainability"),
                }
            ],
            facts=[
                {"field": "module", "value": pack.get("module"), "source": "fie"},
                {"field": "forecast_confidence", "value": level, "source": "fie"},
            ],
            raw={"recommendation": None, "target_price": None, "engine": "forecast_intelligence_engine"},
        )
