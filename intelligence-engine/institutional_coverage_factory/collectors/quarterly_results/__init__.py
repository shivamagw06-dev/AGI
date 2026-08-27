"""Quarterly results + financial statements collector."""

from __future__ import annotations

from typing import Any, Dict

from institutional_coverage_factory.collectors.base import collector_result, soft_step


def collect(ticker: str) -> Dict[str, Any]:
    t = str(ticker or "").upper().strip()
    steps = []

    def _fse_ingest():
        from financial_statements_engine.production import run_ingest

        return run_ingest(t, force=False)

    steps.append(soft_step("fse_ingest", _fse_ingest))

    def _fse_publish():
        from financial_statements_engine.production import run_publish

        return run_publish(t)

    steps.append(soft_step("fse_publish", _fse_publish))

    def _kil():
        from institutional_evidence.integration.layer import integrate_company

        return integrate_company(t, trigger_repair=True)

    steps.append(soft_step("kil_integrate", _kil))
    ok = any(s.get("ok") for s in steps)
    return collector_result("quarterly_results", t, ok=ok, steps=steps)
