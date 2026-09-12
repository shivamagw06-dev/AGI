"""Investment Intelligence provider — Phase 3.2.5 KUL integration.

Wraps investment_intelligence.production.analyse. Surfaces thesis, quality,
catalysts, risks, scenarios, valuation drivers, evidence, and monitoring —
without BUY/SELL recommendations. Does not bypass KUL.
"""

from __future__ import annotations

import re
import time
from typing import Any, Optional

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

# Questions that deserve the company's own thesis rather than a module digest.
_THESIS_QUESTION_RE = re.compile(
    r"\b(investment thesis|thesis|why (?:would|should).{0,25}(?:own|buy into|hold)|"
    r"biggest risks?|key risks?|major risks?|catalysts?|"
    r"business and financial quality|business quality|financial quality|"
    r"capital allocation|bull case|bear case|scenario|"
    r"full institutional view|institutional view|brief me|"
    r"what should i know about|assess)\b",
    re.I,
)


def _wants_thesis(question_lower: str, types: set[str]) -> bool:
    return bool(_THESIS_QUESTION_RE.search(question_lower)) or "investment" in types


def _company_thesis_result(
    provider_id: str, t0: float, ticker: str
) -> Optional[ProviderResult]:
    """Company Thesis Intelligence result, or None to fall through."""
    try:
        from investment_intelligence.company_thesis import thesis_narrative

        pack = thesis_narrative(ticker)
    except Exception:
        return None
    if not pack or not pack.get("summary"):
        return None

    why = [line for line in (pack.get("why") or []) if line][:8]
    why.append("Observations only — no BUY/SELL recommendation.")
    metrics = pack.get("metrics") or {}
    facts = [
        {"field": key, "value": value}
        for key, value in metrics.items()
        if value is not None
    ]
    facts.append({"field": "thesis_sections", "value": list((pack.get("sections") or {}).keys())})
    facts.append({"field": "recommendation", "value": None})
    return timed_result(
        provider_id,
        ok=True,
        empty=False,
        confidence=0.92,
        t0=t0,
        summary=pack["summary"],
        why=why,
        evidence=pack.get("evidence") or [],
        facts=facts,
        raw={
            "engine": "company_thesis_intelligence",
            "ticker": pack.get("ticker"),
            "company_name": pack.get("company_name"),
            "sections": pack.get("sections"),
            "metrics": metrics,
        },
    )

import re

# A bound company asking anything thesis-shaped gets its own thesis, not the
# industry narrative it used to inherit.
_THESIS_QUESTION_RE = re.compile(
    r"\b(investment thesis|thesis|why (?:would|should).{0,25}(?:own|invest|buy into)|"
    r"biggest risks?|key risks?|major risks?|catalysts?|"
    r"business (?:and financial )?quality|financial quality|capital allocation|"
    r"bull case|bear case|scenario|valuation context|"
    r"institutional view|full view|assess|evaluate)\b",
    re.I,
)


def _wants_thesis(question: str, types: set[str]) -> bool:
    return bool(_THESIS_QUESTION_RE.search(question or "")) or "investment" in types


def _company_thesis_result(provider_id: str, t0: float, ticker: str):
    """Company Thesis Intelligence result, or None to fall through."""
    try:
        from investment_intelligence.company_thesis import thesis_narrative

        pack = thesis_narrative(ticker)
    except Exception:
        return None
    if not pack or not pack.get("summary"):
        return None

    why = [line for line in (pack.get("why") or []) if line][:8]
    why.append("Observations only — no BUY/SELL recommendation.")
    metrics = pack.get("metrics") or {}
    facts = [
        {"field": key, "value": value}
        for key, value in metrics.items()
        if value is not None
    ]
    facts.append({"field": "recommendation", "value": None})
    return timed_result(
        provider_id,
        ok=True,
        empty=False,
        confidence=0.92,
        t0=t0,
        summary=pack["summary"],
        why=why,
        evidence=pack.get("evidence") or [],
        facts=facts,
        raw={
            "engine": "company_thesis_intelligence",
            "ticker": pack.get("ticker"),
            "company_name": pack.get("company_name"),
            "sections": pack.get("sections") or {},
            "metrics": metrics,
        },
    )


_INV_TYPES = frozenset(
    {
        "investment",
        "company",
        "business_model",
        "business_risk",
        "comparison",
        "valuation",
        "moat",
    }
)


