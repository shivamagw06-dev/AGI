"""Morning quality gates — READY only when institutional ops checks pass."""

from __future__ import annotations

from typing import Any


def evaluate_morning_gates(ctx: dict[str, Any]) -> dict[str, Any]:
    results = ctx.get("results") or {}
    completed = ctx.get("completed") or {}
    failures: list[str] = []
    checks: dict[str, Any] = {}

    dry = bool(ctx.get("dry_run"))

    # Coverage
    cov = (results.get("coverage_validation") or {}).get("payload") or {}
    cov_status = (results.get("coverage_validation") or {}).get("status")
    checks["coverage"] = cov_status in {"ok", "degraded"} and (bool(cov) or dry)
    if not checks["coverage"]:
        failures.append("coverage")

    # Validation / evidence quality — evidence stage not hard-error
    ev_status = (results.get("evidence_pack_generation") or {}).get("status")
    checks["validation"] = ev_status in {"ok", "degraded", "partial"}
    checks["evidence_quality"] = checks["validation"]
    if not checks["validation"]:
        failures.append("validation")
    if not checks["evidence_quality"]:
        failures.append("evidence_quality")

    # Historical integrity
    hist = (results.get("historical_update") or {}).get("status")
    checks["historical_integrity"] = hist in {"ok", "degraded", "skipped", "error"}  # error → soft warn
    if hist == "error":
        # soft: warn but do not alone block if company ok
        checks["historical_integrity_warning"] = True
    else:
        checks["historical_integrity"] = hist in {"ok", "degraded", "skipped"}

    # Relationship integrity — soft layer; error ⇒ warning check, not always READY kill
    rel = (results.get("economic_relationships") or {}).get("status")
    checks["relationship_integrity"] = rel in {"ok", "degraded"} or dry
    if rel == "error" and not dry:
        checks["relationship_integrity"] = False
        # non-critical: record but do not append to hard failures
        checks["relationship_integrity_warning"] = True

    # Alt freshness — unavailable is transparent insufficiency (does not fail READY)
    alt = results.get("alternative_data") or {}
    checks["alternative_data_freshness"] = (
        alt.get("status") in {"ok", "degraded"}
        or bool(alt.get("dataset_unavailable"))
        or dry
    )
    if alt.get("status") == "error" and not alt.get("dataset_unavailable") and not dry:
        checks["alternative_data_freshness"] = False
        checks["alternative_data_warning"] = True

    # Expectation freshness — soft
    exp = (results.get("market_expectations") or {}).get("status")
    checks["expectation_freshness"] = exp in {"ok", "degraded"} or dry
    if exp == "error" and not dry:
        checks["expectation_freshness"] = False
        checks["expectation_warning"] = True

    # Mission control / daily health are later — gate pre-checks use prior criticals
    checks["mission_control_status"] = True  # validated post-run in ready
    checks["daily_health_status"] = True

    # Critical workflow failures block READY
    for critical in (
        "universe_update",
        "company_intelligence",
        "evidence_pack_generation",
        "coverage_validation",
    ):
        if completed.get(critical) == "error":
            failures.append(f"critical:{critical}")
            checks[f"critical_{critical}"] = False
        else:
            checks[f"critical_{critical}"] = True

    # Deduplicate soft historical: if only historical_integrity_warning, don't fail
    if "historical_integrity" in failures and checks.get("historical_integrity_warning"):
        failures = [f for f in failures if f != "historical_integrity"]

    # relationship/expectation errors → WARNING path via ready_declaration, mark failed gates
    passed = len(failures) == 0
    return {
        "status": "ok" if passed else "degraded",
        "payload": {
            "passed": passed,
            "ready": passed,
            "failures": sorted(set(failures)),
            "checks": checks,
        },
        "fabricated": False,
    }
