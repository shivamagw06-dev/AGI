"""Institutional Corporate Event Intelligence pipeline — soft KF only."""

from __future__ import annotations

import time
from typing import Any

from knowledge_factory.corporate_events import store as icei_store
from knowledge_factory.corporate_events.dashboard import corporate_events_dashboard
from knowledge_factory.corporate_events.objects.compile import compile_company_timeline
from knowledge_factory.corporate_events.schema import ICEI_VERSION

PIPELINE_VERSION = "icei-pipeline-v2.0.0"


def _universe(tickers: list[str] | None = None) -> list[str]:
    if tickers:
        return [str(t).upper() for t in tickers]
    from knowledge_factory.nifty500_universe import NIFTY_500

    return list(NIFTY_500)


def run_corporate_events_pipeline(tickers: list[str] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    universe = _universe(tickers)
    published = 0
    failures: list[dict[str, Any]] = []
    ready = 0
    total_events = 0

    for t in universe:
        try:
            obj = compile_company_timeline(t, persist=True)
            published += 1
            total_events += int(obj.get("event_count") or 0)
            if obj.get("institutional_ready"):
                ready += 1
            if obj.get("quality", {}).get("failed_gates"):
                failures.append({"ticker": t, "failed_gates": obj["quality"]["failed_gates"]})
        except Exception as exc:
            failures.append({"ticker": t, "reason": str(exc)})

    dash = corporate_events_dashboard(ensure=False)
    runtime = round(time.perf_counter() - t0, 2)
    report = {
        "pipeline_version": PIPELINE_VERSION,
        "icei_version": ICEI_VERSION,
        "universe_n": len(universe),
        "timelines_published": published,
        "events_published": total_events,
        "institutional_ready": ready,
        "institutional_ready_pct": round(100.0 * ready / (len(universe) or 1), 2),
        "validation_failures": failures[:50],
        "validation_failure_count": len(failures),
        "dashboard": dash,
        "runtime_seconds": runtime,
        "status": "ok" if published == len(universe) else "degraded",
        "fabricated": False,
        "reasoning_changed": False,
        "governance_changed": False,
        "events_invented": False,
    }
    icei_store.record_run(report)
    return report