class InvestmentIntelligenceProvider:
    spec = ProviderSpec(
        id="investment_intelligence",
        label="Investment Intelligence Engine",
        coverage=(
            "Deterministic investment thesis, quality, catalysts, risks, scenarios, "
            "valuation drivers, evidence, monitoring — observations only (no BUY/SELL)"
        ),
        priority=6,
        supported_question_types=(
            "investment",
            "company",
            "business_model",
            "business_risk",
            "comparison",
            "valuation",
            "moat",
        ),
        typical_latency_ms=45,
        confidence_ceiling=0.93,
    )

    @staticmethod
    def _thesis_hook() -> None:  # pragma: no cover - documentation anchor
        """Company Thesis Intelligence is consulted before the generic analyse()."""

    def health_check(self) -> str:
        try:
            from investment_intelligence.production import health

            h = health()
            return "ok" if h.get("ok") is not False else "degraded"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        types = set(plan.question_types or [])
        q = (plan.question or "").lower()

        # Skip pure industry pedagogy / accounting / macro unless investment-shaped.
        investment_shaped = "investment" in types or any(
            k in q
            for k in (
                "investment thesis",
                "catalyst",
                "scenario",
                "investors monitor",
                "evidence strength",
                "investment quality",
                "investment risk",
                "from an investment",
                "committee",
                "attractive",
                "downside risk",
            )
        )
        if types and not types.intersection(_INV_TYPES) and not investment_shaped:
            return empty_result(self.spec.id, t0, "not_investment_shaped")

        # Pure industry DNA pedagogy without company / investment verbs → leave to II.
        if (
            not investment_shaped
            and "industry" in types
            and "company" not in types
            and not plan.ticker_hint
            and not plan.company_hint
            and "comparison" not in types
        ):
            return empty_result(self.spec.id, t0, "industry_pedagogy_defer_to_ii")

        # Company Thesis Intelligence — a bound company gets its own thesis,
        # synthesised from its identity, financials, consensus and peer
        # position, rather than inheriting the industry narrative.
        if plan.ticker_hint and _wants_thesis(q, types):
            thesis = _company_thesis_result(self.spec.id, t0, plan.ticker_hint)
            if thesis is not None:
                return thesis

        try:
            from investment_intelligence.production import analyse

            out = analyse(plan.question) or {}
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)

        try:
            summary = str(out.get("executive_summary") or out.get("summary") or "").strip()
            if not out.get("ok") or not summary:
                return empty_result(self.spec.id, t0, "inv_empty")
            if summary.lower().startswith("investment intelligence needs a supported"):
                return empty_result(self.spec.id, t0, "inv_unresolved_entity")

            # Hard policy: never surface recommendation leakage via KUL.
            if out.get("recommendation") not in (None, "", "none", "NONE"):
                return empty_result(self.spec.id, t0, "inv_recommendation_blocked")

            modules = list(out.get("modules_used") or [])
            why = [str(w) for w in (out.get("supporting_analysis") or []) if w][:8]
            if out.get("entity"):
                why.insert(0, f"Investment Intelligence entity: {out.get('entity')}.")
            if not why and modules:
                why.append("INV modules: " + ", ".join(modules[:6]) + ".")
            why.append("Observations only — no BUY/SELL recommendation.")

            evidence = [
                {
                    "source": "investment_intelligence",
                    "title": "modules:" + ",".join(modules[:6]) if modules else "inv_analyse",
                    "entity": out.get("entity"),
                    "recommendation_policy": out.get("recommendation_policy"),
                }
            ]

            facts: list[dict[str, Any]] = [
                {"field": "modules_used", "value": modules},
                {"field": "entity", "value": out.get("entity")},
                {"field": "industry", "value": out.get("industry")},
                {"field": "recommendation_policy", "value": out.get("recommendation_policy")},
                {"field": "recommendation", "value": None},
            ]
            ql = out.get("quality") or {}
            if isinstance(ql, dict) and ql.get("composite_score") is not None:
                facts.append({"field": "quality_composite", "value": ql.get("composite_score")})
            if out.get("unknowns"):
                facts.append({"field": "unknowns", "value": list(out.get("unknowns") or [])[:6]})
            if out.get("monitoring_points"):
                facts.append(
                    {"field": "monitoring_points", "value": list(out.get("monitoring_points") or [])[:6]}
                )

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
