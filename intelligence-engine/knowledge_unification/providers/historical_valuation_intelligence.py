"""KUL provider — Historical Valuation Intelligence Engine (HVIE)."""

from __future__ import annotations

import time

from knowledge_unification.providers.base import empty_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

_MARKERS = (
    "historical",
    "history",
    "expensive",
    "cheap",
    "overvalued",
    "undervalued",
    "percentile",
    "regime",
    "rerat",
    "similar to today",
    "when has",
    "when was",
    "ever traded",
    "unusual",
    "afterwards",
    "own history",
    "versus history",
    "vs history",
    "valuation",
    "premium",
    "discount",
    "analyze",
    "outlook",
    "compare",
)


class HistoricalValuationIntelligenceProvider:
    spec = ProviderSpec(
        id="historical_valuation_intelligence",
        label="Historical Valuation Intelligence Engine",
        coverage=(
            "Own-history multiples, percentiles, regimes and re-rating from warehouse "
            "HVIE reconstruction — no vendor historical ratio pulls at Ask time"
        ),
        priority=6,
        supported_question_types=(
            "valuation", "historical", "company", "investment", "comparison", "attribution",
        ),
        typical_latency_ms=200,
        confidence_ceiling=0.9,
    )

    def health_check(self) -> str:
        try:
            from historical_valuation_intelligence.ask import answer_for  # noqa: F401

            return "ok"
        except Exception:
            return "degraded"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        question = (plan.question or "").strip()
        qlow = question.lower()
        if not any(m in qlow for m in _MARKERS):
            return empty_result(self.spec.id, t0, "not_a_hvie_question")
        ticker = (plan.ticker_hint or "").strip().upper()
        if not ticker:
            return empty_result(self.spec.id, t0, "no_company_for_hvie")
        ask_pack: dict = {}
        pack: dict = {}
        try:
            from historical_valuation_intelligence.ask import answer_for
            from historical_valuation_intelligence.production import company as hvie_company

            ask_pack = answer_for(ticker, question) or {}
            pack = ask_pack if ask_pack.get("ok") else (hvie_company(ticker, window="10y") or {})
        except Exception as exc:
            return empty_result(self.spec.id, t0, str(exc)[:160])
        if not pack.get("ok"):
            return empty_result(self.spec.id, t0, str(pack.get("error") or "hvie_empty"))
        use = pack
        summary = use.get("answer") or use.get("prose") or use.get("summary") or (
            f"{ticker} historical valuation — current {use.get('current')} vs "
            f"median {use.get('median')} (percentile {use.get('historical_percentile')})."
        )
        why = []
        for key in ("current", "median", "historical_percentile", "regime", "premium_to_median_pct"):
            if use.get(key) is not None:
                why.append(f"{key}={use.get(key)}")
        expl = use.get("explainability") or {
            "observed": [f"current={use.get('current')}", f"median={use.get('median')}"],
            "derived": [f"historical_percentile={use.get('historical_percentile')}"],
            "inferred": [f"regime={use.get('regime')}"] if use.get("regime") else [],
        }
        return timed_result(
            self.spec.id,
            ok=True,
            empty=False,
            confidence=0.8,
            t0=t0,
            summary=str(summary)[:1200],
            why=why[:8],
            evidence=[{
                "source": "historical_valuation_intelligence",
                "title": f"hvie:{ticker}",
                "explainability": expl,
            }],
            facts=[
                {"field": "historical_percentile", "value": use.get("historical_percentile"), "source": "hvie"},
                {"field": "regime", "value": use.get("regime"), "source": "hvie"},
            ],
            raw={"engine": "historical_valuation_intelligence", "symbol": ticker},
        )
