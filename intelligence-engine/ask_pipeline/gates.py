"""Institutional completeness quality gates for Ask pipeline."""

from __future__ import annotations

from typing import Any


def evaluate_gates(
    *,
    stages: dict[str, Any],
    policy: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []

    knowledge = stages.get("knowledge") or {}
    evidence = stages.get("evidence") or {}
    planner = stages.get("planner") or {}
    governance = stages.get("governance") or {}
    dq = stages.get("decision_quality") or {}
    telemetry = stages.get("telemetry") or {}

    if knowledge.get("status") not in {"executed", "degraded"}:
        failures.append("knowledge_bypassed")
    if evidence.get("status") not in {"executed", "degraded"}:
        failures.append("evidence_bypassed")

    if policy.get("run_planner"):
        if planner.get("status") not in {"executed", "degraded", "error"}:
            failures.append("planner_bypassed")

    if evidence.get("missing_provenance"):
        failures.append("missing_provenance")

    # Provenance required on assembled pack envelopes
    packs = evidence.get("packs") or {}
    for _name, pack in packs.items():
        rows = [pack] if isinstance(pack, dict) and "provenance" in pack else list(
            (pack or {}).values()
        ) if isinstance(pack, dict) else []
        for row in rows:
            if not isinstance(row, dict):
                continue
            if "pack_type" in row and not (row.get("provenance") or {}).get("source"):
                failures.append("missing_provenance")
                break

    if dq.get("status") not in {"executed", "degraded"}:
        failures.append("decision_not_recorded")

    if stages.get("telemetry_pending"):
        pass
    elif not telemetry or telemetry.get("latency_ms") is None:
        failures.append("telemetry_missing")

    if not context.get("replay_id"):
        failures.append("replay_missing")

    for req in ("knowledge", "evidence", "governance", "decision_quality"):
        if req not in stages or not stages[req]:
            failures.append("pipeline_incomplete")
            break
    if governance.get("status") not in {"executed", "degraded", "error"}:
        # error still attempted; missing status = incomplete
        if governance.get("status") is None:
            failures.append("pipeline_incomplete")

    failures = sorted(set(failures))
    return {
        "passed": not failures,
        "failures": failures,
        "institutionally_complete": not failures,
        "note": "skipped_by_policy is allowed for portfolio/outcome/planner on education",
    }
