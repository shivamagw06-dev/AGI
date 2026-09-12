"""Earnings call transcript collector."""

from __future__ import annotations

from typing import Any, Dict

from institutional_coverage_factory.collectors.base import collector_result, soft_step


def collect(ticker: str) -> Dict[str, Any]:
    t = str(ticker or "").upper().strip()
    steps = []

    def _cgl_transcript():
        try:
            from continuous_gather_learn.production import sync_transcripts_for

            return sync_transcripts_for(t)
        except Exception:
            from continuous_gather_learn.knowledge_extract import extract_from_hd_series

            return extract_from_hd_series(t)

    steps.append(soft_step("cgl_transcript_sync", _cgl_transcript))

    def _earnings():
        try:
            from earnings_intelligence.production import get_earnings_pack

            return get_earnings_pack(t)
        except Exception:
            return {"ok": False}

    steps.append(soft_step("earnings_pack", _earnings))

    def _repair():
        from institutional_evidence.integration.repair.auto_repair import repair_missing_knowledge

        return repair_missing_knowledge(t, missing=["earnings_call_transcripts"])

    steps.append(soft_step("kil_repair", _repair))
    ok = any(s.get("ok") for s in steps)
    return collector_result("transcripts", t, ok=ok, steps=steps)
