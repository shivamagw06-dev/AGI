"""Deterministic Financial Concepts provider — no retrieval."""

from __future__ import annotations

import time
from typing import Any

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

# Local phrase → existing concept keys (wiring only; no new concept cards).
_LOCAL_ALIASES = {
    "capital allocation": "capital_recycling",
    "gross margin": "contribution_margin",
    "ebitda": "adjusted_ebitda",  # nearest FC card; foundations owns plain EBITDA
}


class FinancialConceptsProvider:
    spec = ProviderSpec(
        id="financial_concepts",
        label="Institutional Financial Concepts",
        coverage="Deterministic concept cards (corporate finance, ratios, valuation, banking, …)",
        priority=5,
        supported_question_types=("concept", "valuation", "accounting"),
        typical_latency_ms=5,
        confidence_ceiling=0.95,
    )

    def health_check(self) -> str:
        try:
            from financial_concepts.production import health

            h = health()
            return "ok" if h.get("ok") is not False else "degraded"
        except Exception:
            return "error"

    def _card_from_explain(self, question: str) -> dict[str, Any]:
        from financial_concepts.production import explain

        out = explain(question) or {}
        if out.get("found") and (out.get("definition") or out.get("key")):
            return out
        # Try local aliases against existing keys.
        low = (question or "").lower()
        for phrase, key in _LOCAL_ALIASES.items():
            if phrase in low:
                card = explain(key) or {}
                if card.get("found"):
                    return card
        return out if isinstance(out, dict) else {}

    def _card_from_search(self, question: str) -> dict[str, Any]:
        from financial_concepts.production import search

        res = search(question, limit=3) or {}
        rows = list(res.get("results") or [])
        if not rows:
            return {}
        q = (question or "").lower()
        for top in rows:
            key = str(top.get("key") or "").replace("_", " ")
            title = str(top.get("title") or "").lower()
            # Strict: key phrase or full title must appear in the question.
            # Loose search rankings (e.g. EV for debit/credit Qs) are rejected.
            if key and len(key) >= 3 and key in q:
                return {"found": True, **top}
            # Title without parenthetical acronym noise
            title_core = title.split("(")[0].strip()
            if title_core and len(title_core) >= 4 and title_core in q:
                return {"found": True, **top}
        return {}

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        try:
            out = self._card_from_explain(plan.question)
            if not out.get("found"):
                out = self._card_from_search(plan.question)
            if not out.get("found") and not out.get("definition") and not out.get("key"):
                return empty_result(self.spec.id, t0, "concept_miss")

            definition = (
                out.get("definition")
                or (out.get("concept") or {}).get("definition")
                or out.get("summary")
                or ""
            )
            key = out.get("key") or (out.get("concept") or {}).get("key") or ""
            if not definition and not key:
                return empty_result(self.spec.id, t0, "concept_empty")
            meaning = out.get("business_meaning") or (out.get("concept") or {}).get("business_meaning")
            interpretation = out.get("interpretation") or (out.get("concept") or {}).get("interpretation")
            # Lead with business meaning (direct institutional answer); keep
            # the formal definition as supporting context, not the headline.
            lead = str(meaning or definition or "")[:600]
            why = []
            if meaning and definition and str(meaning).strip() != str(definition).strip():
                why.append(str(definition)[:280])
            if interpretation:
                why.append(str(interpretation)[:320])
            formula = out.get("formula") or (out.get("concept") or {}).get("formula")
            if formula:
                why.append(f"Formula: {formula}")
            return timed_result(
                self.spec.id,
                ok=True,
                empty=False,
                confidence=0.95,
                t0=t0,
                summary=lead or str(definition)[:600],
                why=why or [str(definition)[:240]],
                evidence=[{"source": "financial_concepts", "title": key or "concept"}],
                facts=[{"field": "concept_key", "value": key}],
                raw=out if isinstance(out, dict) else {},
            )
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)
