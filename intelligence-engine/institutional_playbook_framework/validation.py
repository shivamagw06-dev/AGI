"""Acceptance tests — playbook quality gates."""

from __future__ import annotations

import re
from typing import Any

from institutional_playbook_framework.schema import FORBIDDEN_OUTPUTS


def _collect_text(pack: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("executive", "bottom_line", "house_label", "thesis"):
        v = pack.get(key)
        if isinstance(v, str):
            parts.append(v)
    rc = pack.get("response_constitution") or {}
    if isinstance(rc, dict):
        for k in ("direct_answer", "bottom_line"):
            if rc.get(k):
                parts.append(str(rc[k]))
    return " ".join(parts).lower()


def validate_playbook_response(
    pack: dict[str, Any],
    *,
    playbook: dict[str, Any],
) -> dict[str, Any]:
    """Run acceptance tests for the active playbook."""
    tests = list(playbook.get("acceptance_tests") or [])
    text = _collect_text(pack)
    forbidden_hits = [tok for tok in FORBIDDEN_OUTPUTS if tok in text]

    section_checks: dict[str, bool] = {}
    rc = pack.get("response_constitution") if isinstance(pack.get("response_constitution"), dict) else {}
    thesis = rc.get("investment_thesis") if isinstance(rc.get("investment_thesis"), dict) else {}
    ipf = pack.get("institutional_playbook_framework") if isinstance(pack.get("institutional_playbook_framework"), dict) else {}
    sections = ipf.get("sections") if isinstance(ipf.get("sections"), dict) else {}

    mapping = {
        "Business Quality": bool(thesis.get("business") or sections.get("business_quality")),
        "Financial Strength": bool(thesis.get("financial_quality") or sections.get("financial_strength")),
        "Valuation": bool(thesis.get("valuation") or sections.get("valuation")),
        "Risks": bool(thesis.get("risks") or sections.get("risks") or pack.get("risks")),
        "Growth": bool(thesis.get("growth") or sections.get("growth_outlook")),
        "Research Conclusion": bool(pack.get("research_conclusion") or sections.get("research_conclusion")),
        "Questions Before You Decide": bool(pack.get("questions_before_you_decide") or sections.get("questions_before_you_decide")),
        "Supporting Evidence": bool(rc.get("why_agib_thinks_this") or pack.get("why")),
        "Confidence explained": bool((rc.get("confidence") or {}).get("explanation") or pack.get("confidence_explanation")),
        "No BUY/SELL": len(forbidden_hits) == 0,
    }

    for test in tests:
        if test in mapping:
            section_checks[test] = mapping[test]

    passed = len(forbidden_hits) == 0 and all(section_checks.get(t, True) for t in tests if t in section_checks)

    return {
        "passed": passed,
        "playbook_key": playbook.get("playbook_key"),
        "tests": tests,
        "section_checks": section_checks,
        "forbidden_hits": forbidden_hits,
    }
