"""Merge gate — no release should merge unless ACS certification passes.

Soft gate function for CI / quality-gates. Does not redesign engines or UI.
"""

from __future__ import annotations

from typing import Any

from academy.certification.schema import CERTIFICATION_PASS_SCORE, INSTITUTIONAL_READY_SCORE


def certification_gate(*, full: bool = False, limit_per_analyst: int | None = 8) -> dict[str, Any]:
    """Return merge-gate decision.

    Default samples exams per analyst for speed; set full=True for release certification.
    """
    from academy.certification.runner import run_certification

    suite = run_certification(
        limit_per_analyst=None if full else limit_per_analyst,
    )
    cert = suite.get("certificate") or {}
    overall = float(cert.get("overall_intelligence") or 0.0)
    allow_merge = bool(cert.get("certified")) and overall >= CERTIFICATION_PASS_SCORE
    return {
        "gate": "ACADEMY_CERTIFICATION_SUITE",
        "allow_merge": allow_merge,
        "certified": bool(cert.get("certified")),
        "institutional_ready": bool(cert.get("institutional_ready")),
        "overall_intelligence": overall,
        "grade": cert.get("grade"),
        "floor": CERTIFICATION_PASS_SCORE,
        "institutional_ready_floor": INSTITUTIONAL_READY_SCORE,
        "failed_exam_ids": (cert.get("exam_stats") or {}).get("failed_exam_ids") or [],
        "weak_areas": cert.get("weak_areas") or [],
        "message": (
            "Certification PASS — merge permitted"
            if allow_merge
            else "Certification FAIL — do not merge until institutional reasoning clears the floor"
        ),
        "certificate": cert,
        "mode": "full" if full else "sampled",
    }
