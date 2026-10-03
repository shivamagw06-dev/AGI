"""Annual report collector — soft bridge to FSE / IEP acquisition."""

from __future__ import annotations

from typing import Any, Dict

from institutional_coverage_factory.collectors.base import collector_result, soft_step


def collect(ticker: str) -> Dict[str, Any]:
    t = str(ticker or "").upper().strip()
    steps = []

    def _fse():
        from financial_statements_engine.production import run_ingest

        return run_ingest(t, force=False)

    steps.append(soft_step("fse_ingest", _fse))

    def _acquire():
        from institutional_evidence.acquisition.collector import acquire_company_documents

        return acquire_company_documents(t, trigger_ingest=False)

    steps.append(soft_step("iep_acquire", _acquire))

    def _repair():
        from institutional_evidence.integration.repair.auto_repair import repair_missing_knowledge

        return repair_missing_knowledge(t, missing=["annual_reports", "financial_statements"])

    steps.append(soft_step("kil_repair", _repair))
    ok = any(s.get("ok") for s in steps)
    return collector_result("annual_reports", t, ok=ok, steps=steps)
