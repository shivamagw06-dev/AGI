"""Contradiction audit — dissent, falsification and disclosure."""

from __future__ import annotations

from typing import Any


def audit_contradictions(trace: dict[str, Any]) -> dict[str, Any]:
    data = trace["stage_data"]
    testing = data.get("Testing") or {}
    falsification = data.get("Falsification") or {}
    debate = data.get("Debate") or {}
    contradictory = [
        evidence
        for hypothesis in testing.get("tested_hypotheses") or []
        for evidence in (
            hypothesis.get("contradicting_evidence")
            or [
                e
                for e in hypothesis.get("evidence_effects") or []
                if e.get("effect") in ("Questions", "Contradicts", "Refutes")
            ]
        )
    ]
    minority = debate.get("minority_report") or []
    disagreements = (
        (debate.get("disagreement") or {}).get("conflicts") or []
    )
    outstanding = debate.get("open_questions") or (
        debate.get("consensus") or {}
    ).get("outstanding_issues") or []
    falsification_executed = bool(falsification)
    checks = {
        "contradictory_evidence_considered": bool(contradictory),
        "minority_reports_preserved": bool(minority)
        and all(m.get("preserved", True) for m in minority),
        "falsification_executed": falsification_executed,
        "outstanding_disagreements_disclosed": bool(disagreements)
        and bool(outstanding),
    }
    score = sum(1 for passed in checks.values() if passed) / len(checks)
    return {
        "score": round(score, 4),
        "score_pct": round(score * 100),
        "passed": all(checks.values()),
        "checks": checks,
        "contradictory_evidence_count": len(contradictory),
        "minority_report_count": len(minority),
        "disagreement_count": len(disagreements),
        "outstanding_disagreements": outstanding[:12],
        "all_contradictions_disclosed": all(checks.values()),
    }
