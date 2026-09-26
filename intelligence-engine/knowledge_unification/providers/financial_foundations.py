"""Financial Foundations (Phase 1) provider — accounting basics."""

from __future__ import annotations

import time

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

# Phrase → existing foundations education keys (no new knowledge cards).
_PHRASE_KEYS = (
    ("balance sheet", "accounting_equation"),
    ("income statement", "gross_profit"),
    ("profit and loss", "gross_profit"),
    ("p&l", "gross_profit"),
    ("gross margin", "gross_profit"),
    ("accrued expenses", "matching_principle"),
    ("accrued expense", "matching_principle"),
    ("journal entry", "journal"),
    ("double entry", "debit"),
    ("double-entry", "debit"),
    ("retained earnings", "retained_earnings"),
    ("depreciation", "depreciation"),
    ("ebitda", "ebitda"),
)


class FinancialFoundationsProvider:
    spec = ProviderSpec(
        id="financial_foundations",
        label="Financial Foundations",
        coverage="Deterministic accounting foundations / transaction → statements",
        priority=6,
        supported_question_types=("accounting", "concept", "financial_statement"),
        typical_latency_ms=8,
        confidence_ceiling=0.95,
    )

    def health_check(self) -> str:
        try:
            from financial_foundations.production import health

            h = health()
            return "ok" if (h.get("ok") is not False and h.get("status") != "error") else "degraded"
        except Exception:
            return "error"

    def _explain_direct(self, question: str) -> dict:
        from financial_foundations.production import explain

        out = explain(question) or {}
        if out.get("found"):
            return out
        low = (question or "").lower()
        for phrase, key in _PHRASE_KEYS:
            if phrase in low:
                hit = explain(key) or {}
                if hit.get("found"):
                    return hit
        return out if isinstance(out, dict) else {}

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        try:
            # Prefer the live financial_router for shaped accounting/FSA
            # questions (advance revenue, salary accrue, YoY interpret, …).
            # Education-layer phrase aliases are a secondary path for plain
            # "what is X" concept cards.
            from app.ui.financial_router import route as financial_router_route

            hit = financial_router_route(plan.question)
            if hit:
                engine = str(hit.get("engine") or hit.get("financial_engine") or "")
                # Only claim foundations ownership when the router chose us
                # (or did not name another engine).
                if engine and "statement" in engine.lower() and "foundation" not in engine.lower():
                    pass  # let FSI provider own this hit
                else:
                    summary = hit.get("summary") or hit.get("executive") or ""
                    why = list(hit.get("why") or [])
                    if summary or why:
                        return timed_result(
                            self.spec.id,
                            ok=True,
                            empty=False,
                            confidence=0.94,
                            t0=t0,
                            summary=str(summary)[:800],
                            why=why[:8],
                            evidence=list(
                                hit.get("evidence")
                                or [{"source": "financial_foundations", "title": engine or "lesson"}]
                            ),
                            facts=[
                                {"field": "engine", "value": engine or "financial_foundations"},
                                {"field": "key", "value": hit.get("key")},
                            ],
                            raw=hit if isinstance(hit, dict) else {},
                        )

            direct = self._explain_direct(plan.question)
            if direct.get("found") and (direct.get("definition") or direct.get("key")):
                why = []
                if direct.get("business_meaning"):
                    why.append(str(direct["business_meaning"]))
                if direct.get("common_mistake"):
                    why.append(f"Common mistake: {direct['common_mistake']}")
                if direct.get("example"):
                    why.append(f"Example: {direct['example']}")
                return timed_result(
                    self.spec.id,
                    ok=True,
                    empty=False,
                    confidence=0.93,
                    t0=t0,
                    summary=str(direct.get("definition") or "")[:800],
                    why=why[:8] or [str(direct.get("definition") or "")[:240]],
                    evidence=[{"source": "financial_foundations", "title": direct.get("key") or "lesson"}],
                    facts=[
                        {"field": "engine", "value": "financial_foundations"},
                        {"field": "key", "value": direct.get("key")},
                    ],
                    raw=direct,
                )

            return empty_result(self.spec.id, t0, "foundations_miss")
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)
