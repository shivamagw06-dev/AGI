"""Management guidance collector."""

from __future__ import annotations

from typing import Any, Dict

from institutional_coverage_factory.collectors.base import collector_result, soft_step


def collect(ticker: str) -> Dict[str, Any]:
    t = str(ticker or "").upper().strip()
    steps = []

    def _earnings():
        try:
            from earnings_intelligence.production import get_earnings_pack

            return get_earnings_pack(t)
        except Exception:
            from earnings_intelligence.pack import build_earnings_pack

            return build_earnings_pack(t)

    steps.append(soft_step("earnings_guidance", _earnings))

    def _repair():
        from institutional_evidence.integration.repair.auto_repair import repair_missing_knowledge

        return repair_missing_knowledge(t, missing=["management_guidance"])

    steps.append(soft_step("kil_repair", _repair))
    ok = any(s.get("ok") for s in steps)
    return collector_result("guidance", t, ok=ok, steps=steps)
