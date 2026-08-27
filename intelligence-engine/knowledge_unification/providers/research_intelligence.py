"""Research Intelligence provider — Phase 3.4.5 KUL integration.

Wraps research_intelligence.production.analyse. Surfaces annual reports,
transcripts, management, guidance, events, memory, timeline, and deep research —
without BUY/SELL or forecasts. Does not bypass KUL.
"""

from __future__ import annotations

import time
from typing import Any

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

_RI_TYPES = frozenset(
    {
        "research",
        "company",
        "news",
        "comparison",
        "business_model",
        "business_risk",
    }
)

_RESEARCH_CUES = (
    "annual report",
    "earnings call",
    "earnings transcript",
    "conference call",
    "transcript",
    "management commentary",
    "management intelligence",
    "guidance history",
    "guidance evolved",
    "guidance intelligence",
    "research memory",
    "deep research",
    "cross-document",
    "cross document",
    "investor day",
    "research timeline",
    "timeline intelligence",
    "what changed since",
    "last quarter",
    "five years of",
    "5 years of",
    "from the annual report",
    "capital allocation evolution",
    "management philosophy",
    "estimate intelligence",
    "estimate changes",
    "event intelligence",
    "event research",
)


class ResearchIntelligenceProvider:
    spec = ProviderSpec(
        id="research_intelligence",
        label="Research Intelligence Engine",
        coverage=(
            "Deterministic institutional research memory — annual reports, transcripts, "
            "management, guidance, events, timeline, deep research (no BUY/SELL, no forecasts)"
        ),
        priority=5,
        supported_question_types=(
            "research",
            "company",
            "news",
            "comparison",
            "business_model",
            "business_risk",
        ),
        typical_latency_ms=55,
        confidence_ceiling=0.94,
    )

    def health_check(self) -> str:
        try:
            from research_intelligence.production import health

            h = health()
            return "ok" if h.get("ok") is not False else "degraded"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        types = set(plan.question_types or [])
        q = (plan.question or "").lower()

        research_shaped = "research" in types or any(k in q for k in _RESEARCH_CUES)
        if types and not types.intersection(_RI_TYPES) and not research_shaped:
            return empty_result(self.spec.id, t0, "not_research_shaped")

        # Pure industry pedagogy without research cues → leave to II.
        if (
            not research_shaped
            and "industry" in types
            and "company" not in types
            and not plan.ticker_hint
            and not plan.company_hint
        ):
            return empty_result(self.spec.id, t0, "industry_pedagogy_defer")

        # Pure investment thesis/catalyst/scenario without research cues → INV.
        if (
            not research_shaped
            and "investment" in types
            and not any(k in q for k in ("annual", "transcript", "guidance", "memory", "timeline"))
        ):
            return empty_result(self.spec.id, t0, "investment_defer_to_inv")

        try:
            from research_intelligence.production import analyse

            out = analyse(plan.question) or {}
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)

        try:
            summary = str(out.get("executive_summary") or out.get("summary") or "").strip()
            if not out.get("ok") or not summary:
                return empty_result(self.spec.id, t0, "ri_empty")
            if summary.lower().startswith("research intelligence needs a supported"):
                return empty_result(self.spec.id, t0, "ri_unresolved_entity")

            if out.get("recommendation") not in (None, "", "none", "NONE"):
                return empty_result(self.spec.id, t0, "ri_recommendation_blocked")

            modules = list(out.get("modules_used") or [])
            why = [str(w) for w in (out.get("whats_new") or []) if w][:6]
            if out.get("entity"):
                why.insert(0, f"Research Intelligence entity: {out.get('entity')}.")
            if out.get("policy_refuse"):
                why.append(f"Policy refusal: {out.get('refuse_kind')}.")
            if not why and modules:
                why.append("RI modules: " + ", ".join(modules[:6]) + ".")
            why.append("Observations only — structured research memory, no BUY/SELL.")

            evidence = [
                {
                    "source": "research_intelligence",
                    "title": "modules:" + ",".join(modules[:6]) if modules else "ri_analyse",
                    "entity": out.get("entity"),
                    "recommendation_policy": out.get("recommendation_policy"),
                    "knowledge_authority": out.get("knowledge_authority"),
                }
            ]

            facts: list[dict[str, Any]] = [
                {"field": "modules_used", "value": modules},
                {"field": "entity", "value": out.get("entity")},
                {"field": "company", "value": out.get("company")},
                {"field": "recommendation_policy", "value": out.get("recommendation_policy")},
                {"field": "recommendation", "value": None},
                {"field": "policy_refuse", "value": out.get("policy_refuse")},
            ]
            if out.get("unknowns"):
                facts.append({"field": "unknowns", "value": list(out.get("unknowns") or [])[:6]})
            if out.get("monitoring_points"):
                facts.append(
                    {"field": "monitoring_points", "value": list(out.get("monitoring_points") or [])[:6]}
                )

            conf = float(out.get("confidence") or 0.85)
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
