"""Constitution validation — forbidden outputs and completeness."""

from __future__ import annotations

from typing import Any

from ask_intelligence_constitution.schema import FORBIDDEN_OUTPUTS, VALIDATION_RULES


def _scan_text(text: str) -> list[str]:
    lower = (text or "").lower()
    lower = lower.replace("not investment advice", "")
    lower = lower.replace("no investment advice", "")
    hits = []
    for token in FORBIDDEN_OUTPUTS:
        if token in lower:
            hits.append(token)
    return hits


def _collect_text(pack: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("executive", "summary", "bottom_line", "thesis"):
        if pack.get(key):
            parts.append(str(pack[key]))
    rc = pack.get("response_constitution") or {}
    for key in ("direct_answer", "bottom_line"):
        if rc.get(key):
            parts.append(str(rc[key]))
    aic = pack.get("ask_intelligence_constitution") or {}
    sections = aic.get("sections") or {}
    for v in sections.values():
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, dict):
            parts.append(str(v.get("summary") or ""))
    return " ".join(parts)


def validate_ask_response(pack: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    intent = (pack.get("ask_intelligence_constitution") or {}).get("intent") or {}
    checks.append({
        "rule": VALIDATION_RULES[0],
        "passed": bool(intent.get("primary_intent")),
        "detail": f"Intent: {intent.get('primary_intent')}" if intent.get("primary_intent") else "Missing intent",
    })

    checks.append({
        "rule": VALIDATION_RULES[1],
        "passed": bool(intent.get("methodology")),
        "detail": "Methodology steps defined" if intent.get("methodology") else "Missing methodology",
    })

    forbidden = _scan_text(_collect_text(pack))
    checks.append({
        "rule": VALIDATION_RULES[4],
        "passed": len(forbidden) == 0,
        "detail": f"Forbidden tokens: {forbidden}" if forbidden else "No forbidden investment instruction language",
    })

    rc = pack.get("research_conclusion") or ((pack.get("ask_intelligence_constitution") or {}).get("sections") or {}).get("research_conclusion")
    checks.append({
        "rule": VALIDATION_RULES[5],
        "passed": bool(rc),
        "detail": "Research conclusion present" if rc else "Missing research conclusion",
    })

    conf = (pack.get("ask_intelligence_constitution") or {}).get("sections", {}).get("confidence") or {}
    checks.append({
        "rule": VALIDATION_RULES[6],
        "passed": bool(conf.get("methodology") or conf.get("explanation")),
        "detail": "Confidence methodology documented",
    })

    passed = sum(1 for c in checks if c["passed"])
    return {
        "constitution": "1.0",
        "passed": passed == len(checks),
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks,
        "forbidden_hits": forbidden,
    }
