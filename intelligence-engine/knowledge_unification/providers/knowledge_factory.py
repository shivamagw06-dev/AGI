"""Knowledge Factory company-intelligence provider."""

from __future__ import annotations

import time

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan


class KnowledgeFactoryProvider:
    spec = ProviderSpec(
        id="knowledge_factory",
        label="Knowledge Factory",
        coverage="Compiled company / industry / event intelligence objects",
        priority=30,
        supported_question_types=("company", "business_model", "industry", "news"),
        typical_latency_ms=60,
        confidence_ceiling=0.8,
    )

    def health_check(self) -> str:
        try:
            from pathlib import Path

            root = Path(__file__).resolve().parents[2] / "data" / "knowledge_factory" / "objects"
            if root.exists() and any(root.glob("*.json")):
                return "ok"
            return "empty"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        ticker = plan.ticker_hint
        if not ticker:
            return empty_result(self.spec.id, t0, "no_ticker")
        try:
            from knowledge_factory.company_intelligence.production import get_company

            out = get_company(ticker) or {}
            if not out or out.get("ok") is False:
                return empty_result(self.spec.id, t0, "kf_miss")
            summary = (
                out.get("summary")
                or (out.get("identity") or {}).get("description")
                or out.get("display")
                or ""
            )
            summary_s = str(summary or "").strip()
            # Stub placeholders must not short-circuit Ask (e.g. "Knowledge Factory object for META").
            if not summary_s or summary_s.lower().startswith("knowledge factory object"):
                return empty_result(self.spec.id, t0, "kf_stub_or_empty")
            why = []
            if out.get("sector") or (out.get("identity") or {}).get("sector"):
                why.append(f"KF sector: {out.get('sector') or (out.get('identity') or {}).get('sector')}.")
            why.append(summary_s[:240])
            return timed_result(
                self.spec.id,
                ok=True,
                empty=False,
                confidence=0.75,
                t0=t0,
                summary=summary_s[:400],
                why=why[:6],
                evidence=[{"source": "knowledge_factory", "title": f"company:{ticker}"}],
                facts=[{"field": "kf_keys", "value": list(out.keys())[:20]}],
                raw=out if isinstance(out, dict) else {},
            )
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)
