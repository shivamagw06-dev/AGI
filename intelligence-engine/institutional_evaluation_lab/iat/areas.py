"""Evaluation areas A–E for the Institutional Acceptance Test."""

from __future__ import annotations

from collections import Counter
from typing import Any

from institutional_evaluation_lab.iat.metrics import as_0_10, as_pct, avg, p95, pct
from institutional_evaluation_lab.iat.schema import REQUIRED_BUCKETS, REQUIRED_UNIVERSE_N, THRESHOLDS


def evaluate_universe(rows: list[dict[str, Any]], *, golden_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    """Confirm the release covers the frozen Golden 200 composition."""
    n = len(rows)
    buckets = Counter(str(r.get("bucket") or "unknown") for r in rows)
    expected = dict(REQUIRED_BUCKETS)
    # Prefer golden composition when available (source of truth for Phase 1)
    if golden_summary and isinstance(golden_summary.get("bucket_counts"), dict):
        expected = {k: int(v) for k, v in golden_summary["bucket_counts"].items()}

    mismatches = []
    for k, need in expected.items():
        got = int(buckets.get(k, 0))
        if got != need:
            mismatches.append({"bucket": k, "expected": need, "actual": got})

    passed = n == REQUIRED_UNIVERSE_N and not mismatches
    return {
        "area": "universe",
        "status": "PASS" if passed else "FAIL",
        "companies": n,
        "required": REQUIRED_UNIVERSE_N,
        "bucket_counts": dict(buckets),
        "required_buckets": expected,
        "mismatches": mismatches,
        "golden_frozen": bool((golden_summary or {}).get("frozen")),
        "composition_sha256": (golden_summary or {}).get("composition_sha256"),
    }


def evaluate_governance(rows: list[dict[str, Any]], phase6: dict[str, Any] | None) -> dict[str, Any]:
    """A. Governance — constitution, spec, editorial, gate, replay provenance."""
    th = THRESHOLDS
    phase6 = phase6 or {}
    present = bool(phase6)
    critical_fails = int(phase6.get("critical_rule_failures") or 0)
    assertions = phase6.get("governance_assertions") or phase6.get("board") or []
    rule_n = len(assertions) if assertions else 8
    rule_pass = sum(1 for a in assertions if str(a.get("status")).upper() == "PASS")
    # If phase6 aggregates pass/fail per rule without status, derive from fail counts
    if assertions and rule_pass == 0:
        rule_pass = sum(1 for a in assertions if int(a.get("fail") or 0) == 0)
    spec_compliance = pct(rule_pass, rule_n) if assertions else (100.0 if present and critical_fails == 0 else 0.0)

    # Gate blocks unsupported High Conviction
    blocked_ok = 0
    blocked_total = 0
    editorial_violations = 0
    for r in rows:
        readiness = as_pct(r.get("recommendation_readiness"))
        decision = str(r.get("decision") or "")
        gate = str(r.get("gate") or "").upper()
        if readiness is not None and readiness < 80.0:
            blocked_total += 1
            if decision != "High Conviction":
                blocked_ok += 1
            else:
                editorial_violations += 1
        if gate in {"FAIL", "FAILED"} and decision == "High Conviction":
            editorial_violations += 1

    gate_enforcement = pct(blocked_ok, blocked_total) if blocked_total else 100.0

    # Constitution / versions stamped on rows or release
    constitution_hits = sum(
        1
        for r in rows
        if (r.get("versions") or {}).get("constitution_version")
        or r.get("constitution_version")
        or r.get("investment_thesis_status") is not None
        or r.get("gate") is not None
    )
    constitution_pct = pct(constitution_hits, len(rows)) or 0.0

    # Replay inputs present (deterministic replay capability)
    replay_hits = sum(1 for r in rows if r.get("replay_inputs") or r.get("price_ltp") is not None)
    replay_pct = pct(replay_hits, len(rows)) or 0.0

    checks = {
        "constitution_enforced": constitution_pct >= 90.0,
        "governance_spec_passes": present and critical_fails <= th["governance_critical_fail_max"],
        "no_editorial_override": editorial_violations <= th["editorial_violations_max"],
        "gate_blocks_unsupported": (gate_enforcement or 0) >= th["gate_enforcement_pct_min"],
        "deterministic_replay_ready": (replay_pct or 0) >= th["replay_inputs_pct_min"],
    }
    passed = all(checks.values()) and (spec_compliance or 0) >= th["spec_compliance_pct_min"]

    return {
        "area": "governance",
        "status": "PASS" if passed else "FAIL",
        "constitution_pct": constitution_pct,
        "spec_compliance_pct": spec_compliance if spec_compliance is not None else 0.0,
        "editorial_violations": editorial_violations,
        "critical_rule_failures": critical_fails,
        "gate_enforcement_pct": gate_enforcement,
        "replay_inputs_pct": replay_pct,
        "phase6_present": present,
        "checks": checks,
    }


def evaluate_evidence(rows: list[dict[str, Any]], summary: dict[str, Any] | None = None) -> dict[str, Any]:
    """B. Evidence — coverage, freshness, lineage, completeness, source attribution."""
    th = THRESHOLDS
    summary = summary or {}
    n = len(rows) or 1

    # Coverage proxies from row completeness
    pack_ok = sum(1 for r in rows if r.get("pack_present") is True or r.get("status") == "COMPLETED")
    price_ok = sum(1 for r in rows if r.get("live_price") or r.get("price_available") or r.get("price_ltp") is not None)
    fin_ok = sum(1 for r in rows if r.get("financial_quality") is not None)
    own_ok = sum(
        1
        for r in rows
        if not (
            isinstance(r.get("failure"), dict)
            and "SHAREHOLDING" in str((r.get("failure") or {}).get("reason") or "").upper()
        )
        and r.get("recommendation_readiness") is not None
    )
    # Prefer summary evidence_coverage when present
    ev_cov = ((summary.get("coverage") or {}).get("evidence_coverage")) or {}
    if ev_cov:
        complete = int(ev_cov.get("Complete") or 0)
        partial = int(ev_cov.get("Partial") or 0)
        insuff = int(ev_cov.get("Insufficient") or 0)
        total = complete + partial + insuff
        coverage = pct(complete + partial, total) if total else pct(pack_ok, n)
    else:
        complete = sum(1 for r in rows if str(r.get("evidence_class") or "") == "Complete")
        partial = sum(1 for r in rows if str(r.get("evidence_class") or "") == "Partial")
        coverage = pct(complete + partial, n)

    # Freshness: non-stale price + no stale flags
    fresh_hits = sum(
        1
        for r in rows
        if not r.get("price_stale")
        and (r.get("live_price") or r.get("price_available") or r.get("freshness_ok") is True or r.get("price_ltp") is not None)
    )
    freshness = pct(fresh_hits, n)

    # Lineage: versions / run_id / release_id
    lineage_hits = sum(
        1
        for r in rows
        if r.get("versions") or r.get("run_id") or r.get("release_id") or r.get("replay_inputs")
    )
    lineage = pct(lineage_hits, n)

    # Completeness: evidence_class Complete rate (stricter)
    completeness = pct(complete if ev_cov else sum(1 for r in rows if str(r.get("evidence_class")) == "Complete"), n)

    # Source attribution
    source_hits = sum(
        1
        for r in rows
        if r.get("price_source")
        or (r.get("replay_inputs") or {}).get("price_snapshot")
        or r.get("evidence_class")
    )
    source_attr = pct(source_hits, n)

    # Institutional readiness average (coverage of gate)
    inst = avg([as_pct(r.get("institutional_readiness")) for r in rows])

    checks = {
        "coverage": (coverage or 0) >= th["evidence_coverage_pct_min"],
        "freshness": (freshness or 0) >= th["evidence_freshness_pct_min"],
        "lineage": (lineage or 0) >= th["lineage_pct_min"],
        "source_attribution": (source_attr or 0) >= th["source_attribution_pct_min"],
    }
    passed = all(checks.values())

    return {
        "area": "evidence",
        "status": "PASS" if passed else "FAIL",
        "coverage_pct": coverage,
        "freshness_pct": freshness,
        "lineage_pct": lineage,
        "completeness_pct": completeness,
        "source_attribution_pct": source_attr,
        "institutional_readiness_pct": inst,
        "pillar_proxies": {
            "pack_pct": pct(pack_ok, n),
            "price_pct": pct(price_ok, n),
            "financials_pct": pct(fin_ok, n),
            "ownership_proxy_pct": pct(own_ok, n),
        },
        "checks": checks,
    }


def evaluate_decision_quality(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """C. Decision Quality — quality / opportunity / readiness / confidence (separate concepts)."""
    cq = avg([as_0_10(r.get("company_quality")) for r in rows])
    # Investment opportunity: prefer explicit field, else derive lightly from valuation+macro (display only)
    opp_vals = []
    for r in rows:
        if r.get("investment_opportunity") is not None:
            opp_vals.append(as_0_10(r.get("investment_opportunity")))
        elif r.get("market_opportunity") is not None:
            opp_vals.append(as_0_10(r.get("market_opportunity")))
        else:
            # Soft proxy from available scores — not a new scoring engine
            parts = [as_0_10(r.get("valuation")), as_0_10(r.get("macro")), as_0_10(r.get("technical"))]
            parts = [p for p in parts if p is not None]
            opp_vals.append(round(sum(parts) / len(parts), 2) if parts else None)
    opp = avg(opp_vals)
    readiness = avg([as_pct(r.get("recommendation_readiness")) for r in rows])
    institutional = avg([as_pct(r.get("institutional_readiness")) for r in rows])
    confidence = avg(
        [
            as_pct(r.get("analytical_confidence") if r.get("analytical_confidence") is not None else r.get("recommendation_readiness"))
            for r in rows
        ]
    )

    # Decision quality area does not hard-fail on averages (descriptive); FAIL only if all missing
    present = any(v is not None for v in (cq, opp, readiness, confidence))
    return {
        "area": "decision_quality",
        "status": "PASS" if present else "FAIL",
        "average_company_quality": cq,
        "average_opportunity": opp,
        "average_recommendation_readiness_pct": readiness,
        "average_institutional_readiness_pct": institutional,
        "average_analytical_confidence_pct": confidence,
        "note": (
            "Company Quality, Investment Opportunity, Recommendation Readiness, "
            "Institutional Readiness, and Analytical Confidence are reported separately "
            "and must not be conflated."
        ),
    }


def evaluate_operational(rows: list[dict[str, Any]], summary: dict[str, Any] | None = None) -> dict[str, Any]:
    """D. Operational — runtime, coverage, failure recovery, replay."""
    th = THRESHOLDS
    summary = summary or {}
    runtimes = []
    for r in rows:
        ms = r.get("runtime_ms")
        if ms is None and isinstance(r.get("timing"), dict):
            ms = (r.get("timing") or {}).get("total_ms")
        if ms is not None:
            try:
                runtimes.append(float(ms) / 1000.0)
            except (TypeError, ValueError):
                pass
    if not runtimes:
        health = summary.get("health") or {}
        if health.get("average_runtime_ms") is not None:
            runtimes = [float(health["average_runtime_ms"]) / 1000.0]

    avg_rt = avg(runtimes)
    p95_rt = p95(runtimes) if runtimes else None

    failed = [
        r
        for r in rows
        if str(r.get("status") or "").upper() in {"FAILED", "FAIL"}
        or str(r.get("gate") or "").upper() in {"FAIL", "FAILED"}
        or r.get("ok") is False
    ]
    structured = sum(
        1
        for r in failed
        if (isinstance(r.get("failure"), dict) and r["failure"].get("reason"))
        or str(r.get("evidence_class") or "") in {"Insufficient", "Partial"}
    )
    structured_pct = pct(structured, len(failed)) if failed else 100.0

    replay_pct = pct(sum(1 for r in rows if r.get("replay_inputs") or r.get("price_ltp") is not None), len(rows) or 1)
    gate_pass = pct(sum(1 for r in rows if str(r.get("gate") or "").upper() == "PASS"), len(rows) or 1)

    checks = {
        "avg_runtime_ok": (avg_rt is None) or avg_rt <= th["avg_runtime_s_max"],
        "failure_recovery": (structured_pct or 0) >= th["structured_failure_pct_min"],
        "replay": (replay_pct or 0) >= th["replay_inputs_pct_min"],
    }
    passed = all(checks.values())
    return {
        "area": "operational",
        "status": "PASS" if passed else "FAIL",
        "average_runtime_s": avg_rt,
        "p95_runtime_s": p95_rt,
        "gate_pass_pct": gate_pass,
        "structured_failure_pct": structured_pct,
        "replay_ready_pct": replay_pct,
        "failed_count": len(failed),
        "checks": checks,
    }


def evaluate_drift(drift: dict[str, Any] | None) -> dict[str, Any]:
    """E. Drift — unknown 0%, budget PASS, expected PASS."""
    th = THRESHOLDS
    if not drift:
        return {
            "area": "drift",
            "status": "FAIL",
            "present": False,
            "recommendation_changes": None,
            "expected": None,
            "unexpected": None,
            "unknown_drift": None,
            "budget": "MISSING",
            "note": "Drift report required for Phase 1 baseline qualification.",
        }

    unknown = int(
        drift.get("unexpected")
        if drift.get("unexpected") is not None
        else (drift.get("by_reason_code") or {}).get("UNKNOWN") or 0
    )
    # Also count UNKNOWN reason code if present
    by_rc = drift.get("by_reason_code") or {}
    if "UNKNOWN" in by_rc:
        unknown = max(unknown, int(by_rc.get("UNKNOWN") or 0))

    budget = drift.get("budget") or {}
    budget_pass = bool(budget.get("passed")) if isinstance(budget, dict) else str(budget).upper() == "PASS"
    changes = drift.get("recommendations_changed")
    if changes is None:
        changes = drift.get("recommendation_changes")
    expected = drift.get("expected")
    unexpected = drift.get("unexpected")
    if unexpected is None:
        unexpected = unknown

    expected_ok = True
    if expected is not None and changes is not None:
        # Expected drift PASS when all changes are accounted as expected (unexpected == 0)
        expected_ok = int(unexpected or 0) == 0

    checks = {
        "unknown_zero": unknown <= th["unknown_drift_max"],
        "budget_pass": budget_pass if th["drift_budget_must_pass"] else True,
        "expected_pass": expected_ok,
    }
    passed = all(checks.values())
    return {
        "area": "drift",
        "status": "PASS" if passed else "FAIL",
        "present": True,
        "recommendation_changes": changes,
        "expected": expected,
        "unexpected": unexpected,
        "unknown_drift": unknown,
        "budget": "PASS" if budget_pass else "FAIL",
        "expected_drift": "PASS" if expected_ok else "FAIL",
        "checks": checks,
    }
