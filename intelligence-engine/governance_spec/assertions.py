"""Execute Governance Spec rules against one Evaluation Lab ticker JSON."""

from __future__ import annotations

from typing import Any

from governance_spec.registry import load_spec


def assert_ticker(
    row: dict[str, Any],
    *,
    spec_version: str | None = None,
) -> dict[str, Any]:
    """Return per-rule PASS/FAIL/SKIP for a single company result."""
    spec = load_spec(spec_version)
    evaluate_rule = spec["evaluate_rule"]
    results = []
    for rule_meta in spec["rules"]:
        rid = rule_meta["rule_id"]
        results.append(evaluate_rule(rid, row))

    failed = [r for r in results if r.get("status") == "FAIL"]
    passed = [r for r in results if r.get("status") == "PASS"]
    skipped = [r for r in results if r.get("status") == "SKIP"]
    critical_fails = [
        r for r in failed if str((spec["rules_by_id"].get(r["rule_id"]) or {}).get("severity")) == "Critical"
        or str(r.get("severity")) == "Critical"
    ]
    return {
        "ticker": row.get("ticker"),
        "spec_version": spec["spec_version"],
        "assertions": results,
        "summary": {
            "pass": len(passed),
            "fail": len(failed),
            "skip": len(skipped),
            "critical_fail": len(critical_fails),
        },
        "passed": len(failed) == 0,
        "board": [
            {"rule_id": r["rule_id"], "status": r["status"], "severity": r.get("severity")}
            for r in results
        ],
    }
