"""Institutional validation gate — constitution v2.0 checks before publish."""

from __future__ import annotations

import re
from typing import Any

from market_intelligence_engine.constitution import FORBIDDEN_ADVICE_TOKENS, VALIDATION_RULES


def _contains_advice(text: str) -> list[str]:
    lower = (text or "").lower()
    # Explicit disclaimers are required copy, not advice
    lower = lower.replace("not investment advice", "")
    lower = lower.replace("no investment advice", "")
    hits = []
    for token in FORBIDDEN_ADVICE_TOKENS:
        if token in lower:
            hits.append(token)
    return hits


def validate_dashboard(pack: dict[str, Any]) -> dict[str, Any]:
    """Run constitution checks on a dashboard pack. Does not block — reports status."""
    checks: list[dict[str, Any]] = []

    # Advice language scan
    texts = [pack.get("summary") or ""]
    for p in pack.get("research_priorities") or []:
        texts.append(p.get("reason") or "")
    advice_hits: list[str] = []
    for t in texts:
        advice_hits.extend(_contains_advice(t))
    checks.append({
        "rule": VALIDATION_RULES[7],
        "passed": len(advice_hits) == 0,
        "detail": f"Forbidden advice tokens: {advice_hits}" if advice_hits else "No advice language detected",
    })

    # Premium basis when premium shown
    sector_issues = []
    for s in pack.get("sectors") or []:
        if s.get("premium_pct") is not None and not s.get("premium_basis"):
            sector_issues.append(s.get("sector"))
    checks.append({
        "rule": VALIDATION_RULES[3],
        "passed": len(sector_issues) == 0,
        "detail": f"Sectors missing premium_basis: {sector_issues[:5]}" if sector_issues else "All premiums have benchmark basis",
    })

    # Research priority reasons
    missing_reasons = [
        p.get("symbol") for p in (pack.get("research_priorities") or [])
        if not (p.get("reason") or p.get("selection_reasons"))
    ]
    checks.append({
        "rule": VALIDATION_RULES[4],
        "passed": len(missing_reasons) == 0,
        "detail": f"Missing reasons: {missing_reasons[:5]}" if missing_reasons else "All priorities have reasons",
    })

    # Breadth universe explanation
    breadth = pack.get("breadth") or {}
    checks.append({
        "rule": VALIDATION_RULES[5],
        "passed": bool(breadth.get("universe_definition")),
        "detail": "Breadth universe definition present" if breadth.get("universe_definition") else "Breadth missing universe_definition",
    })

    # Confidence methodology
    checks.append({
        "rule": VALIDATION_RULES[2],
        "passed": bool((pack.get("confidence") or {}).get("methodology")),
        "detail": "Confidence methodology documented" if (pack.get("confidence") or {}).get("methodology") else "Missing confidence methodology",
    })

    # Provenance on key widgets
    widgets = ("market_regime", "market_health", "market_drivers", "breadth", "flows")
    missing_prov = [w for w in widgets if w in pack and not (pack.get(w) or {}).get("provenance")]
    checks.append({
        "rule": VALIDATION_RULES[6],
        "passed": len(missing_prov) == 0,
        "detail": f"Widgets missing provenance: {missing_prov}" if missing_prov else "Core widgets have provenance",
    })

    passed = sum(1 for c in checks if c["passed"])
    return {
        "constitution": "2.0",
        "passed": passed == len(checks),
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks,
        "publishable": passed == len(checks),
    }
