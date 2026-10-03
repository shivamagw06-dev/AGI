"""Academy / Damodaran structured datasets provider."""

from __future__ import annotations

import time

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan


class AcademyProvider:
    spec = ProviderSpec(
        id="academy",
        label="Academy / Structured Finance Datasets",
        coverage="Learned academy books + Damodaran ERP / country premiums / valuation datasets",
        priority=40,
        supported_question_types=("concept", "valuation", "macro", "accounting"),
        typical_latency_ms=25,
        confidence_ceiling=0.8,
    )

    def health_check(self) -> str:
        try:
            from pathlib import Path

            snap = Path(__file__).resolve().parents[2] / "academy" / "books" / "learned" / "library_snapshot.json"
            if snap.exists():
                return "ok"
            return "empty"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        try:
            # Prefer finance-academy package when present (soft, structured).
            try:
                from finance_academy.production import package_for_query  # type: ignore

                out = package_for_query(plan.question, engine="ask_agi", ticker=plan.ticker_hint) or {}
            except Exception:
                out = {}
            if not out:
                try:
                    from academy.books.production import research_writer_slice  # type: ignore

                    out = research_writer_slice(plan.question, ticker=plan.ticker_hint) or {}
                except Exception:
                    out = {}
            if not out:
                return empty_result(self.spec.id, t0, "academy_miss")
            hints = list(out.get("logic_hints") or out.get("frameworks") or out.get("hints") or [])
            summary = out.get("summary") or (hints[0] if hints else "")
            if not summary and not hints:
                # Still count structured metadata as a soft contribution.
                if out.get("enabled") or out.get("books") or out.get("concepts"):
                    return timed_result(
                        self.spec.id,
                        ok=True,
                        empty=False,
                        confidence=0.55,
                        t0=t0,
                        summary="Academy structured knowledge available for this question.",
                        why=["Academy soft-slice consulted (framework/concept hints)."],
                        evidence=[{"source": "academy", "title": "soft_slice"}],
                        facts=[{"field": "academy_keys", "value": list(out.keys())[:15]}],
                        raw=out if isinstance(out, dict) else {},
                    )
                return empty_result(self.spec.id, t0, "academy_empty")
            return timed_result(
                self.spec.id,
                ok=True,
                empty=False,
                confidence=0.72,
                t0=t0,
                summary=str(summary)[:400],
                why=[str(h)[:200] for h in (hints or [summary])[:5]],
                evidence=[{"source": "academy", "title": "structured_dataset"}],
                facts=[{"field": "academy_hint_count", "value": len(hints)}],
                raw=out if isinstance(out, dict) else {},
            )
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)
