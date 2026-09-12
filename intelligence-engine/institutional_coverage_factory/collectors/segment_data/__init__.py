"""Segment KPI collector."""

from __future__ import annotations

from typing import Any, Dict

from institutional_coverage_factory.collectors.base import collector_result, soft_step


def collect(ticker: str) -> Dict[str, Any]:
    t = str(ticker or "").upper().strip()
    steps = []

    def _fse():
        from financial_statements_engine.production import run_ingest, run_publish

        run_ingest(t, force=False)
        return run_publish(t)

    steps.append(soft_step("fse_segment_publish", _fse))

    def _kil():
        from institutional_evidence.integration.layer import integrate_company

        return integrate_company(t, trigger_repair=True)

    steps.append(soft_step("kil_integrate", _kil))
    ok = any(s.get("ok") for s in steps)
    return collector_result("segment_data", t, ok=ok, steps=steps)
