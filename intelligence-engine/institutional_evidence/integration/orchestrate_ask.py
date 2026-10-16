"""Research orchestration via KIL — Ask AGI path.

User asks → Check Company Memory → Knowledge Version current?
→ Wait/Refresh KIL → Research Ready? → Pack or Research Blocked.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def orchestrate_ask_research(ticker: str, *, force_kil_refresh: bool = False) -> Dict[str, Any]:
    from .layer import integrate_company, get_integrated_company
    from .versioning.snapshots import get_latest_snapshot
    from ..research_pack.builder import build_institutional_research_pack

    t = str(ticker or "").upper().strip()
    latest = get_latest_snapshot()
    current_version = (latest or {}).get("knowledge_version")
    cached = get_integrated_company(t)

    version_current = bool(
        cached
        and cached.get("knowledge_version")
        and current_version
        and cached.get("knowledge_version") == current_version
    )

    if force_kil_refresh or not version_current or not cached:
        integ = integrate_company(t, trigger_repair=True, knowledge_version=current_version)
    else:
        integ = cached

    if not integ.get("research_ready") or not integ.get("claim_safe"):
        failed = (integ.get("institutional_coverage") or {}).get("failed") or []
        reasons = []
        if not integ.get("financials_published"):
            reasons.append("Missing Financial Statements")
        if "earnings_call_transcripts" in failed:
            reasons.append("Missing Transcript")
        if not integ.get("claim_safe"):
            reasons.append("Evidence Incomplete")
        if not reasons:
            reasons.append("Research Ready == false")
        return {
            "ok": True,
            "blocked": True,
            "status": "Research Blocked",
            "ticker": t,
            "reasons": reasons,
            "coverage_state": (integ.get("coverage_state") or {}).get("coverage_state"),
            "knowledge_version": integ.get("knowledge_version"),
            "integration": integ,
        }

    pack = build_institutional_research_pack(t, auto_acquire=True)
    pack["knowledge_version"] = integ.get("knowledge_version")
    pack["kil_integrated"] = True
    return {
        "ok": True,
        "blocked": False,
        "status": "Research Pack Ready",
        "ticker": t,
        "knowledge_version": integ.get("knowledge_version"),
        "coverage_state": (integ.get("coverage_state") or {}).get("coverage_state"),
        "research_pack": pack,
        "next": "generate_research",
    }
