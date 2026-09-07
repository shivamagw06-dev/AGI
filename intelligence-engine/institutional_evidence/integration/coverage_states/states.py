"""Coverage States — every company exists in exactly one state."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..schema import COVERAGE_STATES


def compute_coverage_state(
    *,
    discovered: bool = True,
    acquiring: bool = False,
    transformed: Optional[Dict[str, Any]] = None,
    quality: Optional[Dict[str, Any]] = None,
    pack: Optional[Dict[str, Any]] = None,
    coverage: Optional[Dict[str, Any]] = None,
    knowledge_confidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    fin_pub = bool((transformed or {}).get("financials_published"))
    periods = int((transformed or {}).get("period_count") or 0)
    claim_safe = bool((pack or {}).get("claim_safe"))
    research_ready = bool((pack or {}).get("research_ready"))
    inst_complete = bool((coverage or {}).get("institutional_coverage_complete"))
    quality_ok = bool((quality or {}).get("publish_allowed"))
    kc_ok = bool((knowledge_confidence or {}).get("above_threshold"))

    if inst_complete and research_ready:
        state = "CONTINUOUS MONITORING"
    elif inst_complete:
        state = "INSTITUTIONAL COVERAGE COMPLETE"
    elif research_ready and claim_safe:
        state = "RESEARCH READY"
    elif fin_pub and periods > 0 and (quality_ok or kc_ok):
        state = "KNOWLEDGE READY"
    elif fin_pub and periods > 0:
        state = "VALIDATING"
    elif periods > 0 or (transformed or {}).get("cgl_extract_present"):
        state = "NORMALIZING"
    elif acquiring:
        state = "ACQUIRING"
    elif discovered:
        state = "DISCOVERED"
    else:
        state = "DISCOVERED"

    if state not in COVERAGE_STATES:
        state = "DISCOVERED"

    return {
        "ok": True,
        "coverage_state": state,
        "states": list(COVERAGE_STATES),
        "signals": {
            "financials_published": fin_pub,
            "period_count": periods,
            "claim_safe": claim_safe,
            "research_ready": research_ready,
            "institutional_coverage_complete": inst_complete,
            "quality_publishable": quality_ok,
            "knowledge_confidence_ok": kc_ok,
        },
    }
