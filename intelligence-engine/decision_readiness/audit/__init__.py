"""IDRE package audit and sprint quality minima."""

from __future__ import annotations

from typing import Any

from decision_readiness.schema import MIN_MONITORING_TRIGGERS


def audit_package(
    readiness: dict[str, Any],
    decision_package: dict[str, Any],
) -> dict[str, Any]:
    dimensions = readiness["dimensions"]
    checks = {
        "evidence_coverage_90": dimensions["Evidence"].get(
            "coverage_pct", 0
        )
        >= 90,
        "falsification_complete": dimensions["Reasoning"].get(
            "falsification_cycles", 0
        )
        >= 1,
        "minority_reviewed": bool(
            dimensions["Debate"].get("minority_reviewed")
        ),
        "three_monitoring_triggers": dimensions["Monitoring"].get(
            "active_trigger_count", 0
        )
        >= MIN_MONITORING_TRIGGERS,
        "zero_critical_policy_violations": dimensions["Policy"].get(
            "critical_violation_count", 0
        )
        == 0,
        "decision_package_consistent": (
            decision_package["decision_readiness"]["status"]
            == readiness["decision_status"]
        ),
        "capital_readiness_separated": (
            decision_package.get("capital_allocation_readiness") is not None
        ),
        "heat_map_complete": len(readiness.get("decision_heat_map") or [])
        >= 7,
        "go_no_go_conditions_defined": len(
            decision_package.get("conditions") or []
        )
        >= 3,
    }
    mandatory = {
        "falsification_complete",
        "minority_reviewed",
        "three_monitoring_triggers",
        "zero_critical_policy_violations",
        "decision_package_consistent",
        "capital_readiness_separated",
        "heat_map_complete",
        "go_no_go_conditions_defined",
    }
    return {
        "checks": checks,
        "passed": all(checks[key] for key in mandatory),
        "fully_ready_quality_bar": all(checks.values()),
        "failed_checks": [
            key for key, passed in checks.items() if not passed
        ],
        "note": (
            "A failed 90% evidence check correctly prevents READY classification "
            "but does not invalidate the diagnostic decision package."
        ),
    }
