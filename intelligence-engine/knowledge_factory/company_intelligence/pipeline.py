"""Institutional Company Intelligence pipeline — soft KF only."""

from __future__ import annotations

import time
from typing import Any

from knowledge_factory.company_intelligence import store as ici_store
from knowledge_factory.company_intelligence.dashboard import company_intelligence_dashboard
from knowledge_factory.company_intelligence.objects.compile import compile_company_intelligence
from knowledge_factory.company_intelligence.schema import ICI_VERSION

PIPELINE_VERSION = "ici-pipeline-v2.0.0"


def _universe(tickers: list[str] | None = None) -> list[str]:
    if tickers:
        return [str(t).upper() for t in tickers]
    from knowledge_factory.nifty500_universe import NIFTY_500

    return list(NIFTY_500)


def run_company_intelligence_pipeline(tickers: list[str] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    universe = _universe(tickers)
    published = 0
    failures: list[dict[str, Any]] = []
    partials: list[dict[str, Any]] = []
    ready = 0
    levels: dict[int, int] = {i: 0 for i in range(8)}

    for t in universe:
        try:
            obj = compile_company_intelligence(t, persist=True)
            published += 1
            levels[int(obj.get("coverage_level") or 0)] = levels.get(int(obj.get("coverage_level") or 0), 0) + 1
            if obj.get("institutional_ready"):
                ready += 1
            if obj.get("quality", {}).get("failed_gates"):
                partials.append({"ticker": t, "failed_gates": obj["quality"]["failed_gates"]})
        except Exception as exc:
            failures.append({"ticker": t, "reason": str(exc)})

    dash = company_intelligence_dashboard(ensure=False)
    runtime = round(time.perf_counter() - t0, 2)
    report = {
        "pipeline_version": PIPELINE_VERSION,
        "ici_version": ICI_VERSION,
        "universe_n": len(universe),
        "objects_published": published,
        "institutional_ready": ready,
        "institutional_ready_pct": round(100.0 * ready / (len(universe) or 1), 2),
        "coverage_levels": levels,
        "execution_failures": failures[:50],
        "execution_failure_count": len(failures),
        "partial_objects": partials[:50],
        "partial_object_count": len(partials),
        "validation_failures": failures[:50],
        "validation_failure_count": len(failures),
        "dashboard": dash,
        "runtime_seconds": runtime,
        "status": "ok" if published == len(universe) else "degraded",
        "fabricated": False,
        "reasoning_changed": False,
        "governance_changed": False,
    }
    ici_store.record_run(report)
    return report
