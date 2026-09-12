"""KUL provider — Research Intelligence Engine dossiers (Phase 8.4)."""

from __future__ import annotations

import time
from typing import Any

from knowledge_unification.providers.base import empty_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

_RESEARCH_MARKERS = (
    "research note",
    "complete research",
    "complete company intelligence",
    "company intelligence",
    "institutional equity analyst",
    "investment committee",
    "ic report",
    "committee report",
    "committee memorandum",
    "research report",
    "research memorandum",
    "dossier",
    "as if you were",
    "preparing an investment",
    "summarize",
    "explain",
    "analyze",
    "analyse",
    "investment case",
    "biggest risk",
    "what should i monitor",
    "monitoring points",
    "key monitoring",
    "why is",
    "trading at a premium",
    "trades at a premium",
    "premium valuation",
    "rerated",
    "roe evolved",
    "institutional profile",
    "compare",
    "similarities",
    "differences",
    "forecast",
    "outlook",
    "3–5 year",
    "3-5 year",
    "bull",
    "bear",
    "macro exposure",
    "historical valuation",
    "research",
    "agib",
)


class ResearchIntelligenceEngineProvider:
    spec = ProviderSpec(
        id="research_intelligence_engine",
        label="Research Intelligence Engine (institutional dossier consumer)",
        coverage=(
            "Evidence-backed company research dossiers synthesized from warehouse + "
            "UVE/HVIE/VARIE/VPAE — no vendor calls, no BUY/SELL language"
        ),
        priority=5,
        supported_question_types=(
            "research", "company", "valuation", "investment", "financial", "risk",
        ),
        typical_latency_ms=180,
        confidence_ceiling=0.88,
    )

    def health_check(self) -> str:
        try:
            from research_intelligence_engine import health

            return "ok" if health().get("ok") else "empty"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        question = (plan.question or "").strip()
        qlow = question.lower()
        if not any(m in qlow for m in _RESEARCH_MARKERS):
            return empty_result(self.spec.id, t0, "not_a_research_dossier_question")
        ticker = (plan.ticker_hint or "").strip().upper()
        if not ticker:
            return empty_result(self.spec.id, t0, "no_company_for_research")
        try:
            from research_intelligence_engine import ask_slice

            pack = ask_slice(question, symbol=ticker)
        except Exception as exc:
            return empty_result(self.spec.id, t0, str(exc)[:160])
        if not pack.get("ok"):
            return empty_result(self.spec.id, t0, str(pack.get("error") or "rie_empty"))
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
                    "source": "research_intelligence_engine",
                    "title": f"rie:{pack.get('section')}:{ticker}",
                    "explainability": pack.get("explainability"),
                }
            ],
            facts=[
                {"field": "section", "value": pack.get("section"), "source": "rie"},
                {"field": "research_confidence", "value": level, "source": "rie"},
            ],
            meta={"recommendation": None, "engine": "research_intelligence_engine"},
        )
