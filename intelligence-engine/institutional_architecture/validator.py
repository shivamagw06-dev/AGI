"""RC-01 validator façades — quality gate outcomes."""

from __future__ import annotations

from typing import Any

from institutional_architecture.conformance import run_conformance


def validate_architecture() -> dict[str, Any]:
    result = run_conformance()
    return {
        "ok": result["ok"],
        "workstream_id": result["workstream_id"],
        "architecture_score": result.get("architecture_score"),
        "violation_count": result.get("violation_count"),
        "violations": result.get("violations"),
        "release_candidate_ready": (result.get("architecture_score") or {}).get(
            "release_candidate_ready"
        ),
        "is_quality_gate": True,
        "affects_business_logic": False,
    }


def assert_conformance_or_raise() -> dict[str, Any]:
    result = run_conformance()
    if not result["ok"]:
        raise AssertionError(
            f"RC-01 architecture conformance failed with "
            f"{result.get('violation_count')} violation(s): "
            f"{[v.get('message') or v for v in (result.get('violations') or [])[:5]]}"
        )
    return result
