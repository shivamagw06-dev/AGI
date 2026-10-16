"""Shareholding pattern collector."""

from __future__ import annotations

from typing import Any, Dict

from institutional_coverage_factory.collectors.base import collector_result, soft_step


def collect(ticker: str) -> Dict[str, Any]:
    t = str(ticker or "").upper().strip()
    steps = []

    def _live():
        from live_institutional_data.production import get_company_snapshot

        return get_company_snapshot(t)

    steps.append(soft_step("lidi_snapshot", _live))

    def _acquire():
        from institutional_evidence.acquisition.collector import acquire_company_documents

        return acquire_company_documents(t)

    steps.append(soft_step("iep_acquire", _acquire))

    def _repair():
        from institutional_evidence.integration.repair.auto_repair import repair_missing_knowledge

        return repair_missing_knowledge(t, missing=["shareholding"])

    steps.append(soft_step("kil_repair", _repair))
    ok = any(s.get("ok") for s in steps)
    return collector_result("shareholding", t, ok=ok, steps=steps)
