"""Company Memory Compiler provider."""

from __future__ import annotations

import concurrent.futures
import time

from knowledge_unification.providers.base import empty_result, error_result, timed_result
from knowledge_unification.schema import ProviderResult, ProviderSpec, QueryPlan

# Soft timeout: memory compile/package can be slow on cold paths.
_MEMORY_TIMEOUT_SEC = 1.0


class CompanyMemoryProvider:
    spec = ProviderSpec(
        id="company_memory",
        label="Company Memory Compiler",
        coverage="Compiled financial/ownership/valuation/event memory per ticker",
        priority=12,
        supported_question_types=("company", "business_model", "valuation", "market"),
        typical_latency_ms=80,
        confidence_ceiling=0.85,
    )

    def health_check(self) -> str:
        try:
            from company_memory.production import health

            h = health()
            return "ok" if h.get("ok") is not False else "degraded"
        except Exception:
            return "error"

    def consult(self, plan: QueryPlan) -> ProviderResult:
        t0 = time.perf_counter()
        ticker = plan.ticker_hint
        if not ticker:
            return empty_result(self.spec.id, t0, "no_ticker")

        def _package() -> dict:
            from company_memory.production import package_for_ask_agi

            return package_for_ask_agi(ticker) or {}

        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            fut = pool.submit(_package)
            out = fut.result(timeout=_MEMORY_TIMEOUT_SEC)
        except concurrent.futures.TimeoutError:
            return empty_result(self.spec.id, t0, "timeout")
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)
        finally:
            # Do not wait for a hung compile — wait=True would defeat the timeout.
            pool.shutdown(wait=False, cancel_futures=True)

        try:
            if not out.get("ok"):
                return empty_result(self.spec.id, t0, "memory_not_ok")
            mem = out.get("memory") or {}
            why = []
            if mem.get("financial_history"):
                why.append("Company memory includes compiled financial history.")
            if mem.get("ownership_history"):
                why.append("Company memory includes ownership history.")
            if mem.get("valuation_history"):
                why.append("Company memory includes valuation history.")
            if mem.get("event_timeline_n"):
                why.append(f"Event timeline entries: {mem.get('event_timeline_n')}.")
            if not why:
                return empty_result(self.spec.id, t0, "memory_empty_payload")
            return timed_result(
                self.spec.id,
                ok=True,
                empty=False,
                confidence=float(out.get("confidence") or 0.75),
                t0=t0,
                summary=f"Company memory available for {ticker}.",
                why=why,
                evidence=[{"source": "company_memory", "title": f"memory:{ticker}"}],
                facts=[{"field": k, "value": v} for k, v in mem.items() if v],
                raw=out,
            )
        except Exception as exc:
            return error_result(self.spec.id, t0, exc)
