"""Hedge fund screen provider — strategy scanners + warehouse factors for Ask."""

from __future__ import annotations

import time
from typing import Any

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

_SCREEN_MARKERS = (
    "hedge fund",
    "screen",
    "compounder",
    "find high-quality",
    "find companies",
    "which stocks",
    "which companies",
    "qualify",
    "attractive valuation",
    "rising institutional",
    "strong roce",
    "quality",
    "momentum",
    "value trap",
    "factor",
)


class HedgeFundScreenProvider:
    spec = ProviderSpec(
        id="hedge_fund_screens",
        label="Hedge fund strategy screens",
        coverage=(
            "Warehouse-backed institutional screens and hedge_fund_factors — "
            "research observations only, never recommendations"
        ),
        priority=26,
        supported_question_types=("investment", "valuation", "company", "market", "portfolio", "screen"),
        typical_latency_ms=400,
        confidence_ceiling=0.8,
    )

    def health_check(self) -> str:
        try:
            from hedge_fund_lab.scanner import universe_meta

            meta = universe_meta()
            if meta.get("count"):
                return "ok"
            from hedge_fund_lab.scanner import _universe

            rows = _universe()
            return "ok" if rows else "empty"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        try:
            qlow = (plan.question or "").lower()
            ticker = (plan.ticker_hint or "").strip().upper() or None

            # Universe / factor screen when no single company is bound.
            if not ticker and any(m in qlow for m in _SCREEN_MARKERS):
                return self._universe_screen(plan, t0)

            if not ticker:
                return empty_result(self.spec.id, t0, "no_screen_company")

            from hedge_fund_lab.terminal import opportunity

            data = opportunity(ticker)
            if not data.get("ok"):
                return empty_result(self.spec.id, t0, data.get("error") or "not_scanned")

            matched = data.get("strategies_matched") or []
            name = data.get("company_name") or ticker
            factors = data.get("factors") or {}
            if not matched and not factors:
                return empty_result(self.spec.id, t0, "no_screen_match")

            labels = [m.get("label") for m in matched if m.get("label")]
            if matched:
                summary = (
                    f"{name} currently satisfies {len(matched)} institutional "
                    f"{'screen' if len(matched) == 1 else 'screens'}: {', '.join(labels)}. "
                    "Screen membership marks a research priority, not a position."
                )
            else:
                summary = (
                    f"{name} hedge-fund factor pack — opportunity "
                    f"{factors.get('opportunity_score')} with "
                    f"{factors.get('strategy_agreement')} strategy agreement."
                )

            why: list[str] = [m.get("why") for m in matched if m.get("why")]
            for key in ("value_score", "quality_score", "momentum_score", "opportunity_score"):
                if factors.get(key) is not None:
                    why.append(f"{key}={factors.get(key)}")
            for risk in (data.get("risks") or [])[:2]:
                why.append(f"Risk: {risk}")
            for catalyst in (data.get("catalysts") or [])[:2]:
                why.append(f"Catalyst: {catalyst}")

            facts: list[dict[str, Any]] = [
                {"field": f"screen_{m.get('strategy')}", "value": m.get("confidence"), "label": m.get("label")}
                for m in matched
            ]
            return timed_result(
                self.spec.id,
                ok=True,
                empty=False,
                confidence=0.72,
                t0=t0,
                summary=summary,
                why=why,
                evidence=[{"source": "hedge_fund_lab.terminal", "title": f"screens:{ticker}"}],
                facts=facts,
                raw={
                    "ticker": ticker,
                    "company_name": name,
                    "strategies_matched": matched,
                    "factors": factors,
                    "calculation_chain": data.get("calculation_chain"),
                    "timeline": (data.get("timeline") or [])[-5:],
                },
            )
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)

    def _universe_screen(self, plan: QueryPlan, t0: float) -> ProviderResult:
        from hedge_fund_lab.terminal import scan

        qlow = (plan.question or "").lower()
        strategy = "quality"
        if "value" in qlow or "cheap" in qlow or "attractive valuation" in qlow:
            strategy = "value"
        elif "momentum" in qlow:
            strategy = "momentum"
        elif "dividend" in qlow:
            strategy = "dividend"
        elif "stress" in qlow or "distress" in qlow:
            strategy = "stress"
        elif "conviction" in qlow or "consensus" in qlow:
            strategy = "conviction"
        elif "growth" in qlow or "compounder" in qlow:
            strategy = "growth"
        elif "pair" in qlow:
            strategy = "pairs"

        data = scan(strategy, limit=12)
        if not data.get("ok"):
            return empty_result(self.spec.id, t0, data.get("error") or "screen_empty")
        rows = data.get("results") or []
        if not rows:
            return empty_result(self.spec.id, t0, "no_screen_hits")

        top = rows[:8]
        names = [
            f"{r.get('ticker') or (r.get('long_leg') or {}).get('ticker')} "
            f"({r.get('confidence') or '—'})"
            for r in top
            if r.get("ticker") or r.get("long_leg")
        ]
        summary = (
            f"Hedge Fund Lab {data.get('label') or strategy} screen — "
            f"{len(rows)} research observations from "
            f"{data.get('universe_scanned')} companies. Top: {', '.join(names[:5])}. "
            "Descriptive only — not recommendations."
        )
        why = [r.get("why") for r in top if r.get("why")][:8]
        return timed_result(
            self.spec.id,
            ok=True,
            empty=False,
            confidence=0.7,
            t0=t0,
            summary=summary,
            why=why,
            evidence=[{"source": "hedge_fund_lab.terminal", "title": f"scan:{strategy}"}],
            facts=[
                {"field": "scan", "value": strategy, "source": "hedge_fund_lab"},
                {"field": "hits", "value": len(rows), "source": "hedge_fund_lab"},
            ],
            raw={
                "scan": strategy,
                "count": len(rows),
                "top": [
                    {
                        "ticker": r.get("ticker") or (r.get("long_leg") or {}).get("ticker"),
                        "why": r.get("why"),
                        "confidence": r.get("confidence"),
                    }
                    for r in top
                ],
                "sources": data.get("sources"),
                "universe_meta": data.get("universe_meta"),
            },
        )
