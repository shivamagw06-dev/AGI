"""Decision constitution — never bypass Evidence → Reasoning → Committee → Portfolio → Policy → Decision."""

from __future__ import annotations

from typing import Any

from decision_engine_v2.schema import CONSTITUTIONAL_CHAIN


def enforce_constitution(pack: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "evidence": bool(pack.get("evidence_summary") or pack.get("inputs_present")),
        "reasoning": bool(pack.get("reasoning_chain") or pack.get("weights")),
        "committee": bool(pack.get("committee_position") is not None or pack.get("committee_present")),
        "portfolio": bool(pack.get("portfolio_context") is not None or pack.get("portfolio_present")),
        "policy": bool(pack.get("recommendation_gate") or pack.get("policy_checked")),
        "decision": bool(pack.get("executive_decision") or pack.get("institutional_judgement")),
    }
    order_ok = list(CONSTITUTIONAL_CHAIN) == [
        "evidence",
        "reasoning",
        "committee",
        "portfolio",
        "policy",
        "decision",
    ]
    violations = [k for k, ok in checks.items() if not ok]
    return {
        "constitutional": order_ok and not violations,
        "chain": list(CONSTITUTIONAL_CHAIN),
        "checks": checks,
        "violations": violations,
        "rule": "Every decision is constitutional — no bypass of Evidence→Reasoning→Committee→Portfolio→Policy→Decision",
        "never_bypass": True,
    }
