"""KUL provider — Macro Intelligence Engine (Phase 9.0)."""

from __future__ import annotations

import time

from knowledge_unification.providers.base import empty_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

_MACRO_MARKERS = (
    "macro",
    "macro regime",
    "macro exposure",
    "macro backdrop",
    "interest rates",
    "inflation",
    "liquidity environment",
    "economic cycle",
    "falling inflation",
    "oil impact",
    "which sectors benefit",
    "which sectors are likely",
    "why are interest rates",
    "macro outlook",
    "rbi",
    "repo rate",
    "rate cut",
    "rate hike",
    "basis point",
    "100 basis",
    "nbfc",
    "real estate",
    "usdinr",
    "commodity",
    "fiscal deficit",
    "today's indian market",
    "market breadth",
)


class MacroIntelligenceEngineProvider:
    spec = ProviderSpec(
        id="macro_intelligence_engine",
        label="Macro Intelligence Engine (institutional top-down context)",
        coverage=(
            "Explainable macro regime, cycle, sector/industry impact, company exposure, "
            "scenarios and risks from warehouse + CMKP/HMIP/MRI/HMAI/MFI — no vendors, no BUY/SELL"
        ),
        priority=4,
        supported_question_types=(
            "macro", "regime", "inflation", "rates", "sector", "forecast", "risk",
        ),
        typical_latency_ms=240,
        confidence_ceiling=0.88,
    )

    def health_check(self) -> str:
        try:
            from macro_intelligence_engine import health

            return "ok" if health().get("ok") else "empty"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        question = (plan.question or "").strip()
        qlow = question.lower()
        if not any(m in qlow for m in _MACRO_MARKERS):
            return empty_result(self.spec.id, t0, "not_a_macro_question")
        ticker = (plan.ticker_hint or "").strip().upper() or None
        try:
            from macro_intelligence_engine import ask_slice

            pack = ask_slice(question, symbol=ticker)
        except Exception as exc:
            return empty_result(self.spec.id, t0, str(exc)[:160])
        if not pack.get("ok"):
            return empty_result(self.spec.id, t0, str(pack.get("error") or "mie_empty"))
        conf_raw = pack.get("confidence")
        if isinstance(conf_raw, dict):
            level = str(conf_raw.get("confidence") or "Medium")
            score = float(conf_raw.get("score") or 0.55)
        else:
            level = str(conf_raw or "Medium")
            score = {"High": 0.85, "Medium": 0.65, "Low": 0.4}.get(level, 0.55)
        return timed_result(
            self.spec.id,
            ok=True,
            empty=False,
            confidence=min(score, self.spec.confidence_ceiling),
            t0=t0,
            summary=pack.get("summary") or "",
            why=list(pack.get("findings") or [])[:8],
            evidence=[
                {
                    "source": "macro_intelligence_engine",
                    "title": f"mie:{pack.get('module')}:{pack.get('country') or 'India'}",
                    "explainability": pack.get("explainability"),
                }
            ],
            facts=[
                {"field": "module", "value": pack.get("module"), "source": "mie"},
                {"field": "macro_regime", "value": pack.get("regime"), "source": "mie"},
                {"field": "macro_confidence", "value": level, "source": "mie"},
            ],
            raw={"recommendation": None, "gdp_point_prediction": None, "engine": "macro_intelligence_engine"},
        )
