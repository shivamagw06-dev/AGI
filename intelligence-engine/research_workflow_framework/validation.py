"""Workflow acceptance tests."""

from __future__ import annotations

from typing import Any

from research_workflow_framework.schema import FORBIDDEN_OUTPUTS


def _text(pack: dict[str, Any]) -> str:
    parts: list[str] = []
    for k in ("executive", "bottom_line", "house_label"):
        if pack.get(k):
            parts.append(str(pack[k]))
    rc = pack.get("response_constitution") or {}
    if isinstance(rc, dict):
        for k in ("direct_answer", "bottom_line"):
            if rc.get(k):
                parts.append(str(rc[k]))
    return " ".join(parts).lower()


def validate_workflow_response(
    pack: dict[str, Any],
    *,
    workflow: dict[str, Any],
    workflow_result: dict[str, Any],
) -> dict[str, Any]:
    """Run workflow-level acceptance tests."""
    text = _text(pack)
    forbidden = [t for t in FORBIDDEN_OUTPUTS if t in text]

    checks = {
        "Correct workflow selected": bool(workflow.get("workflow_key")),
        "Required intelligence collected": bool(
            (pack.get("institutional_playbook_framework") or {}).get("playbook", {}).get("required_intelligence")
        ),
        "Evidence available": bool(pack.get("why") or (pack.get("response_constitution") or {}).get("why_agib_thinks_this")),
        "Research conclusion generated": bool(pack.get("research_conclusion")),
        "Next Best Research Question generated": bool(workflow_result.get("next_best_research_question")),
        "Research status updated": bool(workflow_result.get("research_status")),
        "No prohibited language": len(forbidden) == 0,
    }

    tests = list(workflow.get("acceptance_tests") or [])
    relevant = {t: checks.get(t, True) for t in tests if t in checks}
    passed = all(relevant.values()) and len(forbidden) == 0

    return {
        "passed": passed,
        "workflow_key": workflow.get("workflow_key"),
        "checks": relevant,
        "forbidden_hits": forbidden,
        "needs_further_investigation": workflow_result.get("research_status", {}).get("needs_further_investigation"),
    }
