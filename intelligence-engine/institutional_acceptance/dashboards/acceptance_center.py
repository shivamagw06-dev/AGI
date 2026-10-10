"""Acceptance Center soft-slice board for Mission Control."""

from __future__ import annotations

from typing import Any, Optional


def acceptance_center_board(report: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    r = dict(report or {})
    phases = r.get("phases") or {}
    return {
        "acceptance_center": True,
        "status": "certified" if r.get("certified") else ("ok" if r else "idle"),
        "total_cases": r.get("total"),
        "passed": r.get("passed"),
        "failed": r.get("failed"),
        "pass_rate_pct": r.get("pass_rate_pct"),
        "critical_failures": r.get("critical_failures"),
        "architecture_score": r.get("architecture_score"),
        "security_violations": r.get("security_violations"),
        "memory_leaks": r.get("memory_leaks"),
        "certified": bool(r.get("certified")),
        "overall_result": r.get("overall_result") or "NOT RUN",
        "phase_status": {
            k: (v or {}).get("status")
            for k, v in phases.items()
        },
        "closed_beta_recommendation": (
            "After PAT passes: closed beta with 5–10 experienced finance professionals; "
            "observe struggle points; prioritize v1.1 from real workflows."
        ),
    }
